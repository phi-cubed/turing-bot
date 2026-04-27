from django.db import models
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.validators import MaxValueValidator
from django.utils import timezone, dateparse
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords

from datetime import timedelta, date, time
import json
import uuid
from dateutil.parser import parse

import logging
logger = logging.getLogger(__name__)

from string import Template
from django.conf import settings
import pytz
TIME_ZONE_SETTING = getattr(settings, "TIME_ZONE", None)
assert TIME_ZONE_SETTING is not None
assert isinstance(TIME_ZONE_SETTING, str)
TIME_ZONE_SETTING = pytz.timezone(TIME_ZONE_SETTING)


class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


def get_file_path(instance, filename):  # pragma: no cover
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return 'testi/'+filename


def str2arr(s):
    if s == "":
        return []
    return [int(x) for x in s.split(',')]


def all_nonnegative_validator(val):
    arr = str2arr(val)
    if not all(x>=0 for x in arr):
        raise ValidationError("Gli interi devono essere tutti non negativi")

class User(AbstractUser):
    GENDERS = (
        ('M', 'Maschio'),
        ('F', 'Femmina'),
        ('N', 'Non specificato'),
    )
    gender = models.CharField(max_length=1, choices=GENDERS, default='N', verbose_name='Genere')

    def can_administrate(self, gara):
        return gara.admin == self

    def is_inseritore(self, gara):
        return self in gara.inseritori.all()

    def is_consegnatore(self, gara):
        return Squadra.objects.filter(gara=gara, consegnatore=self).exists()

    def can_insert_gara(self, gara):
        """Controlla che l'utente sia un admin, un inseritore o un consegnatore"""
        return self.can_administrate(gara) or self.is_inseritore(gara) or self.is_consegnatore(gara)

    def can_insert_squadra(self, squadra):
        """Controlla che l'utente sia un admin, un inseritore o un consegnatore"""
        return self.can_administrate(squadra.gara) or self.is_inseritore(squadra.gara) or squadra.consegnatore == self

    def can_edit_or_delete(self, evento):
        """Controlla che l'utente sia admin, o un inseritore proprietario dell'evento."""
        return self.can_administrate(evento.gara) or (self.is_inseritore(evento.gara) and evento.creatore == self)

    def can_create_gara(self):
        return self.has_perm("engine.change_gara")

class Gara(models.Model):
    """
    Modello che descrive una gara
    """
    nome = models.CharField(max_length=200, help_text="Nome della gara")
    inizio = models.DateTimeField(blank=True, null=True)
    sospensione = models.DateTimeField(blank=True, null=True)
    durata = models.DurationField(default=timedelta(hours=2), help_text="Durata nel formato hh:mm:ss")
    n_blocco = models.PositiveSmallIntegerField(blank=True, default=2, null=True,  # Il valore NULL non fa bloccare mai il punteggio
                                                verbose_name="Parametro N",
                                                help_text="Numero di risposte esatte che bloccano il punteggio di un problema")
    k_blocco = models.PositiveSmallIntegerField(blank=True, default=1, null=True,  # Il valore NULL fa aumentare sempre il punteggio
                                                verbose_name="Parametro K",
                                                help_text="Numero di risposte errate che aumentano il punteggio di un problema")
    durata_blocco = models.DurationField(default=timedelta(minutes=20), help_text="Il punteggio dei problemi viene bloccato quando il tempo rimanente è quello indicato in questo campo nel formato hh:mm:ss")
    num_problemi = models.PositiveSmallIntegerField(default=20,
                                                    verbose_name="Problemi",
                                                    help_text="Numero di problemi")
    punteggio_iniziale_squadre = models.PositiveSmallIntegerField(blank=True, null=True, help_text="Punteggio iniziale per ciascuna squadra. Se lasciato bianco, il punteggio è pari al numero di quesiti moltiplicato per 10 (dove -10 corrisponde alla penalità per una risposta errata)")
    fixed_bonus = models.CharField(blank=True, max_length=100,
                                   default='20,15,10,8,6,5,4,3,2,1',
                                   validators=[all_nonnegative_validator],
                                   verbose_name="Bonus problema",
                                   help_text="Bonus per le prime squadre a risolvere un problema")
    super_mega_bonus = models.CharField(blank=True, max_length=100,
                                        default='100,60,40,30,20,10',
                                        validators=[all_nonnegative_validator],
                                        verbose_name="Bonus finale",
                                        help_text="Bonus per le prime squadre a risolvere tutti i problemi")
    jolly = models.BooleanField(default=True,
                                verbose_name="Jolly",
                                help_text="Possibilità di inserire un jolly")
    history = HistoricalRecords()

    #
    # Permessi
    #

    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="administered_gare", null=True)
    inseritori = models.ManyToManyField(User, blank=True)

    class Meta:
        verbose_name_plural = "gare"

    def __str__(self):
        return self.nome

    """
    Definisce delle proprietà in modo da poter ottenere e settare direttamente
    degli array per i bonus di risoluzione dei problemi
    """

    def get_fixed_bonus_array(self):
        return str2arr(self.fixed_bonus)

    def set_fixed_bonus_array(self, array):
        self.fixed_bonus = ','.join(map(str, array))

    fixed_bonus_array = property(get_fixed_bonus_array, set_fixed_bonus_array)

    def get_super_mega_bonus_array(self):
        return str2arr(self.super_mega_bonus)

    def set_super_mega_bonus_array(self, array):
        self.super_mega_bonus = ','.join(map(str, array))

    super_mega_bonus_array = property(get_super_mega_bonus_array, set_super_mega_bonus_array)

    def get_ora_fine(self):
        if not self.inizio:
            return None
        if self.sospensione:
            return None
        return self.inizio + self.durata

    def get_ora_blocco(self):
        if not self.inizio:
            return None
        if self.sospensione:
            return None
        return self.inizio + self.durata - self.durata_blocco

    def finished(self):
        return (self.inizio is not None) and (self.sospensione is None) and (timezone.now() > self.get_ora_fine())

    def get_all_eventi(self, user, id_evento, num_squadra, problema, risposta):
        """Restituisce tutti gli eventi all'amministratore."""
        qs = self.eventi.all().select_related("consegna__squadra", "jolly__squadra", "bonus__squadra")

        if user.can_administrate(self):

            res = [x.as_child() for x in qs]
            for x in res:
                x.timestamp = strfdelta(x.orario - self.inizio, "%H:%M:%S")
                if hasattr(x, "problema") and hasattr(x, "risposta"):
                    x.giusta = (x.risposta == self.soluzioni.get(problema=x.problema).risposta)
                else:
                    x.giusta = None
            if id_evento:
                res = [x for x in res if x.pk == int(id_evento)]
            if num_squadra:
                res = [x for x in res if x.squadra.num == int(num_squadra)]
            if problema:
                if problema == "B":
                    res = [x for x in res if isinstance(x, Bonus)]
                else:
                    assert problema.isdigit()
                    res = [x for x in res if hasattr(x, "problema") and x.problema == int(problema)]
            if risposta:
                if risposta == "J":
                    res = [x for x in res if isinstance(x, Jolly)]
                else:
                    if risposta == "G":
                        res = [x for x in res if hasattr(x, "risposta") and x.giusta]
                    elif risposta == "S":
                        res = [x for x in res if hasattr(x, "risposta") and not x.giusta]
                    else:
                        assert risposta.isdigit()
                        res = [x for x in res if hasattr(x, "risposta") and x.risposta == int(risposta)]

            return res
        raise PermissionDenied("L'utente non può chiedere gli eventi della gara.")

    def get_eventi_recenti(self, user, limit):
        """Restituisce gli eventi visualizzabili dall'utente."""
        qs = self.eventi.all().select_related("consegna__squadra", "jolly__squadra", "bonus__squadra")

        if user.can_administrate(self):
            return [(True, x.as_child()) for x in qs[:limit]]
        if user.is_inseritore(self):
            return [(x.creatore == user, x.as_child()) for x in qs[:limit]]
        if user.is_consegnatore(self):
            return [(False, x.as_child()) for x in qs.filter(creatore=user)[:limit]]
        raise PermissionDenied("L'utente non può chiedere gli eventi della gara.")

    def get_squadre_inseribili(self, user):
        '''Restiuisce le squadre per cui l'utente può effettuare una consegna.'''
        qs = self.squadre.all()
        if user.can_administrate(self) or user.is_inseritore(self):
            return qs
        else:
            qs = qs.filter(consegnatore=user)
            if qs.exists():
                return qs
            else:
                raise PermissionDenied("L'utente non può consegnare per nessuna squadra.")

    def get_soluzioni(self):
        sol = {}
        for s in self.soluzioni.all():
            sol[s.problema] = s.risposta
        return sol

    def get_problemi(self):
        problems = {}
        for s in self.soluzioni.all():
            problems[s.problema] = {"nome": s.nome, "punteggio": s.punteggio}
        return problems

    def get_consegne(self, last=None):
        sol = self.get_soluzioni()
        res = []
        qs = Consegna.objects.filter(gara=self).select_related('squadra')
        if last is not None:
            qs = qs.filter(pk__gt=last)

        # TODO: ottimizzare questa cosa, magari in una query
        for c in qs.order_by('orario'):
            tmp = {}
            tmp['id'] = c.pk
            tmp['squadra'] = c.squadra.num
            tmp['ospite'] = c.squadra.ospite
            tmp['orario'] = c.orario
            tmp['problema'] = c.problema
            tmp['giusta'] = (c.risposta == sol[c.problema])
            res.append(tmp)
        return res

    def get_jolly(self, last=None):
        res = []
        qs = Jolly.objects.filter(gara=self).select_related('squadra')
        if last is not None:
            qs = qs.filter(pk__gt=last)
        for c in qs.order_by('orario'):
            tmp = {}
            tmp["id"] = c.pk
            tmp["squadra"] = c.squadra.num
            tmp["problema"] = c.problema
            res.append(tmp)
        return res

    def get_bonus(self, last=None):
        res = []
        qs = Bonus.objects.filter(gara=self).select_related('squadra')
        if last is not None:
            qs = qs.filter(pk__gt=last)
        for c in qs.order_by('orario'):
            tmp = {}
            tmp["id"] = c.pk
            tmp["squadra"] = c.squadra.num
            tmp["punteggio"] = c.punteggio
            tmp["orario"] = c.orario
            res.append(tmp)
        return res

    def get_squadre(self):
        res = {}
        for s in self.squadre.all():
            res[s.num] = {"nome": s.nome, "ospite": s.ospite}
        return res

    def get_squadre_order(self):
        return self.squadre.all().order_by('num')

    def get_last_update(self):
        """
        Metodo per vedere qual è stata l'ultima modifica sostanziale
        Restituisce il più recente tra:
        - Ultima modifica di gara
        - Ultima modifica o eliminazione di un jolly
        - Ultima modifica o eliminazione di una consegna
        - Ultima modifica o eliminazione di un bonus
        - Ultima modifica di un problema
        """
        lu = self.history.latest().history_date
        try:
            obj = Jolly.history.filter(gara=self).exclude(history_type='+').latest()
            lu = max(lu, obj.history_date)
        except:
            pass

        try:
            obj = Consegna.history.filter(gara=self).exclude(history_type='+').latest()
            lu = max(lu, obj.history_date)
        except:
            pass

        try:
            obj = Bonus.history.filter(gara=self).exclude(history_type='+').latest()
            lu = max(lu, obj.history_date)
        except:
            pass

        try:
            obj = Soluzione.history.filter(gara=self).exclude(history_type='+').latest()
            lu = max(lu, obj.history_date)
        except:
            pass
        return lu


    @staticmethod
    def serialize(obj):
        """JSON serializer for objects not serializable by default json code"""

        if isinstance(obj, date):
            return obj.isoformat()

        if isinstance(obj, time):
            return obj.isoformat()

        if isinstance(obj, timedelta):
            return int(obj.seconds / 60)

        if hasattr(obj, 'to_dict'):
            return obj.to_dict()

        return obj.__dict__

    def dump_to_json(self):
        return json.dumps(self, default=self.serialize, indent=4)

    # Loads current_game from json
    @classmethod
    def create_from_dict(cls, data):
        this = cls()
        this.save()
        for k in {'nome', 'n_blocco', 'k_blocco', 'punteggio_iniziale_squadre', 'num_problemi', 'fixed_bonus', 'super_mega_bonus', 'jolly'}:
            if k in data:
                setattr(this, k, data[k])

        if "inizio" in data and data["inizio"] is not None:
            this.inizio = parse(data['inizio'])
        this.durata = timedelta(minutes=data['durata'])
        this.durata_blocco = timedelta(minutes=data.get('durata_blocco', 20))
        this.num_problemi = len(data['soluzioni'])
        this.save()

        for squadra in data['squadre']:
            Squadra(gara=this, **squadra).save()

        for soluzione in data['soluzioni']:
            Soluzione(gara=this, **soluzione).save()

        if 'eventi' in data:
            for evento in data['eventi']:
                evento_copy = dict(evento)
                evento_copy['orario'] = parse(evento['orario'])
                if 'squadra_id' in evento:
                    evento_copy['squadra'] = Squadra.objects.get(gara=this, num=evento['squadra_id'])
                    del evento_copy['squadra_id']

                [subclass] = [x for x in Evento.__subclasses__() if x.__name__ == evento['subclass']]
                obj = subclass(gara=this, **evento_copy)
                obj.save()
                obj.orario = evento_copy['orario']
                obj.save()
                assert obj.orario == evento_copy['orario'], "Orario dell'evento non caricato correttamente"

        return this

    def to_dict(self):
        d = {}
        for k in {'nome', 'n_blocco', 'k_blocco', 'punteggio_iniziale_squadre', 'num_problemi', 'jolly'}:
            d[k] = getattr(self, k)
        for k in {'fixed_bonus', 'super_mega_bonus'}:
            # Elimina valori nulli al termine della lista
            d[k] = ','.join([x for x in getattr(self, k).split(',') if int(x) > 0]) if getattr(self, k) != '' else ''
        for k in {'inizio'}:
            inizio = getattr(self, k)
            if inizio is not None:
                d[k] = inizio.isoformat()
            else:
                d[k] = None
        for k in {'durata', 'durata_blocco'}:
            d[k] = int(getattr(self, k).seconds / 60)

        d.update({
            # Non si può usare order_by perché la classe padre Evento contiene solo orario e subclass
            # 'eventi': [e.to_dict() for e in self.eventi.all().order_by('orario', 'subclass', 'squadra_id', 'problema')],
            'eventi': list(sorted([e.to_dict() for e in self.eventi.all()], key=lambda e: (
                e["orario"], e["subclass"], e["squadra_id"], e["problema"] if "problema" in e else None))),
            'soluzioni': [s.to_dict() for s in self.soluzioni.all().order_by('problema')],
            'squadre': [s.to_dict() for s in self.squadre.all().order_by('num')],
        })
        return d


class Squadra(models.Model):
    """
    Modello che descrive un'istanza di una squadra che partecipa ad una gara
    """
    nome = models.CharField(max_length=200, help_text="Nome della squadra")
    gara = models.ForeignKey(Gara, on_delete=models.CASCADE, related_name='squadre')
    num = models.PositiveSmallIntegerField(verbose_name="Numero", help_text="Identificativo della squadra")
    ospite = models.BooleanField(default=False, help_text="Squadra ospite")
    consegnatore = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name_plural = "squadre"
        unique_together = ('gara', 'num')
        ordering = ['-gara']

    def get_id_nome(self):
        return "{0:02d} - {1}".format(self.num, self.nome)

    def __str__(self):
        return "{} @ gara {}".format(self.get_id_nome(), self.gara)

    def to_dict(self):
        return {
            'nome': self.nome,
            'num': self.num,
            'ospite': self.ospite
        }


class Soluzione(models.Model):
    """
    Modello che descrive un problema di gara, in particolare la risposta esatta
    """
    gara = models.ForeignKey(Gara, on_delete=models.CASCADE, related_name='soluzioni')
    problema = models.PositiveSmallIntegerField()
    nome = models.CharField(max_length=50, blank=True, null=True, help_text="Nome del problema")
    risposta = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(9999)], help_text="Soluzione del problema")
    punteggio = models.PositiveSmallIntegerField(default=20, help_text="Punteggio iniziale del problema")
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "soluzioni"
        unique_together = ('gara', 'problema',)
        ordering = ("gara", "problema",)

    def __str__(self):
        return "Soluzione del problema {} della gara {} (Risposta {}, punti {})".format(self.problema, self.gara, self.risposta, self.punteggio)

    def to_dict(self):
        return {
            'problema': self.problema,
            'nome': self.nome,
            'risposta': self.risposta,
            'punteggio': self.punteggio
        }


class KnowsChild(models.Model):
    # Make a place to store the class name of the child
    # (copied almost entirely from http://blog.headspin.com/?p=474)
    subclass = models.CharField(max_length=200)

    class Meta:
        abstract = True

    # Funzione che restituisce se stesso come sottoevento
    def as_child(self):
        return getattr(self, self.subclass.lower())

    def fill_subclass(self):
        self.subclass = self.__class__.__name__

    def save(self, *args, **kwargs):
        self.fill_subclass()
        super(KnowsChild, self).save(*args, **kwargs)

    def clean_fields(self, *args, **kwargs):
        self.fill_subclass()
        super(KnowsChild, self).clean_fields(*args, **kwargs)


class Evento(KnowsChild):
    """
    Modello che rappresenta un generico evento durante la gara.
    """

    orario = models.DateTimeField(auto_now_add=True)
    gara = models.ForeignKey(Gara, on_delete=models.CASCADE, related_name='eventi')
    creatore = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    history = HistoricalRecords(inherit=True)

    class Meta:
        verbose_name_plural = "eventi"
        ordering = ['-orario', '-pk']

    def __str__(self):
        if self.pk is not None:
            return "%s %d" % (self.subclass, self.pk)
        else:
            return "%s" % self.subclass

    def get_valore(self):
        """
        Valore generico che dipende dal tipo di sottoevento (risposta, punti di penalità, ecc.)
        """
        raise NotImplementedError("Implementa get_valore() o chiama self.as_child().get_valore()")

    def to_dict(self):
        d = {}
        c = self.as_child()
        for k, v in c.__dict__.items():
            if k in {'subclass', 'problema', 'risposta', 'punteggio'}:
                d[k] = v
            if k == 'orario':
                d[k] = v.isoformat()
            if k == 'squadra_id':
                d['squadra_id'] = c.squadra.num

        return d

    def clean(self):
        """
        Validazione dell'oggetto: accettiamo la consegna solo se:
        - la squadra sta partecipando alla gara
        - il problema sta nella gara
        """
        if self.squadra.gara != self.gara:
            raise ValidationError("Questa squadra non sta partecipando alla gara!")

        if self.problema > self.gara.num_problemi:
            raise ValidationError("Il problema deve esistere")

    def maybe_save(self):
        """
        Controllo che la consegna sia avvenuta entro il tempo di gara
        e che la squadra stia partecipando alla gara
        """
        loraesatta = timezone.now()
        if self.gara.inizio is None:
            return (False, "Gara non ancora iniziata")
        if self.gara.sospensione is not None:
            return (False, "Gara sospesa")
        if loraesatta < self.gara.inizio:
            return (False, "Non puoi consegnare con un orario precedente all'inizio della gara")
        if loraesatta > self.gara.get_ora_fine():
            if self.creatore == self.squadra.consegnatore:
                return (False, "Non puoi consegnare dopo la fine della gara")

        return (True, "Inserimento avvenuto")


class Consegna(Evento):
    """
    Modello che descrive una consegna di una risposta di una squadra
    """
    squadra = models.ForeignKey(Squadra, on_delete=models.CASCADE, related_name='consegne')
    problema = models.PositiveSmallIntegerField()
    risposta = models.PositiveSmallIntegerField(validators=[MaxValueValidator(9999)])

    class Meta(Evento.Meta):
        # Eredita il Meta dell'evento generico
        verbose_name_plural = "consegne"

    def __str__(self):
        return "Risposta {} al problema {} della squadra {} nella gara {} @ {}".format(
            self.risposta, self.problema, self.squadra.get_id_nome(), self.gara, self.orario.astimezone(TIME_ZONE_SETTING))

    def get_valore(self):
        return self.risposta

    def maybe_save(self):
        res = super().maybe_save()

        if res[0]:
            self.save()

            sol = self.gara.soluzioni.get(problema=self.problema)
            if sol.risposta == self.risposta:
                frase = "La risposta che hai consegnato è esatta!"
            else:
                frase = "La risposta che hai consegnato è errata."
            frase += f" Il numero di protocollo è {self.pk} e la data di inserimento è {self.orario.astimezone(TIME_ZONE_SETTING)}."
            return (True, frase)

        return res


class Jolly(Evento):
    """
    Modello che descrive la scelta di un jolly.
    """
    squadra = models.ForeignKey(Squadra, on_delete=models.CASCADE, related_name='jollys')
    problema = models.PositiveSmallIntegerField()

    class Meta(Evento.Meta):
        # Eredita il Meta dell'evento generico
        verbose_name_plural = "jolly"

    def __str__(self):
        return "Jolly sul problema {} della squadra {} nella gara {} @ {}".format(self.problema, self.squadra, self.gara, self.orario.astimezone(TIME_ZONE_SETTING))

    def get_valore(self):
        return "J"

    def maybe_save(self):
        res = super().maybe_save()

        if not res[0]:
            return res

        if not self.gara.jolly:
            return (False, "Questa gara non prevede l'inserimento di jolly")

        loraesatta = timezone.now()
        if loraesatta > self.gara.inizio+timedelta(minutes=15):
            if self.creatore == self.squadra.consegnatore:
                return (False, "Non puoi inserire un jolly dopo 15 minuti")

        qs = self.gara.eventi.all()
        events = [x.as_child() for x in qs]

        jolly = [x for x in events if isinstance(x, Jolly) and x.pk != self.pk]
        jolly = [x.as_child() for x in jolly if x.squadra.num == self.squadra.num]
        if len(jolly) > 0:
            return (False, f"È già stato inserito un jolly per la squadra: {jolly}")

        if not self.creatore.can_administrate(self.gara):
            sol = self.gara.soluzioni.get(problema=self.problema)
            consegne = [x for x in events if isinstance(x, Consegna)]
            consegne = [x for x in consegne if x.squadra.num == self.squadra.num and x.problema == self.problema]
            consegne_esatte = [x for x in consegne if x.risposta == sol.risposta]
            if len(consegne_esatte) > 0:
                return (False, f"Solo l'amministratore può inserire il jolly ad una risposta a cui la squadra ha già risposto correttamente: {consegne_esatte}")

        if res[0]:
            self.save()
            res = (res[0], res[1] + f". Il numero di protocollo è {self.pk} e la data di inserimento è {self.orario.astimezone(TIME_ZONE_SETTING)}.")
        return res


class Bonus(Evento):
    """
    Modello che descrive l'assegnazione di un bonus.
    """
    squadra = models.ForeignKey(Squadra, on_delete=models.CASCADE, related_name='bonus')
    punteggio = models.SmallIntegerField()

    class Meta(Evento.Meta):
        # Eredita il Meta dell'evento generico
        verbose_name_plural = "bonus"

    def __str__(self):
        return "Bonus di {} punti alla squadra {} nella gara {} @ {}".format(self.punteggio, self.squadra, self.gara, self.orario.astimezone(TIME_ZONE_SETTING))

    def get_valore(self):
        return self.punteggio

    def clean(self):
        """
        Validazione dell'oggetto: accettiamo la consegna solo se:
        - la squadra sta partecipando alla gara
        """
        if self.squadra.gara != self.gara:
            raise ValidationError("Questa squadra non sta partecipando alla gara!")

    def maybe_save(self):
        res = super().maybe_save()

        if res[0]:
            self.save()
            res = (res[0], res[1] + f". Il numero di protocollo è {self.pk} e la data di inserimento è {self.orario.astimezone(TIME_ZONE_SETTING)}.")
        return res


class SystemSettings(models.Model):
    is_archive_public = models.BooleanField(default=True, verbose_name="Archivio pubblico")
    allowed_users = models.ManyToManyField(User, blank=True, related_name="can_view_archive", verbose_name="Utenti autorizzati")

    class Meta:
        verbose_name = "Impostazioni di sistema"
        verbose_name_plural = "Impostazioni di sistema"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Impostazioni di sistema"


from engine.allenamento.models import Allenamento  # noqa: E402,F401

