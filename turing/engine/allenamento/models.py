from django.conf import settings
from django.db import models

from engine.models import Gara


class Allenamento(models.Model):
    STATI = (
        ('da_iniziare', 'Da iniziare'),
        ('in_corso', 'In corso'),
        ('finita', 'Finita'),
        ('errore', 'Errore'),
    )

    gara = models.OneToOneField(Gara, on_delete=models.CASCADE, related_name='allenamento')
    creato_da = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='allenamenti_creati')
    base_anno = models.PositiveSmallIntegerField()
    base_nome = models.CharField(max_length=100)
    base_file = models.CharField(max_length=500)
    num_squadre_umane = models.PositiveSmallIntegerField()
    stato = models.CharField(max_length=20, choices=STATI, default='da_iniziare')
    runner_pid = models.PositiveIntegerField(null=True, blank=True)
    runner_log = models.CharField(max_length=500, blank=True)
    avviato_il = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'allenamento'
        verbose_name_plural = 'allenamenti'
        ordering = ['-created_at']

    def __str__(self):
        return f'Allenamento "{self.gara.nome}" ({self.get_stato_display()})'

    def runner_alive(self):
        if not self.runner_pid:
            return False
        import os
        try:
            os.kill(self.runner_pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
