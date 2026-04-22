from django.views.generic import TemplateView, FormView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import login, authenticate
from django import forms
from django.db.models import F

from engine.models import User, Gara, Soluzione, Squadra, Evento, Consegna, Jolly, Bonus
from engine.forms import SignUpForm, RispostaFormset, SquadraFormset, InserimentoForm,\
    ModificaConsegnaForm, ModificaJollyForm, ModificaBonusForm, UploadGaraForm, QueryForm, CreaGaraForm, ModificaGaraForm
from engine.formfields import IntegerMultiField

import logging
logger = logging.getLogger(__name__)


class CheckPermissionsMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin che controlla che l'utente sia autenticato e che soddisfi la funzione test_func.
    """
    pass


class IndexView(TemplateView):
    """ Pagina principale """
    template_name = "index.html"


class AboutView(TemplateView):
    """ Pagina 'chi siamo' """
    template_name = "about.html"

class NowView(TemplateView):
    """ Tempo corrente"""
    template_name = "now.html"


class SignUpView(FormView):
    """ Pagina di registrazione """
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = "/engine/"

    def form_valid(self, form):
        user = form.save()
        raw_password = form.cleaned_data.get('password1')
        user = authenticate(username=user.username, password=raw_password)
        login(self.request, user)
        return super().form_valid(form)


class SignUpClosedView(TemplateView):
    """ Pagina per quando la registrazione è disabilitata """
    template_name = "registration/signup_closed.html"


#####################
#    VIEWS GARA     #
#####################

class CreaOModificaGaraView(SuccessMessageMixin):
    """ Superclasse per astrarre metodi comuni a CreaGaraView e GaraParametriView"""
    model = Gara

    def get_form(self):
        form = super().get_form()
        # Cambia i campi per i bonus per avere caselle multiple
        form.fields['fixed_bonus'] = IntegerMultiField(
            required=False, require_all_fields=False,
            help_text=form.fields['fixed_bonus'].help_text,
            label=form.fields['fixed_bonus'].label,
            initial=form.fields['fixed_bonus'].initial)
        form.fields['super_mega_bonus'] = IntegerMultiField(
            required=False, require_all_fields=False,
            help_text=form.fields['super_mega_bonus'].help_text,
            label=form.fields['super_mega_bonus'].label,
            initial=form.fields['super_mega_bonus'].initial)
        return form

    def get_success_url(self, **kwargs):
        return reverse("engine:gara-admin", kwargs={'pk': self.object.pk})


class CreaGaraView(PermissionRequiredMixin, CreaOModificaGaraView, FormView, CreateView):
    """ View per la creazione di una gara """
    form_class = CreaGaraForm
    template_name = "gara/create.html"
    success_message = 'Gara creata con successo!'
    permission_required = "engine.add_gara"

    def get_form_kwargs(self):
        kwargs = super(CreaGaraView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.admin = self.request.user
        response = super().form_valid(form)
        gara = form.instance
        nomi_squadre = form.cleaned_data.get("nomi_squadre")
        nomi_problemi = form.cleaned_data.get("nomi_problemi")
        risposte_problemi = form.cleaned_data.get("risposte_problemi")
        for (i, nome) in enumerate(nomi_squadre):
            Squadra.objects.create(gara=gara, num=i + 1, nome=nome)
        for i in range(gara.num_problemi):
            Soluzione.objects.create(gara=gara, problema=i + 1, nome=nomi_problemi[i], risposta=risposte_problemi[i])
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Errore: gara non creata correttamente")
        return super().form_invalid(form)


class GaraParametriView(CheckPermissionsMixin, CreaOModificaGaraView, FormView, UpdateView):
    """ View per cambiare i parametri di una gara """
    form_class = ModificaGaraForm
    template_name = "gara/modify.html"
    success_message = 'Parametri di gara salvati con successo!'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['num_squadre'] = len(self.get_object().squadre.all())
        return kwargs

    def test_func(self):
        # Salva la gara dentro self.object, così siamo sicuri
        # che sia stata validata e non viene chiamato get_object() due volte.
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    @transaction.atomic   # visto che creiamo nuovi problemi E aggiorniamo gara.num_problemi
    def form_valid(self, form):
        gara_nuova = form.instance
        gara_vecchia = self.get_object()

        num_squadre_nuova = form.cleaned_data.get("num_squadre")
        num_squadre_vecchia = len(gara_vecchia.squadre.all())
        num_problemi_nuova = gara_nuova.num_problemi
        num_problemi_vecchia = gara_vecchia.num_problemi

        if num_squadre_nuova > num_squadre_vecchia:
            # dobbiamo creare nuove squadre
            for i in range(num_squadre_vecchia+1, num_squadre_nuova+1):
                Squadra.objects.create(gara=gara_vecchia, num=i, nome="Squadra {}".format(i))
        elif num_squadre_nuova < num_squadre_vecchia:
            # dobbiamo cancellare squadre
            Squadra.objects.filter(gara=gara_vecchia, num__range=(num_squadre_nuova+1, num_squadre_vecchia)).delete()

        if num_problemi_nuova > num_problemi_vecchia:
            # dobbiamo creare nuovi problemi
            for i in range(num_problemi_vecchia+1, num_problemi_nuova+1):
                Soluzione.objects.create(gara=gara_vecchia, problema=i, nome="Problema {}".format(i))
        elif num_problemi_nuova < num_problemi_vecchia:
            # dobbiamo cancellare problemi
            Soluzione.objects.filter(gara=gara_vecchia, problema__range=(num_problemi_nuova+1, num_problemi_vecchia)).delete()

        response = super().form_valid(form) # committa le modifiche
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Errore: parametri di gara non salvati correttamente")
        return super().form_invalid(form)


class GaraView(DetailView):
    """ View con riepilogo di una gara """
    model = Gara
    template_name = "gara/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["can_insert"] = self.request.user.can_insert_gara(self.object)
            context["is_admin"] = self.request.user.can_administrate(self.object)
        return context


class GaraAdminView(CheckPermissionsMixin, DetailView):
    """ View per l'amministrazione di una gara """
    model = Gara
    template_name = "gara/detail_admin.html"

    def test_func(self):
        # Salva la gara dentro self.object, così siamo sicuri
        # che sia stata validata e non viene chiamato get_object() due volte.
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['num_eventi'] = len(self.object.eventi.all())
        return context

    def post(self, request, *args, **kwargs):
        if "inizia" in request.POST:
            loraesatta = timezone.now()
            gara = self.object
            gara.inizio = loraesatta
            gara.save()
        return super().get(self, request)


class GaraRisposteView(CheckPermissionsMixin, SuccessMessageMixin, FormView, DetailView):
    """ View per l'inserimento delle soluzioni esatte di una gara """
    model = Gara
    template_name = 'gara/risposte.html'
    success_message = 'Soluzioni inserite con successo!'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    def get_success_url(self, **kwargs):
        return reverse("engine:gara-admin", kwargs={'pk': self.object.pk})

    def get_form(self):
        if self.request.POST:
            return RispostaFormset(self.request.POST)
        return RispostaFormset(queryset=Soluzione.objects.filter(gara=self.object))

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Errore: soluzioni non inserite correttamente")
        return super().form_invalid(form)


class GaraSquadreView(CheckPermissionsMixin, SuccessMessageMixin, FormView, DetailView):
    """ View per l'inserimento delle squadre partecipanti ad una gara """
    model = Gara
    template_name = 'gara/squadre.html'
    success_message = 'Squadre inserite con successo!'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    def get_success_url(self, **kwargs):
        return reverse("engine:gara-admin", kwargs={'pk': self.object.pk})

    def get_form(self):
        users = User.objects.all()
        if self.request.POST:
            return SquadraFormset(self.request.POST, users_qs=users)
        return SquadraFormset(queryset=self.object.squadre.all(), users_qs=users)

    def form_valid(self, form):
        for res in form.cleaned_data:
            sq = self.object.squadre.filter(num=res['num']).first()
            if sq:
                sq.nome = res['nome']
                sq.ospite = res['ospite']
                sq.consegnatore = res['consegnatore']
            else:
                sq = Squadra(gara=self.object, num=res['num'], nome=res['nome'], ospite=res['ospite'], consegnatore=res['consegnatore'])
            sq.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Errore: squadre non inserite correttamente")
        return super().form_invalid(form)


class UploadGaraView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    """ Importa una gara tramite l'upload di un file JSON """
    form_class = UploadGaraForm
    template_name = "gara/upload.html"
    success_message = "Gara caricata con successo!"
    permission_required = "engine.add_gara"

    def get_success_url(self):
        return reverse("engine:gara-detail", kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        self.object = Gara.create_from_dict(form.cleaned_data["gara_json"])
        self.object.admin = self.request.user
        self.object.eventi.update(creatore=self.request.user)
        self.object.save()
        return super().form_valid(form)


class DownloadGaraView(DetailView):
    """ Serializza la gara e crea un json da scaricare """
    model = Gara

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        data = self.object.dump_to_json()
        response = HttpResponse(data, content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}.json'.format(self.object.nome)
        return response


class GaraResetView(CheckPermissionsMixin, SuccessMessageMixin, FormView, DetailView):
    """ View per il reset di una gara """
    model = Gara
    form_class = forms.Form
    template_name = "gara/reset.html"
    success_message = 'Reset gara avvenuto con successo!'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    @transaction.atomic
    def form_valid(self, form):
        gara = self.object
        Jolly.objects.filter(gara=gara).delete()
        Jolly.history.filter(gara=gara).delete()
        Consegna.objects.filter(gara=gara).delete()
        Consegna.history.filter(gara=gara).delete()
        Bonus.objects.filter(gara=gara).delete()
        Bonus.history.filter(gara=gara).delete()
        gara.inizio = None
        gara.save()
        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        return reverse("engine:gara-admin", kwargs={'pk': self.object.pk})


class GaraDeleteView(CheckPermissionsMixin, SuccessMessageMixin, FormView, DeleteView):
    """ View per la cancellazione di una gara """
    model = Gara
    form_class = forms.Form
    template_name = "gara/delete.html"
    success_message = 'Gara cancellata con successo!'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    def get_success_url(self, **kwargs):
        return reverse("engine:index")


class GaraPauseView(CheckPermissionsMixin, SuccessMessageMixin, FormView, DetailView):
    """ View per la sospensione di una gara """
    model = Gara
    form_class = forms.Form
    template_name = "gara/pause.html"
    success_message = 'Gara sospesa con successo!'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    def form_valid(self, form):
        gara = self.object
        gara.sospensione = timezone.now()
        gara.save()
        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        return reverse("engine:gara-resume", kwargs={'pk': self.object.pk})


class GaraResumeView(CheckPermissionsMixin, SuccessMessageMixin, FormView, DetailView):
    """ View per la ripresa di una gara """
    model = Gara
    form_class = forms.Form
    template_name = "gara/resume.html"
    success_message = 'Gara ripartita con successo!'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    @transaction.atomic
    def form_valid(self, form):
        gara = self.object
        loraesatta = timezone.now()
        shift = loraesatta - gara.sospensione
        gara.inizio += shift
        gara.eventi.update(orario=F("orario") + shift)
        gara.sospensione = None
        gara.save()
        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        return reverse("engine:gara-admin", kwargs={'pk': self.object.pk})

#######################################
#             VIEW QUERY              #
#######################################

class QueryView(CheckPermissionsMixin, DetailView, FormView):
    """ Query: consente di cercare tra gli eventi """
    model = Gara
    template_name = 'gara/query.html'
    form_class = QueryForm

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_administrate(self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'squadre_inseribili': self.object.get_squadre_inseribili(self.request.user),
            'eventi': self.object.get_all_eventi(self.request.user, self.request.GET.get('id_evento'), self.request.GET.get('num_squadra'), self.request.GET.get('problema'), self.request.GET.get('risposta'))
        })
        return context

    def get_form_kwargs(self):
        kwargs = super(QueryView, self).get_form_kwargs()
        kwargs['gara'] = self.object
        kwargs['querystring_id_evento'] = self.request.GET.get('id_evento', '')
        kwargs['querystring_num_squadra'] = self.request.GET.get('num_squadra', '')
        kwargs['querystring_problema'] = self.request.GET.get('problema', '')
        kwargs['querystring_risposta'] = self.request.GET.get('risposta', '')
        return kwargs


#######################################
#    VIEWS INSERIMENTO E MODIFICA     #
#######################################

class InserimentoView(CheckPermissionsMixin, DetailView, FormView):
    """ View per l'inserimento di una risposta durante la gara """
    model = Gara
    template_name = 'gara/inserimento.html'
    form_class = InserimentoForm

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_insert_gara(self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'squadre_inseribili': self.object.get_squadre_inseribili(self.request.user),
            'eventi_recenti': self.object.get_eventi_recenti(self.request.user, 20),
            'is_admin': self.request.user.can_administrate(self.object)
        })
        return context

    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['gara'] = self.object
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self, **kwargs):
        return reverse("engine:inserimento", kwargs={'pk': self.get_object().pk})

    def form_valid(self, form, *args, **kwargs):
        consegna = form.get_instance()
        consegna.creatore = self.request.user
        res = consegna.maybe_save()
        if res[0]:
            messages.info(self.request, res[1])
        else:
            messages.warning(self.request, res[1])
        return super().form_valid(form)

    def form_invalid(self, form, *args, **kwargs):
        messages.error(self.request, f"Inserimento non riuscito. Vedere l'elenco puntato sotto \"Gara: {self.get_object().nome} - inserimento risposte\" per maggiori dettagli sull'errore.")
        return super().form_invalid(form)


class ModificaEventoView(CheckPermissionsMixin, DetailView, FormView):
    model = Evento
    template_name = "forms/evento_modifica.html"

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_edit_or_delete(self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'squadre_inseribili': self.object.gara.get_squadre_inseribili(self.request.user)
        })
        return context

    def get_form_class(self):
        if self.object.subclass == "Consegna":
            return ModificaConsegnaForm
        elif self.object.subclass == "Jolly":
            return ModificaJollyForm
        elif self.object.subclass == "Bonus":
            return ModificaBonusForm

    def get_initial(self):
        c = self.object.as_child()
        if self.object.subclass == "Consegna":
            initial = {'squadra': c.squadra.num, 'problema': c.problema, 'risposta': c.risposta}
        elif self.object.subclass == "Jolly":
            initial = {'squadra': c.squadra.num, 'problema': c.problema}
        elif self.object.subclass == "Bonus":
            initial = {'squadra': c.squadra.num, 'risposta': c.punteggio}
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['gara'] = self.object.gara
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self, **kwargs):
        return reverse(self.request.GET.get("redirect_to", "engine:inserimento"), kwargs={'pk': self.object.gara.pk})

    def form_valid(self, form):
        self.object = self.object.as_child()
        if self.object.subclass == "Consegna":
            self.object.squadra = form.cleaned_data.get('squadra')
            self.object.problema = form.cleaned_data.get('problema')
            self.object.risposta = form.cleaned_data.get('risposta')
        elif self.object.subclass == "Jolly":
            self.object.squadra = form.cleaned_data.get('squadra')
            self.object.problema = form.cleaned_data.get('problema')
        elif self.object.subclass == "Bonus":
            self.object.squadra = form.cleaned_data.get('squadra')
            self.object.punteggio = form.cleaned_data.get('risposta')
        self.object.creatore = self.request.user
        try:
            self.object.clean()
        except Exception as e:
            messages.warning(self.request, f"Modifica non effettuata. {e}")
        else:
            res = self.object.maybe_save()
            if res[0]:
                messages.info(self.request, "Modifica eseguita con successo")
            else:
                messages.warning(self.request, f"Modifica non effettuata. {res[1]}")
        return super().form_valid(form)


class EliminaEventoView(CheckPermissionsMixin, DeleteView):
    model = Evento

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.can_edit_or_delete(self.object)

    def get_success_url(self):
        return reverse(self.request.GET.get("redirect_to", "engine:inserimento"), kwargs={'pk': self.object.gara.pk})

    def form_valid(self, form):
        messages.info(self.request, "Evento eliminato con successo")
        return super().form_valid(form)


####################################
#    VIEWS STATO E CLASSIFICA     #
###################################

class StatusView(DetailView):
    model = Gara

    def get(self, request, *args, **kwargs):
        gara = self.get_object()
        resp = {}
        resp['last_update'] = gara.get_last_update()

        if "last_consegna_id" in request.GET or "last_jolly_id" in request.GET or "last_bonus_id" in request.GET:
            assert "last_consegna_id" in request.GET
            resp['consegne'] = gara.get_consegne(request.GET["last_consegna_id"])
            assert "last_jolly_id" in request.GET
            resp['jolly'] = gara.get_jolly(request.GET["last_jolly_id"])
            assert "last_bonus_id" in request.GET
            resp['bonus'] = gara.get_bonus(request.GET["last_bonus_id"])
            return JsonResponse(resp)

        resp['nome'] = gara.nome
        resp['inizio'] = gara.inizio
        resp['squadre'] = gara.get_squadre()
        resp['n_prob'] = gara.num_problemi
        resp['problemi'] = gara.get_problemi()
        resp['fixed_bonus'] = gara.fixed_bonus_array
        resp['super_mega_bonus'] = gara.super_mega_bonus_array
        resp['n_blocco'] = gara.n_blocco
        resp['k_blocco'] = gara.k_blocco
        resp['punteggio_iniziale_squadre'] = gara.punteggio_iniziale_squadre
        resp['jolly_enabled'] = gara.jolly
        if request.user.is_authenticated:
            ids = list(gara.squadre.filter(consegnatore=request.user).values_list("num", flat=True).all())
        else:
            ids = []
        resp['consegnatore_per'] = ids

        if gara.inizio is None:
            return JsonResponse(resp)

        resp['fine'] = gara.get_ora_fine()
        resp['tempo_blocco'] = gara.get_ora_blocco()

        resp['consegne'] = gara.get_consegne()
        resp['jolly'] = gara.get_jolly()
        resp['bonus'] = gara.get_bonus()

        return JsonResponse(resp)


class ClassificaBaseView(UserPassesTestMixin, DetailView):
    """ Visualizzazione classifica - classe base """

    @staticmethod
    def _elapsed_time_to_integer(elapsed):
        """Convert HH:MM:SS to the number of elapsed seconds"""
        return sum(int(x) * 60 ** i for i, x in enumerate(reversed(elapsed.split(":"))))

    def _convert_time(self, variable_name, qs):
        variable_value = self.request.GET.get(variable_name, None)
        if variable_value is None:
            qs[variable_name] = None
        elif variable_value.isdecimal():
            qs[variable_name] = int(variable_value)
        elif ":" in variable_value:
            qs[variable_name] = self._elapsed_time_to_integer(variable_value)
        else:
            qs[variable_name] = None

    def _convert_boolean(self, variable_name, qs):
        variable_value = self.request.GET.get(variable_name, None)
        if variable_value is None:
            qs[variable_name] = None
        elif variable_value.lower() == "true" or variable_value == "1":
            qs[variable_name] = True
        elif variable_value.lower() == "false" or variable_value == "0":
            qs[variable_name] = False
        else:
            qs[variable_name] = None

    def _convert_integer(self, variable_name, qs):
        variable_value = self.request.GET.get(variable_name, None)
        if variable_value is None:
            qs[variable_name] = None
        elif variable_value.isdecimal():
            qs[variable_name] = int(variable_value)
        else:
            qs[variable_name] = None

    def _convert_querystring(self):
        qs = {}
        self._convert_time("race_time", qs)
        self._convert_boolean("ended", qs)
        self._convert_time("computation_rate", qs)
        return qs

    def test_func(self):
        self.object = self.get_object()
        self.querystring = self._convert_querystring()
        is_admin = (
            self.request.user.is_authenticated and self.request.user.can_administrate(self.object))
        if any(self.querystring[k] is not None for k in ("race_time", "ended", "computation_rate")) and not is_admin:
            return False
        else:
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.querystring)
        # Assign default values if querystring is not provided.
        # This cannot be done in self._convert_querystring because otherwise it would
        # not be possible to correctly check permissions.
        if context["ended"] is None:
            context["ended"] = self.object.finished
        if context["computation_rate"] is None:
            context["computation_rate"] = 3
        return context


class ClassificaView(ClassificaBaseView):
    """ Visualizzazione classifica squadre """
    model = Gara
    template_name = "classifiche/squadre.html"


class PuntiProblemiView(ClassificaBaseView):
    """ Visualizzazione punteggi problemi """
    model = Gara
    template_name = "classifiche/punti_problemi.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['soluzioni'] = self.object.soluzioni.all().order_by("problema")
        return context


class StatoProblemiView(ClassificaBaseView):
    """ Visualizzazione stato problemi: quali sono stati risolti e quali no """
    model = Gara
    template_name = "classifiche/stato_problemi.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['soluzioni'] = self.object.soluzioni.all().order_by("problema")
        return context


class UnicaView(ClassificaBaseView):
    """ Visualizzazione unica: tutte le informazioni """
    model = Gara
    template_name = "classifiche/unica.html"

    def _convert_querystring(self):
        qs = super()._convert_querystring()
        self._convert_integer("start_pos", qs)
        self._convert_integer("end_pos", qs)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context["start_pos"] is None:
            context["start_pos"] = 1
        if context["end_pos"] is None:
            context["end_pos"] = len(self.object.squadre.all())
        context["soluzioni"] = self.object.soluzioni.all().order_by("problema")
        return context

class ScorrimentoView(ClassificaBaseView):
    """ Visualizzazione scorrimento: tutte le informazioni """
    model = Gara
    template_name = "classifiche/scorrimento.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['soluzioni'] = self.object.soluzioni.all().order_by("problema")
        return context
