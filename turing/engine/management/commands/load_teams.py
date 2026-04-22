from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from engine.models import Gara, Squadra

import csv
import argparse

User = get_user_model()


class Command(BaseCommand):
    help = "Loads the teams from the specified file"

    def add_arguments(self, parser):
        parser.add_argument("gara_id", type=int)
        parser.add_argument("filename", type=argparse.FileType())

    def handle(self, *args, **options):
        reader = csv.DictReader(options["filename"])
        try:
            gara = Gara.objects.get(pk=options["gara_id"])
        except Gara.DoesNotExist:
            raise CommandError("No gara found")
        idx = 1
        for row in reader:
            username = row["username"]
            psw = row["password"]
            nome = row["squadra"]

            try:
                user = User.objects.get(username=username)
                user.set_password(psw)
                user.save()
            except:
                user = User.objects.create_user(username, password=psw)
                user.save()

            try:
                sq = Squadra(gara=gara, nome=nome, num=idx, consegnatore=user)
                sq.save()
            except:
                pass

            idx += 1
