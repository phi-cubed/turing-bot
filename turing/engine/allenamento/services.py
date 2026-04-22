import os
import re
import subprocess
import sys
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from engine.models import Squadra


_PASSWORD_RE = re.compile(r'(password[^\s=]*[=\s]+)[^\s]+', re.IGNORECASE)


def _scrub_secrets(text):
    if not text:
        return ''
    return _PASSWORD_RE.sub(r'\1***', text)


def list_allenamenti_disponibili():
    """Scansiona settings.ALLENAMENTI_DIR e ritorna una lista di tuple
    (anno, nome, json_path, problemi_path, risposte_path) solo per le gare
    per cui tutti e tre i file esistono.
    """
    base = Path(settings.ALLENAMENTI_DIR)
    if not base.is_dir():
        return []
    result = []
    for anno_dir in sorted(base.iterdir()):
        if not anno_dir.is_dir():
            continue
        try:
            anno = int(anno_dir.name)
        except ValueError:
            continue
        for json_path in sorted(anno_dir.glob('*.json')):
            nome = json_path.stem
            problemi = anno_dir / f'{nome}_nome_problemi.txt'
            risposte = anno_dir / f'{nome}_risposte.txt'
            if problemi.is_file() and risposte.is_file():
                result.append((anno, nome, json_path, problemi, risposte))
    return result


def _resolve_base_paths(base_key):
    """Converte 'anno/nome' nel dict {json, problemi, risposte} se i file esistono."""
    if not base_key or '/' not in base_key:
        return None
    anno_str, nome = base_key.split('/', 1)
    try:
        anno = int(anno_str)
    except ValueError:
        return None
    base = Path(settings.ALLENAMENTI_DIR) / anno_str
    json_path = base / f'{nome}.json'
    problemi = base / f'{nome}_nome_problemi.txt'
    risposte = base / f'{nome}_risposte.txt'
    if not (json_path.is_file() and problemi.is_file() and risposte.is_file()):
        return None
    return {'anno': anno, 'nome': nome, 'json': json_path,
            'problemi': problemi, 'risposte': risposte}


def _script_path(name):
    return Path(settings.TESTFILES_DIR) / name


def run_setup_gara_bot(cleaned_data, user):
    """Esegue setup_gara_bot.py in foreground. Ritorna l'id della Gara Turing creata.
    Alza RuntimeError (con messaggio scrubbed) in caso di fallimento.
    Best-effort: se la gara era stata creata prima del fallimento, la elimina.
    """
    paths = cleaned_data['base_paths']
    consegnatori_arg = ','.join(
        f'{u.username}:{i}' for i, u in enumerate(cleaned_data['consegnatori'], 1)
    )
    
    json_file = paths['json']
    if not json_file.is_file():
        raise RuntimeError(f'File JSON non trovato: {json_file}')
    
    loaded_json = None
    try:
        import json
        with open(json_file, 'r') as f:
            loaded_json = json.load(f)
    except Exception as e:
        raise RuntimeError(f'Errore nel parsing del file JSON: {e}')
    
    if not "n_blocco" in loaded_json or not "k_blocco" in loaded_json:
        raise RuntimeError('Il file JSON deve contenere i campi "n_blocco" e "k_blocco".')
    
    cmd = [
        sys.executable, str(_script_path('setup_gara_bot.py')),
        '--base-url', settings.TURING_BASE_URL,
        '--admin-username', settings.TURING_ADMIN_USER,
        '--admin-password', settings.TURING_ADMIN_PASS,
        '--bot-username', settings.BOT_USERNAME,
        '--bot-password', settings.TURING_BOT_PASS,
        '--nome', cleaned_data['nome'],
        '-N', str(cleaned_data['num_squadre_umane']),
        '--n-blocco', str(loaded_json['n_blocco']),
        '--k-blocco', str(loaded_json['k_blocco']),
        '--bot-file', str(paths['json']),
        '--nomi-problemi', str(paths['problemi']),
        '--risposte-problemi', str(paths['risposte']),
        '--consegnatori-esistenti', consegnatori_arg,
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300, check=False,
        cwd=str(Path(settings.BASE_DIR).parent),
    )
    gara_id_match = re.search(r'^gara_id=(\d+)$', proc.stdout or '', re.MULTILINE)
    if proc.returncode != 0:
        if gara_id_match:
            from engine.models import Gara
            Gara.objects.filter(pk=int(gara_id_match.group(1))).delete()
        detail = _scrub_secrets(proc.stderr or proc.stdout[-800:])
        raise RuntimeError(detail or f'setup_gara_bot.py fallito (returncode {proc.returncode})')
    if not gara_id_match:
        raise RuntimeError('setup_gara_bot.py non ha restituito gara_id')
    return int(gara_id_match.group(1))


def spawn_avvia_gara_bot(allenamento):
    """Avvia avvia_gara_bot.py in background (detached). Salva pid e path log."""
    log_dir = Path(settings.BASE_DIR) / 'logs' / 'allenamenti'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f'gara_{allenamento.gara_id}_{int(time.time())}.log'
    logf = open(log_path, 'ab', buffering=0)

    env = {
        **os.environ,
        'TURING_BASE_URL': settings.TURING_BASE_URL,
        'TURING_ADMIN_USER': settings.TURING_ADMIN_USER,
        'TURING_ADMIN_PASS': settings.TURING_ADMIN_PASS,
        'TURING_BOT_PASS': settings.TURING_BOT_PASS,
    }
    cmd = [
        sys.executable, str(_script_path('avvia_gara_bot.py')),
        str(allenamento.gara_id),
        '--skip-start',
        '--base-url', settings.TURING_BASE_URL,
        '--bot-username', settings.BOT_USERNAME,
        '--bot-file', allenamento.base_file,
        '-N', str(allenamento.num_squadre_umane),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=logf, stderr=logf, stdin=subprocess.DEVNULL,
        start_new_session=True, close_fds=True,
        cwd=str(Path(settings.BASE_DIR).parent), env=env,
    )
    allenamento.runner_pid = proc.pid
    allenamento.runner_log = str(log_path)
    allenamento.avviato_il = timezone.now()
    allenamento.save(update_fields=['runner_pid', 'runner_log', 'avviato_il',
                                    'stato', 'updated_at'])


def user_can_see_allenamento(user, gara):
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    allenamento = getattr(gara, 'allenamento', None)
    if allenamento is None:
        return True
    if allenamento.creato_da_id == user.id or gara.admin_id == user.id:
        return True
    if gara.inseritori.filter(pk=user.pk).exists():
        return True
    return Squadra.objects.filter(gara=gara, consegnatore=user).exists()
