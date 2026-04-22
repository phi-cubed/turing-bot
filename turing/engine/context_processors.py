from django.utils import timezone
from django.conf import settings

from engine.models import Gara, SystemSettings


def _is_allenamento(gara):
    return hasattr(gara, 'allenamento')


def _can_see_allenamento(user, gara):
    from engine.allenamento.services import user_can_see_allenamento
    return user_can_see_allenamento(user, gara)


def get_gare(user):
    gare = Gara.objects.filter(inizio__isnull=False).order_by("-inizio", "-id")
    loraesatta = timezone.now()
    attive = []
    archivio = []
    for g in gare:
        if _is_allenamento(g) and not _can_see_allenamento(user, g):
            continue
        if g.sospensione is not None:
            attive.append(g)
        elif g.get_ora_fine() < loraesatta:
            archivio.append(g)
        else:
            attive.append(g)
    da_iniziare_qs = Gara.objects.filter(
        inizio__isnull=True, allenamento__isnull=True,
    ).order_by("-id")
    return attive, archivio, list(da_iniziare_qs)


def gare(request):
    attive, archivio, da_iniziare = get_gare(request.user)

    can_view_archive = False
    try:
        sys_settings = SystemSettings.get_settings()
        if sys_settings.is_archive_public:
            can_view_archive = True
        elif request.user.is_authenticated:
            if request.user.is_superuser or sys_settings.allowed_users.filter(pk=request.user.pk).exists():
                can_view_archive = True
    except Exception:
        # In caso di migrazioni non ancora applicate
        can_view_archive = True

    if not can_view_archive:
        archivio = []

    return {
        "gare_attive": attive,
        "gare_archivio": archivio,
        "gare_da_iniziare": da_iniziare,
        "can_view_archive": can_view_archive
    }


def export_settings(request):
    data = {
        "registration_open": settings.REGISTRATION_OPEN
    }
    return data
