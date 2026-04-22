from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/aggiorna l'utente bot_driver usato dagli allenamenti."

    def handle(self, *args, **options):
        User = get_user_model()
        username = settings.BOT_USERNAME
        password = settings.TURING_BOT_PASS
        if not password:
            self.stderr.write(self.style.ERROR(
                "TURING_BOT_PASS non configurata: impossibile creare bot_driver."))
            return
        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_active = True
        user.save()
        verb = "creato" if created else "aggiornato"
        self.stdout.write(self.style.SUCCESS(f"Utente {username!r} {verb}."))
