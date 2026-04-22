from django import forms

from engine.models import User
from engine.allenamento.services import (
    list_allenamenti_disponibili, _resolve_base_paths,
)


class AllenamentoCreateForm(forms.Form):
    MAX_SQUADRE = 20

    base = forms.ChoiceField(label='Gara base', choices=[])
    nome = forms.CharField(label='Nome gara', max_length=200)
    num_squadre_umane = forms.IntegerField(
        label='Numero squadre umane', min_value=1, max_value=MAX_SQUADRE,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        disponibili = list_allenamenti_disponibili()
        self.fields['base'].choices = [
            (f'{anno}/{nome}', f'{anno} \u2013 {nome}')
            for (anno, nome, *_paths) in disponibili
        ]
        users_qs = User.objects.filter(is_active=True).order_by('username')
        for i in range(1, self.MAX_SQUADRE + 1):
            self.fields[f'consegnatore_{i}'] = forms.ModelChoiceField(
                queryset=users_qs, required=False,
                label=f'Consegnatore squadra {i}',
            )

    def consegnatore_fields(self):
        return [self[f'consegnatore_{i}'] for i in range(1, self.MAX_SQUADRE + 1)]

    def clean(self):
        cd = super().clean()
        N = cd.get('num_squadre_umane') or 0
        consegnatori = []
        for i in range(1, N + 1):
            u = cd.get(f'consegnatore_{i}')
            if u is None:
                raise forms.ValidationError(
                    f'Consegnatore mancante per la squadra {i}'
                )
            consegnatori.append(u)
        if len({u.pk for u in consegnatori}) != len(consegnatori):
            raise forms.ValidationError(
                'I consegnatori devono essere utenti distinti'
            )
        cd['consegnatori'] = consegnatori
        paths = _resolve_base_paths(cd.get('base'))
        if paths is None:
            raise forms.ValidationError(
                'File della gara base non trovati sul filesystem'
            )
        cd['base_paths'] = paths
        return cd
