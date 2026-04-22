from django import forms
from engine.models import User
from django.core.validators import FileExtensionValidator
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from crispy_forms.helper import FormHelper

from engine.models import Squadra, Soluzione, Jolly, Consegna, Bonus, Gara
from dateutil.parser import parse
from mathrace_interaction.journal_reader import journal_reader
from mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing import (
    strip_mathrace_only_attributes_from_imported_turing)

import io
import json

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

class RispostaEsattaFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super(RispostaEsattaFormSet, self).__init__(*args, **kwargs)
        no_of_forms = len(self)
        for i in range(0, no_of_forms):
            self[i].fields['risposta'].label += " {}".format(i + 1)
            self[i].fields['problema'].widget = forms.HiddenInput()


RispostaFormset = forms.modelformset_factory(
    Soluzione, fields=('problema', 'risposta', 'nome', 'punteggio'),
    extra=0, formset=RispostaEsattaFormSet,)


class BaseSquadraFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        users_qs = kwargs.pop("users_qs")
        super().__init__(*args, **kwargs)
        users_qs.all = lambda: users_qs
        users_qs.iterator = users_qs.all

        # Apply the common (non-cloning) querysets to all the forms
        for form in self.forms:
            form.fields["consegnatore"].queryset = users_qs

    def clean(self, *args, **kwargs):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        squadre = []
        ids = []
        for form in self.forms:
            id = form.cleaned_data["num"]
            sq = form.cleaned_data['nome']
            if sq in squadre:
                raise forms.ValidationError('I nomi delle squadre devono essere distinti!')
            if id in ids:
                raise forms.ValidationError('Gli identificativi delle squadre devono essere unici!')
            squadre.append(sq)
            ids.append(id)


class SquadraForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'forms/inline_field.html'

    class Meta:
        model = Squadra
        fields = ['num', 'nome', 'ospite', 'consegnatore']


SquadraFormset = forms.modelformset_factory(
                    Squadra, form=SquadraForm,
                    extra=0, formset=BaseSquadraFormSet,)


class SquadraChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_id_nome()


class QueryForm(forms.Form):
    id_evento = forms.IntegerField(required=False, label="Id")
    num_squadra = SquadraChoiceField(required=False, queryset=None, to_field_name="num")
    problema = forms.CharField(required=False, help_text='Usare "B" per cercare i bonus')
    risposta = forms.CharField(required=False, help_text='Usare "J" per cercare i jolly, "G" per cercare risposte giuste, "S" per cercare risposte sbagliate')

    def __init__(self, *args, **kwargs):
        self.gara = kwargs.pop('gara', None)
        querystring_id_evento = kwargs.pop('querystring_id_evento', '')
        querystring_num_squadra = kwargs.pop('querystring_num_squadra', '')
        querystring_problema = kwargs.pop('querystring_problema', '')
        querystring_risposta = kwargs.pop('querystring_risposta', '')
        super(QueryForm, self).__init__(*args, **kwargs)
        if self.gara:
            self.fields['num_squadra'].queryset = self.gara.squadre.all()
            self.fields['num_squadra'].widget.attrs.update({'autofocus': ''})
        self.fields['id_evento'].initial = querystring_id_evento
        self.fields['num_squadra'].initial = querystring_num_squadra
        self.fields['problema'].initial = querystring_problema
        self.fields['risposta'].initial = querystring_risposta


class SquadraChoiceUserSubsetForm(forms.Form):
    squadra = SquadraChoiceField(required=True, queryset=None)

    def __init__(self, *args, **kwargs):
        self.gara = kwargs.pop('gara', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.gara:
            self.fields['squadra'].queryset = self.gara.get_squadre_inseribili(self.user)
            self.fields['squadra'].empty_label = None
            self.fields['squadra'].widget.attrs.update({'autofocus': ''})


class InserimentoForm(SquadraChoiceUserSubsetForm):
    problema = forms.IntegerField(min_value=1, required=False, help_text='Problema di cui si inserisce la risposta o il jolly. Lasciare vuoto se "Bonus manuale" è spuntato')
    risposta = forms.IntegerField(required=False, help_text='Valore della risposta. Se "Jolly" è spuntato lasciare vuoto; se "Bonus manuale" è spuntato, inserire il valore del bonus')
    jolly = forms.BooleanField(required=False)
    bonus = forms.BooleanField(required=False, label="Bonus manuale")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.gara:
            self.fields['squadra'].widget.attrs.update({'size': '5'})

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        is_jolly = bool(cleaned_data['jolly'])
        is_bonus = bool(cleaned_data['bonus'])

        has_problema = bool(cleaned_data['problema'] is not None)
        has_risposta = bool(cleaned_data['risposta'] is not None)

        if is_jolly and is_bonus:
            raise forms.ValidationError('Inserire il bonus o il jolly, ma non entrambi')
        if is_jolly:
            if not has_problema:
                raise forms.ValidationError('Inserire il problema')
            if has_risposta:
                raise forms.ValidationError('Inserire la risposta o il jolly, ma non entrambi')
        elif is_bonus:
            if not has_risposta:
                raise forms.ValidationError('Inserire il valore numerico del punteggio del bonus')
            if has_problema:
                raise forms.ValidationError('Non inserire il problema quando si aggiunge un bonus')
        else:
            if not has_problema:
                raise forms.ValidationError('Inserire il problema')
            if not has_risposta:
                raise forms.ValidationError('Inserire il valore numerico della risposta')
            risposta = int(cleaned_data['risposta'])
            if risposta < 0:
                raise forms.ValidationError('La risposta deve essere non negativa')
            if risposta > 9999:
                raise forms.ValidationError('La risposta deve essere inferiore o uguale a 9999')

        obj = self.get_instance()
        obj.clean()
        return cleaned_data

    def get_instance(self):
        if self.cleaned_data.get('jolly'):
            return Jolly(gara=self.gara, squadra=self.cleaned_data.get('squadra'),
                         problema=self.cleaned_data.get('problema'))
        elif self.cleaned_data.get('bonus'):
            return Bonus(gara=self.gara, squadra=self.cleaned_data.get('squadra'),
                         punteggio=self.cleaned_data.get('risposta'))
        else:
            return Consegna(gara=self.gara, squadra=self.cleaned_data.get('squadra'),
                            problema=self.cleaned_data.get('problema'),
                            risposta=self.cleaned_data.get('risposta'))


class ModificaConsegnaForm(SquadraChoiceUserSubsetForm):
    problema = forms.IntegerField(min_value=1, max_value=50)
    risposta = forms.IntegerField(min_value=0, max_value=9999)


class ModificaJollyForm(SquadraChoiceUserSubsetForm):
    problema = forms.IntegerField(min_value=1, max_value=50)


class ModificaBonusForm(SquadraChoiceUserSubsetForm):
    risposta = forms.IntegerField()


class ModificaGaraForm(forms.ModelForm):
    num_squadre = forms.IntegerField(initial=10, label="Squadre", help_text="Numero di squadre")

    class Meta:
        model = Gara
        fields = ['nome', 'durata', 'durata_blocco', 'n_blocco', 'k_blocco',
                 'num_problemi', 'punteggio_iniziale_squadre', 'fixed_bonus', 'super_mega_bonus', 'jolly',
                 'admin', 'inseritori']

    def __init__(self, *args, **kwargs):
        num_squadre = kwargs.pop('num_squadre', None)
        super(ModificaGaraForm, self).__init__(*args, **kwargs)
        if num_squadre is not None:
            self.fields["num_squadre"].initial = num_squadre
        self.fields["admin"].required = False
        self.fields["admin"].queryset = User.objects.filter(is_staff=True)
        self.fields["inseritori"].queryset = User.objects.filter(is_staff=False)

class CreaGaraForm(ModificaGaraForm):
    nomi_squadre_upload = forms.FileField(
        label="Nomi delle squadre", help_text="Scegli il file .txt contente i nomi delle squadre (opzionale)",
        validators=[FileExtensionValidator(allowed_extensions=["txt"])], required=False)
    nomi_problemi_upload = forms.FileField(
        label="Nomi dei problemi", help_text="Scegli il file .txt contente i nomi dei problemi (opzionale)",
        validators=[FileExtensionValidator(allowed_extensions=["txt"])], required=False)
    risposte_problemi_upload = forms.FileField(
        label="Risposte ai problemi", help_text="Scegli il file .txt contente le risposte ai problemi (opzionale)",
        validators=[FileExtensionValidator(allowed_extensions=["txt"])], required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CreaGaraForm, self).__init__(*args, **kwargs)
        self.fields["admin"].initial = user.id

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        nomi_squadre = self._read_text_upload(cleaned_data["nomi_squadre_upload"])
        nomi_problemi = self._read_text_upload(cleaned_data["nomi_problemi_upload"])
        risposte_problemi = self._read_text_upload(cleaned_data["risposte_problemi_upload"])

        num_squadre = cleaned_data["num_squadre"]
        has_nomi_squadre = (nomi_squadre is not None)
        if has_nomi_squadre:
            if len(nomi_squadre) != num_squadre:
                raise forms.ValidationError("Il numero di righe nel file contenente i nomi delle squadre deve essere uguale al numero di squadre")
        else:
            nomi_squadre = [f"Squadra {i + 1}" for i in range(num_squadre)]

        num_problemi = cleaned_data["num_problemi"]
        has_nomi_problemi = (nomi_problemi is not None)
        has_risposte_problemi = (risposte_problemi is not None)
        if has_nomi_problemi != has_risposte_problemi:
            raise forms.ValidationError("Devi caricare sia i nomi dei problemi sia le loro risposte")
        if has_nomi_problemi:  # and also has_risposte_problemi
            if len(risposte_problemi) != len(risposte_problemi):
                raise forms.ValidationError("Il numero di righe nel file contenente le risposte ai problemi deve essere uguale al numero di righe nel file contenente le risposte ai problemi")
            if len(nomi_problemi) != num_problemi:
                raise forms.ValidationError("Il numero di righe nel file contenente i nomi dei problemi deve essere uguale al numero dei problemi")
            if len(risposte_problemi) != num_problemi:
                raise forms.ValidationError("Il numero di righe nel file contenente le risposte ai problemi deve essere uguale al numero dei problemi")
        else:
            nomi_problemi = [f"Problema {i + 1}" for i in range(num_problemi)]
            risposte_problemi = [0 for _ in range(num_problemi)]

        cleaned_data["nomi_squadre"] = nomi_squadre
        cleaned_data["nomi_problemi"] = nomi_problemi
        cleaned_data["risposte_problemi"] = risposte_problemi
        return cleaned_data

    @staticmethod
    def _read_text_upload(text_file):
        if text_file is None:
            return None
        else:
            all_lines = [line.strip() for line in text_file.read().decode("utf-8").splitlines()]
            return [line for line in all_lines if line != ""]

class UploadGaraForm(forms.Form):
    gara = forms.FileField(
        label="Gara", help_text="Scegli il file .journal o .json contente la gara da importare",
        validators=[FileExtensionValidator(allowed_extensions=["journal", "json"])])
    eventi_futuri = forms.BooleanField(
        required=False, initial=False, label="Consenti eventi futuri", help_text=(
            "Spuntare per consentire eventi che hanno data nel futuro. Di default tali eventi non sono consentiti, "
            "perché possono creare confusione tra gli inseritori i quali, guardando la classifica, "
            "vedrebbero comparire gradualmente eventi senza che loro li stiano inserendo"
        ))
    eventi_riordina = forms.BooleanField(
        required=False, initial=False, label="Riordina automaticamente eventi", help_text=(
            "Spuntare per riordinare automaticamente gli eventi in ordine cronologico crescente. "
            "Caricare un file con eventi disordinati può creare problemi nella visualizzazione della classifica, "
            "perché gli inserimento non arrivano in ordine corretto. Di default gli eventi non vengono automaticamente "
            "riordinati ma, se questa opzione non è selezionata, viene comunque controllato che siano già nell'ordine "
            "cronologico corretto"
        ))
    nome_gara = forms.CharField(
        label="Nome della gara (richiesto solo per il formato .journal)",
        initial="Disfida", required=False)
    data_gara = forms.DateTimeField(
        label="Data della gara (richiesto solo per il formato .journal)",
        initial=timezone.now(), required=False)

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        gara_file = cleaned_data["gara"]
        if gara_file.name.endswith(".json"):
            gara_json = json.load(gara_file)
        elif gara_file.name.endswith(".journal"):
            race_name = cleaned_data["nome_gara"]
            race_date = cleaned_data["data_gara"]
            with journal_reader(io.TextIOWrapper(gara_file, encoding="utf-8")) as journal_stream:
                # Disable strict processing: incorrectly sorted events will be handled according to
                # the choice in eventi_riordina
                journal_stream.strict_timestamp_race_events = False
                try:
                    gara_json = journal_stream.read(race_name, race_date)
                except RuntimeError as e:
                    raise forms.ValidationError(f"Errore nella conversione del file journal: {e}")
            strip_mathrace_only_attributes_from_imported_turing(gara_json)

        has_inizio = ("inizio" in gara_json and gara_json["inizio"] is not None)
        has_eventi = ("eventi" in gara_json)
        if not has_inizio and has_eventi:
            raise forms.ValidationError(f'La gara contiene eventi ma non ha una data di inizio')

        if has_eventi:
            if cleaned_data["eventi_riordina"]:
                gara_json['eventi'] = list(sorted(gara_json['eventi'], key=lambda e: (
                    e["orario"], e["subclass"], e["squadra_id"], e["problema"] if "problema" in e else None)))

            loraesatta = timezone.now()
            orario_precedente = parse(gara_json["inizio"])
            for evento in gara_json["eventi"]:
                orario = parse(evento["orario"])
                if not cleaned_data["eventi_futuri"] and orario > loraesatta:
                    raise forms.ValidationError(f'La gara contiene eventi che hanno data nel futuro, ad esempio in data {evento["orario"]}')
                if orario < orario_precedente:
                    raise forms.ValidationError(f"La gara contiene eventi in ordine non cronologico crescente, ad esempio l'evento alle {orario_precedente} viene prima dell'evento delle {orario}")
                else:
                    orario_precedente = orario

        cleaned_data["gara_json"] = gara_json
        return cleaned_data
