from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static

from engine.views import *

app_name = 'engine'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('gara/new', CreaGaraView.as_view(), name='gara-new'),
    path('gara/upload', UploadGaraView.as_view(), name='gara-upload'),
    path('gara/<int:pk>', GaraView.as_view(), name='gara-detail'),
    path('gara/<int:pk>/admin', GaraAdminView.as_view(), name='gara-admin'),
    path('gara/<int:pk>/parametri', GaraParametriView.as_view(), name='gara-parametri'),
    path('gara/<int:pk>/risposte', GaraRisposteView.as_view(), name='gara-risposte'),
    path('gara/<int:pk>/squadre', GaraSquadreView.as_view(), name='gara-squadre'),
    path('gara/<int:pk>/download', DownloadGaraView.as_view(), name='gara-download'),
    path('gara/<int:pk>/reset', GaraResetView.as_view(), name='gara-reset'),
    path('gara/<int:pk>/delete', GaraDeleteView.as_view(), name='gara-delete'),
    path('gara/<int:pk>/pause', GaraPauseView.as_view(), name='gara-pause'),
    path('gara/<int:pk>/resume', GaraResumeView.as_view(), name='gara-resume'),
    path('query/<int:pk>', QueryView.as_view(), name='query'),
    path('inserisci/<int:pk>', InserimentoView.as_view(), name='inserimento'),
    path('evento/<int:pk>/modifica', ModificaEventoView.as_view(), name='evento-modifica'),
    path('evento/<int:pk>/elimina', EliminaEventoView.as_view(), name='evento-elimina'),
    path('status/<int:pk>', StatusView.as_view(), name='status'),
    path('classifica/<int:pk>/squadre', ClassificaView.as_view(), name='classifica-squadre'),
    path('classifica/<int:pk>/problemi', PuntiProblemiView.as_view(), name='classifica-problemi'),
    path('classifica/<int:pk>/stato', StatoProblemiView.as_view(), name='classifica-stato'),
    path('classifica/<int:pk>/unica', UnicaView.as_view(), name='classifica-unica'),
    path('classifica/<int:pk>/scorrimento', ScorrimentoView.as_view(), name='classifica-scorrimento'),
    path('about', AboutView.as_view(), name="about"),
    path('now', NowView.as_view(), name="now"),
    path('allenamenti/', include('engine.allenamento.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
