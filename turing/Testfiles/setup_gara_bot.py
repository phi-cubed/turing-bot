#!/usr/bin/env python3
"""Crea una gara Turing per l'allenamento contro squadre bot.

Effettua via HTTP come admin:
  - verifica/crea l'utente bot condiviso
  - crea una gara con N squadre reali + M squadre bot (prese dal file JSON)
  - assegna l'utente bot come consegnatore delle squadre bot
  - aggiunge l'utente bot come inseritore della gara
  - opzionale: crea gli utenti reali dal CSV e li assegna come consegnatori

Le squadre bot sono nominate `<nome_originale>_bot`.

Esempio:
  python Testfiles/setup_gara_bot.py \\
      --admin-username admin --admin-password admin \\
      --bot-password 'BotPass!2026' \\
      --nome "Allenamento Disfida" -N 4 \\
      --bot-file mathrace_interaction/data/2025/disfida.json \\
      --utenti-reali-csv Testfiles/Credenziali.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from turing_client import TuringClient, TuringError, die


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default=os.environ.get("TURING_BASE_URL", "http://localhost:8000"))
    p.add_argument("--admin-username", default=os.environ.get("TURING_ADMIN_USER"),
                   help="Username admin (staff). Default da env TURING_ADMIN_USER.")
    p.add_argument("--admin-password", default=os.environ.get("TURING_ADMIN_PASS"),
                   help="Password admin. Default da env TURING_ADMIN_PASS.")
    p.add_argument("--bot-username", default="bot_driver")
    p.add_argument("--bot-password", default=os.environ.get("TURING_BOT_PASS"),
                   help="Password del bot user. Default da env TURING_BOT_PASS.")
    p.add_argument("--nome", required=True, help="Nome della gara")
    p.add_argument("-N", "--num-squadre-reali", type=int, required=True)
    p.add_argument("--num-problemi", type=int, default=None,
                   help="Override del numero problemi. Default dal JSON.")
    p.add_argument("--bot-file", required=True, type=Path,
                   help="Path al file JSON di gara (es. disfida.json)")
    p.add_argument("--nomi-squadre-reali", type=Path, default=None,
                   help="File txt con N nomi (default: 'Squadra i')")
    p.add_argument("--nomi-problemi", type=Path, default=None)
    p.add_argument("--risposte-problemi", type=Path, default=None)
    p.add_argument("--utenti-reali-csv", type=Path, default=None,
                   help="CSV 'username,password,squadra' come load_teams.py")
    p.add_argument("--gara-admin-username", default=None,
                   help="Username Django che diventera' admin della gara creata "
                        "(default: --admin-username).")
    p.add_argument("--consegnatori-esistenti", default=None,
                   help="CSV 'username:num,username:num' per assegnare utenti "
                        "gia' esistenti come consegnatori delle squadre reali, "
                        "senza crearne di nuovi (alternativa a --utenti-reali-csv).")
    # Overrides parametri gara (default dal JSON)
    p.add_argument("--durata-minuti", type=int, default=None)
    p.add_argument("--durata-blocco-minuti", type=int, default=None)
    p.add_argument("--n-blocco", type=int, default=None)
    p.add_argument("--k-blocco", type=int, default=None)
    p.add_argument("--fixed-bonus", default=None,
                   help="CSV interi (es. '20,15,10'), max 10 valori")
    p.add_argument("--super-mega-bonus", default=None)
    p.add_argument("--no-jolly", action="store_true",
                   help="Disabilita i jolly (override del JSON).")
    return p.parse_args()


def read_lines(path: Path | None) -> list[str] | None:
    if path is None:
        return None
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() != ""]


def format_duration(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}:00"


def bonus_to_inputs(field_name: str, csv_value: str) -> dict[str, str]:
    """Expand 'a,b,c' into {field_0: a, field_1: b, field_2: c, field_3..9: ''}.

    Matches IntegerMultiWidget which renders 10 text inputs named <field>_<i>.
    """
    values = [v.strip() for v in csv_value.split(",")] if csv_value else []
    out = {}
    for i in range(10):
        out[f"{field_name}_{i}"] = values[i] if i < len(values) else ""
    return out


_GARA_ADMIN_RE = re.compile(r"/engine/gara/(\d+)/admin")


def extract_form_data(
    soup: BeautifulSoup, form_selector: str | None = None
) -> list[tuple[str, str]]:
    """Return a list of (name, value) pairs from inputs/selects/textareas in a form.

    Skips submit buttons and unchecked checkboxes. Select elements emit their
    selected options (or the first option if none selected, matching browser behavior).

    If no selector is provided, picks the form with the most named fields
    (skipping the site-wide logout form, which has ~1 field).
    """
    if form_selector:
        form = soup.select_one(form_selector)
    else:
        candidates = [
            f for f in soup.find_all("form")
            if not (f.get("action") or "").endswith("/accounts/logout/")
        ]
        form = max(candidates, key=lambda f: len(f.find_all(["input", "select", "textarea"])),
                   default=None)
    if form is None:
        raise TuringError("Form non trovato nella pagina")
    pairs: list[tuple[str, str]] = []
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        typ = (inp.get("type") or "text").lower()
        if typ in ("submit", "button", "image", "reset", "file"):
            continue
        if typ in ("checkbox", "radio"):
            if inp.has_attr("checked"):
                pairs.append((name, inp.get("value", "on")))
        else:
            pairs.append((name, inp.get("value", "")))
    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        selected = [o for o in sel.find_all("option") if o.has_attr("selected")]
        if not selected and not sel.has_attr("multiple"):
            first = sel.find("option")
            if first is not None and first.get("value") not in (None, ""):
                pairs.append((name, first.get("value")))
        for opt in selected:
            pairs.append((name, opt.get("value", "")))
    for ta in form.find_all("textarea"):
        name = ta.get("name")
        if not name:
            continue
        pairs.append((name, ta.get_text()))
    return pairs


def set_pair(pairs: list[tuple[str, str]], name: str, value: str) -> None:
    """Replace all existing (name, *) tuples with a single (name, value)."""
    pairs[:] = [(n, v) for (n, v) in pairs if n != name]
    pairs.append((name, value))


def add_pair(pairs: list[tuple[str, str]], name: str, value: str) -> None:
    pairs.append((name, value))


def remove_name(pairs: list[tuple[str, str]], name: str) -> None:
    pairs[:] = [(n, v) for (n, v) in pairs if n != name]


def main() -> int:
    args = parse_args()
    if not args.admin_username or not args.admin_password:
        die("Servono --admin-username e --admin-password (o env TURING_ADMIN_USER/PASS)")
    if not args.bot_password:
        die("Serve --bot-password (o env TURING_BOT_PASS)")

    # --- Legge file JSON bot ---
    try:
        bot_json = json.loads(args.bot_file.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Impossibile leggere {args.bot_file}: {e}")

    num_problemi = args.num_problemi if args.num_problemi is not None else bot_json.get("num_problemi")
    if num_problemi is None:
        die("Devi specificare --num-problemi (il JSON non lo contiene).")

    if "squadre" not in bot_json or not bot_json["squadre"]:
        die("Il file bot non contiene 'squadre'.")

    bot_squadre = bot_json["squadre"]
    M = len(bot_squadre)
    N = args.num_squadre_reali
    if N <= 0:
        die("--num-squadre-reali deve essere > 0")

    # --- Nomi squadre reali ---
    nomi_reali = read_lines(args.nomi_squadre_reali)
    if nomi_reali is None:
        nomi_reali = [f"Squadra {i+1}" for i in range(N)]
    elif len(nomi_reali) != N:
        die(f"--nomi-squadre-reali ha {len(nomi_reali)} righe ma N={N}")

    # --- Nomi squadre bot con suffisso _bot ---
    nomi_bot = [f"{s['nome']}_bot" for s in bot_squadre]

    # --- CSV utenti reali (opzionale) ---
    utenti_reali: list[dict[str, str]] = []
    if args.utenti_reali_csv is not None:
        with args.utenti_reali_csv.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # salta righe vuote
                if not row.get("username", "").strip():
                    continue
                utenti_reali.append({
                    "username": row["username"].strip(),
                    "password": row.get("password", "").strip(),
                    "squadra": row.get("squadra", "").strip(),
                })
        if len(utenti_reali) > N:
            die(f"Il CSV ha {len(utenti_reali)} righe ma N={N}")

    # --- File contenuti per upload ---
    nomi_squadre_blob = "\n".join(nomi_reali + nomi_bot).encode("utf-8")
    nomi_problemi_blob = None
    risposte_blob = None
    if args.nomi_problemi is not None:
        nomi_problemi_lines = read_lines(args.nomi_problemi)
        if len(nomi_problemi_lines) != num_problemi:
            die(f"--nomi-problemi: {len(nomi_problemi_lines)} righe vs num_problemi {num_problemi}")
        nomi_problemi_blob = "\n".join(nomi_problemi_lines).encode("utf-8")
    if args.risposte_problemi is not None:
        risposte_lines = read_lines(args.risposte_problemi)
        if len(risposte_lines) != num_problemi:
            die(f"--risposte-problemi: {len(risposte_lines)} righe vs num_problemi {num_problemi}")
        risposte_blob = "\n".join(risposte_lines).encode("utf-8")
    if (nomi_problemi_blob is None) != (risposte_blob is None):
        die("Se si passa uno tra --nomi-problemi e --risposte-problemi, vanno passati entrambi")

    # --- Parametri gara (default dal JSON, override CLI) ---
    durata_min = args.durata_minuti if args.durata_minuti is not None else bot_json.get("durata", 120)
    durata_blocco_min = args.durata_blocco_minuti if args.durata_blocco_minuti is not None else bot_json.get("durata_blocco", 20)
    n_blocco = args.n_blocco if args.n_blocco is not None else bot_json.get("n_blocco", 2)
    k_blocco = args.k_blocco if args.k_blocco is not None else bot_json.get("k_blocco", 1)
    fixed_bonus = args.fixed_bonus if args.fixed_bonus is not None else bot_json.get("fixed_bonus", "20,15,10,8,6,5,4,3,2,1")
    super_mega = args.super_mega_bonus if args.super_mega_bonus is not None else bot_json.get("super_mega_bonus", "100,60,40,30,20,10")
    jolly_enabled = (not args.no_jolly) and bool(bot_json.get("jolly", True))

    # --- Login admin + check accesso /admin/ ---
    client = TuringClient(base_url=args.base_url)
    try:
        client.login(args.admin_username, args.admin_password)
        client.ensure_admin_access()
    except TuringError as e:
        die(str(e))
    print(f"[setup] Login come admin {args.admin_username!r} ok.")

    # --- Ensure bot user ---
    try:
        bot_pk = client.ensure_user(args.bot_username, change_create=False)
    except TuringError as e:
        die(f"Setup utente bot fallito: {e}")
    print(f"[setup] Utente bot {args.bot_username!r} pronto (pk={bot_pk}).")

    # --- Admin PK per il form gara ---
    admin_pk = client.find_user_pk(args.admin_username)
    if admin_pk is None:
        die(f"Admin {args.admin_username!r} non trovato nella UI admin.")
    gara_admin_username = args.gara_admin_username or args.admin_username
    gara_admin_pk = client.find_user_pk(gara_admin_username)
    if gara_admin_pk is None:
        die(f"Utente admin gara {gara_admin_username!r} non trovato.")

    # --- POST /engine/gara/new ---
    print("[setup] Creazione gara...")
    token, _ = client.get_csrf("/engine/gara/new")
    data: list[tuple[str, str]] = [
        ("csrfmiddlewaretoken", token),
        ("nome", args.nome),
        ("durata", format_duration(durata_min)),
        ("durata_blocco", format_duration(durata_blocco_min)),
        ("n_blocco", str(n_blocco)),
        ("k_blocco", str(k_blocco)),
        ("num_problemi", str(num_problemi)),
        ("punteggio_iniziale_squadre", ""),
        ("admin", str(gara_admin_pk)),
        ("num_squadre", str(N + M)),
    ]
    if jolly_enabled:
        data.append(("jolly", "on"))
    for k, v in bonus_to_inputs("fixed_bonus", fixed_bonus).items():
        data.append((k, v))
    for k, v in bonus_to_inputs("super_mega_bonus", super_mega).items():
        data.append((k, v))

    files: dict[str, tuple[str, bytes, str]] = {
        "nomi_squadre_upload": ("nomi_squadre.txt", nomi_squadre_blob, "text/plain"),
    }
    if nomi_problemi_blob is not None:
        files["nomi_problemi_upload"] = ("nomi_problemi.txt", nomi_problemi_blob, "text/plain")
    if risposte_blob is not None:
        files["risposte_problemi_upload"] = ("risposte_problemi.txt", risposte_blob, "text/plain")

    r = client.post("/engine/gara/new", data=data, files=files,
                    referer="/engine/gara/new", allow_redirects=False)
    if r.status_code not in (301, 302):
        soup = BeautifulSoup(r.text, "html.parser")
        errors = [e.get_text(" ", strip=True) for e in soup.find_all(class_="errorlist")]
        die(f"POST /engine/gara/new fallito (status {r.status_code}): {' | '.join(errors) or r.text[:500]}")
    location = r.headers.get("Location", "")
    m = _GARA_ADMIN_RE.search(location)
    if not m:
        die(f"Impossibile estrarre gara_id dal redirect: {location!r}")
    gara_id = int(m.group(1))
    print(f"[setup] Gara creata: id={gara_id}")

    # --- Aggiunge bot user a gara.inseritori via /parametri ---
    print("[setup] Aggiungo bot user agli inseritori...")
    param_path = f"/engine/gara/{gara_id}/parametri"
    r = client.get(param_path)
    if r.status_code != 200:
        die(f"GET {param_path} -> {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")
    pairs = extract_form_data(soup)
    # Garantisci che bot_pk sia tra gli inseritori (il campo è multi-value).
    existing_inseritori = {v for (n, v) in pairs if n == "inseritori"}
    if str(bot_pk) not in existing_inseritori:
        pairs.append(("inseritori", str(bot_pk)))
    r = client.post(param_path, data=pairs, referer=param_path, allow_redirects=False)
    if r.status_code not in (301, 302):
        soup = BeautifulSoup(r.text, "html.parser")
        errors = [e.get_text(" ", strip=True) for e in soup.find_all(class_="errorlist")]
        die(f"POST {param_path} fallito (status {r.status_code}): {' | '.join(errors) or r.text[:500]}")

    # --- Crea utenti reali (se CSV) ---
    real_user_pks_by_num: dict[int, int] = {}
    for i, u in enumerate(utenti_reali, start=1):
        try:
            pk = client.ensure_user(u["username"], u["password"])
        except TuringError as e:
            die(f"Setup utente reale {u['username']!r} fallito: {e}")
        real_user_pks_by_num[i] = pk
        print(f"[setup] Utente reale {u['username']!r} (pk={pk}) -> squadra num={i}")

    # --- Consegnatori esistenti (senza crearli) ---
    if args.consegnatori_esistenti:
        for entry in args.consegnatori_esistenti.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" not in entry:
                die(f"--consegnatori-esistenti: entry {entry!r} non nel formato username:num")
            username, num_str = entry.rsplit(":", 1)
            try:
                num = int(num_str)
            except ValueError:
                die(f"--consegnatori-esistenti: num non intero in {entry!r}")
            if num < 1 or num > N:
                die(f"--consegnatori-esistenti: num={num} fuori range [1, {N}]")
            pk = client.find_user_pk(username.strip())
            if pk is None:
                die(f"--consegnatori-esistenti: utente {username!r} non trovato")
            real_user_pks_by_num[num] = pk
            print(f"[setup] Consegnatore esistente {username!r} (pk={pk}) -> squadra num={num}")

    # --- Assegna consegnatori via /squadre formset ---
    print("[setup] Assegno consegnatori alle squadre...")
    sq_path = f"/engine/gara/{gara_id}/squadre"
    r = client.get(sq_path)
    if r.status_code != 200:
        die(f"GET {sq_path} -> {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")
    pairs = extract_form_data(soup)

    # Individua gli indici delle sotto-form dal management form e dai campi form-i-num
    num_by_idx: dict[int, int] = {}
    idx_re = re.compile(r"^form-(\d+)-num$")
    for name, value in pairs:
        m = idx_re.match(name)
        if m and value:
            num_by_idx[int(m.group(1))] = int(value)

    if len(num_by_idx) != N + M:
        die(f"Formset squadre attese {N+M}, trovate {len(num_by_idx)}")

    # Per ogni squadra decidi il consegnatore da impostare.
    for idx, num in num_by_idx.items():
        field = f"form-{idx}-consegnatore"
        if num > N:
            # squadra bot -> bot_pk
            set_pair(pairs, field, str(bot_pk))
        else:
            # squadra reale: se CSV fornito, assegna; altrimenti lascia vuoto
            target_pk = real_user_pks_by_num.get(num)
            set_pair(pairs, field, str(target_pk) if target_pk is not None else "")

    r = client.post(sq_path, data=pairs, referer=sq_path, allow_redirects=False)
    if r.status_code not in (301, 302):
        soup = BeautifulSoup(r.text, "html.parser")
        errors = [e.get_text(" ", strip=True) for e in soup.find_all(class_="errorlist")]
        die(f"POST {sq_path} fallito (status {r.status_code}): {' | '.join(errors) or r.text[:500]}")

    # --- Output finale ---
    marker_path = Path(__file__).parent / ".ultima_gara_bot"
    marker_path.write_text(
        f"gara_id={gara_id}\n"
        f"bot_file={args.bot_file.resolve()}\n"
        f"num_squadre_reali={N}\n"
        f"bot_username={args.bot_username}\n"
        f"bot_password={args.bot_password}\n"
        f"admin_username={args.admin_username}\n"
        f"admin_password={args.admin_password}\n"
        f"base_url={args.base_url}\n",
        encoding="utf-8",
    )

    print()
    print(f"gara_id={gara_id}")
    print(f"  squadre reali: {N}  (num 1..{N})")
    print(f"  squadre bot:   {M}  (num {N+1}..{N+M}, suffisso _bot)")
    print(f"  bot user:      {args.bot_username!r} (consegnatore + inseritore)")
    if utenti_reali:
        print(f"  utenti reali: {len(utenti_reali)} creati dal CSV")
    print()
    print("Per avviare la gara e i bot:")
    print("Per avviare la gara e i bot basta eseguire:")
    print("  python Testfiles/avvia_gara_bot.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
