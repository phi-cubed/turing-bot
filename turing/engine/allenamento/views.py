from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from engine.allenamento.forms import AllenamentoCreateForm
from engine.allenamento.models import Allenamento
from engine.allenamento.services import (
    run_setup_gara_bot, spawn_avvia_gara_bot,
)
from engine.models import Gara


class AllenamentoListView(LoginRequiredMixin, TemplateView):
    template_name = 'allenamento/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mine = list(Allenamento.objects.filter(creato_da=self.request.user)
                    .select_related('gara'))
        da_iniziare, in_corso, archivio, errore = [], [], [], []
        for a in mine:
            if a.stato == 'errore':
                errore.append(a)
            elif a.gara.inizio is None:
                da_iniziare.append(a)
            elif a.gara.finished():
                archivio.append(a)
            else:
                in_corso.append(a)
        ctx['allenamenti_da_iniziare'] = da_iniziare
        ctx['allenamenti_in_corso'] = in_corso
        ctx['allenamenti_archivio'] = archivio
        ctx['allenamenti_errore'] = errore
        return ctx


class AllenamentoCreateView(LoginRequiredMixin, FormView):
    template_name = 'allenamento/create.html'
    form_class = AllenamentoCreateForm
    success_url = reverse_lazy('engine:allenamento-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        cd = form.cleaned_data
        try:
            gara_id = run_setup_gara_bot(cd, self.request.user)
        except RuntimeError as e:
            messages.error(self.request,
                           f'Errore nella creazione dell\'allenamento: {e}')
            return self.form_invalid(form)
        paths = cd['base_paths']
        with transaction.atomic():
            Gara.objects.filter(pk=gara_id).update(admin=self.request.user)
            Allenamento.objects.create(
                gara_id=gara_id,
                creato_da=self.request.user,
                base_anno=paths['anno'],
                base_nome=paths['nome'],
                base_file=str(paths['json']),
                num_squadre_umane=cd['num_squadre_umane'],
                stato='da_iniziare',
            )
        messages.success(self.request, 'Allenamento creato.')
        return super().form_valid(form)


class AllenamentoStartView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'allenamento/start.html'
    form_class = forms.Form
    success_url = reverse_lazy('engine:allenamento-list')

    def get_allenamento(self):
        if not hasattr(self, '_allenamento'):
            self._allenamento = get_object_or_404(
                Allenamento.objects.select_related('gara'), pk=self.kwargs['pk'],
            )
        return self._allenamento

    def test_func(self):
        a = self.get_allenamento()
        u = self.request.user
        return a.creato_da_id == u.id or u.can_administrate(a.gara)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['allenamento'] = self.get_allenamento()
        return ctx

    def form_valid(self, form):
        a = self.get_allenamento()
        with transaction.atomic():
            updated = Allenamento.objects.filter(
                pk=a.pk, stato='da_iniziare',
            ).update(stato='in_corso')
            if updated == 0:
                messages.error(self.request, 'Allenamento gi\u00e0 avviato o non disponibile.')
                return redirect(self.success_url)
            a.refresh_from_db()
            a.gara.inizio = timezone.now()
            a.gara.save(update_fields=['inizio'])
            spawn_avvia_gara_bot(a)
        messages.success(self.request, 'Allenamento avviato.')
        return super().form_valid(form)
