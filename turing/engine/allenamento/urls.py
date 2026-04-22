from django.urls import path

from engine.allenamento.views import (
    AllenamentoCreateView, AllenamentoListView, AllenamentoStartView,
)


urlpatterns = [
    path('', AllenamentoListView.as_view(), name='allenamento-list'),
    path('crea/', AllenamentoCreateView.as_view(), name='allenamento-create'),
    path('<int:pk>/avvia/', AllenamentoStartView.as_view(), name='allenamento-start'),
]
