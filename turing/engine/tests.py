from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.db.models import F
from django.urls import reverse
from django.test import Client, TestCase

import os
import time as t
import json
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import random

from engine.models import Gara, Squadra, Soluzione, Consegna, Jolly, User, Bonus
# Create your tests here.


class js_variable_evals_to_true(object):
    def __init__(self, variable):
        self.variable = variable

    def __call__(self, driver):
        return driver.execute_script("return {0};".format(self.variable))


def wait_for_element(browser, by, value):
    WebDriverWait(browser, 5).until(EC.presence_of_element_located((by, value)))


class TuringTests():
    '''Classe con alcuni metodi utili implementati'''

    def crea_gara(self, num_squadre, soluzioni, num_ospiti=0, n_blocco=2, k_blocco=5, iniziata=True, **kwargs):
        '''
        Inizializza una gara di test.
        ---
        Parametri:

        num_squadre - numero di squadre che partecipano alla gara
        soluzioni - array delle soluzioni ai problemi
        num_ospiti - numero di squadre ospiti
        *altri parametri (k_blocco, n_blocco, ecc.)* - vengono passati al costruttore della gara.
        '''
        if iniziata:
            inizio = timezone.now()
        else:
            inizio = None
        self.gara = Gara.objects.create(nome="GaraTest", inizio=inizio, num_problemi=len(soluzioni), n_blocco=n_blocco, k_blocco=k_blocco, **kwargs)
        for i in range(num_squadre):
            Squadra.objects.create(nome="Squadra {}".format(i+1), gara=self.gara, num=i+1)

        for i in range(num_squadre, num_squadre+num_ospiti):
            Squadra.objects.create(nome="Squadra {}".format(i+1), gara=self.gara, ospite=True, num=i+1)

        for num, sol in enumerate(soluzioni):
            Soluzione.objects.create(problema=num+1, gara=self.gara, nome="Problema {}".format(num+1), risposta=sol)

    def go_to_minute(self, minutes):
        '''Trasla gli eventi in modo da essere al minuto indicato'''

        self.updated = False
        shift = self.gara.inizio - (timezone.now() - timedelta(minutes=minutes))
        self.gara.inizio = self.gara.inizio - shift
        self.gara.save()
        self.gara.eventi.update(orario=F('orario')-shift)

    def consegna(self, squadra, problema, risposta):
        '''Aggiunge una consegna al database (nel minuto corrente)'''

        self.updated = False
        res = Consegna(problema=problema, squadra=Squadra.objects.get(gara=self.gara, num=squadra), risposta=risposta, gara=self.gara, creatore=self.user)
        res.save()
        t.sleep(0.005)
        return res

    def put_jolly(self, squadra, problema):
        '''Aggiunge un jolly al database (nel minuto corrente)'''

        self.updated = False
        res = Jolly(problema=problema, squadra=Squadra.objects.get(gara=self.gara, num=squadra), gara=self.gara, creatore=self.user)
        res.save()
        t.sleep(0.005)
        return res

    def put_bonus(self, squadra, punteggio):
        '''Aggiunge un bonus al database (nel minuto corrente)'''

        self.updated = False
        res = Bonus(punteggio=punteggio, squadra=Squadra.objects.get(gara=self.gara, num=squadra), gara=self.gara, creatore=self.user)
        res.save()
        t.sleep(0.005)
        return res

    def modifica(self, evento, **kwargs):
        self.updated = False
        for k, v in kwargs.items():
            setattr(evento, k, v)
        evento.save()
        return evento

    def elimina(self, evento):
        self.updated = False
        evento.delete()


class LiveTests(StaticLiveServerTestCase, TuringTests):
    '''Esegue dei test sul calcolo della classifica'''

    def setUp(self):
        super(LiveTests, self).setUp()
        chrome_service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1420,1080')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.selenium = webdriver.Chrome(service=chrome_service, options=chrome_options)
        self.updated = False

        self.user = User.objects.create_user('test', 't@e.st', 'test')

    def tearDown(self):
        self.selenium.quit()
        super().tearDown()

    def debug(self):  # pragma: no cover
        '''Ferma l'esecuzione del test e apre una finestra per il debug.'''
        chrome_service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1420,1080')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome = webdriver.Chrome(service=chrome_service, options=chrome_options)
        url = '{}/engine/'.format(self.live_server_url)
        chrome.get(url)
        input('Premi Invio per continuare...')
        chrome.quit

    def get_classifica(self, tipo):
        '''Naviga alla schermata del tipo indicato, aspettando che abbia dati aggiornati.'''

        url = '{}/engine/classifica/{}/{}'.format(self.live_server_url, self.gara.pk, tipo)

        wait = False
        # Se la pagina richiesta è diversa da quella corrente, naviga in quella pagina.
        # Idem se la gara è finita (perché il browser non farà più richieste)
        if self.selenium.current_url != url or self.gara.finished():
            self.selenium.get('{}/engine/classifica/{}/{}'.format(self.live_server_url, self.gara.pk, tipo))
            wait = True

        # Se la pagina non è cambiata, ma è cambiato qualcosa sul server,
        # dice alla pagina che i suoi dati potrebbero non essere aggiornati
        elif not self.updated:
            self.selenium.execute_script('document.updated = false;')
            wait = True

        # Se la pagina è cambiata, o c'erano dei dati da aggiornare,
        # aspetta che la pagina faccia le richieste AJAX necessarie
        if wait:
            WebDriverWait(self.selenium, 5).until(js_variable_evals_to_true('document.updated'))
            self.updated = True

    def check_punti_squadra(self, squadra, expected=None):
        '''
        Restitiusce il punteggio della squadra indicata.
        Se expected è indicato, controlla che sia uguale al punteggio ottenuto.
        ---
        Parametri:

        squadra - numero identificativo della squadra in quella gara
        expected - punteggio che quella squadra dovrebbe avere se tutto funziona
        '''

        self.get_classifica('squadre')

        punteggio = self.selenium.find_element(By.ID, 'label-points-{}'.format(squadra)).text
        if expected is not None:
            self.assertEqual(
                str(expected), punteggio,
                "La squadra {} ({}) aveva {} punti invece di {}".format(
                    self.gara.squadre.get(num=squadra).nome,
                    squadra, punteggio, expected))

        return int(punteggio)

    def check_posizione_squadra(self, squadra, expected=None):
        '''
        Restitiusce la posizione in classifica della squadra indicata.
        Se expected è indicato, controlla che sia uguale alla posizione ottenuta.
        ---
        Parametri:

        squadra - numero identificativo della squadra in quella gara
        expected - posizione in classifica che quella squadra dovrebbe avere se tutto funziona
        '''

        self.get_classifica('squadre')

        el = self.selenium.find_element(By.ID, 'label-pos-{}'.format(squadra))
        posizione = int(el.text[:-1])
        if expected is not None:
            self.assertEqual(
                expected, posizione,
                "La squadra {} ({}) era in posizione {} invece di {}".format(
                    self.gara.squadre.get(num=squadra).nome,
                    squadra, posizione, expected))

        return posizione

    def check_punti_problema(self, problema, expected_base=None, expected_bonus=None, expected_total=None):
        '''
        Restitiusce il punteggio totale del problema indicato.
        Se expected_base e/o expected_bonus sono indicati, controlla che siano uguale al punteggio base/bonus ottenuti.
        ---
        Parametri:

        problema - numero identificativo del problema
        expected_base - punteggio base che quel problema dovrebbe avere
        expected_bonus - punteggio bonus che quel problema dovrebbe avere
        '''

        self.get_classifica('problemi')

        punteggio_base = self.selenium.find_element(By.ID, 'label-punti-{}'.format(problema)).text
        punteggio_bonus = self.selenium.find_element(By.ID, 'label-bonus-{}'.format(problema)).text
        if punteggio_bonus == "":
            punteggio_bonus = "0"
        if expected_base is not None:
            self.assertEqual(
                str(expected_base), punteggio_base,
                "Il problema {} valeva {} punti base invece di {}".format(
                    problema, punteggio_base, expected_base))

        if expected_bonus is not None:
            self.assertEqual(
                str(expected_bonus), punteggio_bonus,
                "Il problema {} valeva {} punti bonus invece di {}".format(
                    problema, punteggio_bonus, expected_bonus))

        total = int(punteggio_base) + int(punteggio_bonus)
        if expected_total is not None:
            self.assertEqual(
                expected_total, total,
                "Il problema {} valeva {} punti totali invece di {}".format(
                    problema, total, expected_total))
        return total

    #####################
    #  Inizio dei test  #
    #####################

    def test_initial_score(self):
        self.crea_gara(5, [0, 0, 0, 0, 0, 0, 0])
        self.check_punti_squadra(1, 70)

    def test_derivata(self):
        self.crea_gara(5, [42, 9999, 0, 0, 0])
        self.check_punti_squadra(1, 50)

        self.consegna(1, 2, 9999)
        self.check_punti_squadra(1, 90)

        self.go_to_minute(30)
        self.check_punti_squadra(1, 120)

    def test_n_blocco(self):
        self.crea_gara(5, [0, 0, 0])
        self.check_punti_squadra(1, 30)

        self.consegna(1, 1, 0)
        self.go_to_minute(30)
        self.check_punti_problema(1, expected_base=50, expected_bonus=15)

        self.consegna(2, 1, 0)
        self.go_to_minute(60)
        self.check_punti_problema(1, expected_base=50, expected_bonus=10)

    def test_k_blocco(self):
        self.crea_gara(5, [42, 9999, 0, 0, 0])
        self.assertEqual(self.gara.k_blocco, 5)

        self.consegna(2, 2, 76)
        self.check_punti_squadra(2, 40)

        # La squadra 2 sbaglia a raffica
        self.consegna(2, 2, 76)
        self.consegna(2, 2, 76)
        self.consegna(2, 2, 76)
        self.consegna(2, 2, 76)
        self.check_punti_squadra(2, 0)

        # Si è raggiunto il massimo blocco (k=5)
        self.consegna(2, 2, 76)
        self.consegna(1, 2, 9999)
        self.check_punti_squadra(2, -10)
        self.check_punti_squadra(1, 100)

    def test_n_blocco_zero(self):
        self.crea_gara(5, [0, 0, 0], n_blocco=0)

        self.consegna(1, 2, 0)
        self.check_punti_problema(2, expected_base=20)

        self.go_to_minute(20)
        self.consegna(2, 2, 0)
        self.check_punti_problema(2, expected_base=20)

        self.go_to_minute(40)
        self.consegna(3, 2, 0)
        self.check_punti_problema(2, expected_base=20)

        self.check_punti_squadra(1, expected=30+20+20)
        self.check_punti_squadra(2, expected=30+20+15)
        self.check_punti_squadra(3, expected=30+20+10)

    def test_k_blocco_zero(self):
        self.crea_gara(5, [0, 0, 0], k_blocco=0)

        self.consegna(1, 2, 1)
        self.check_punti_problema(2, expected_base=20)

        self.go_to_minute(20)
        self.consegna(2, 2, 1)
        self.check_punti_problema(2, expected_base=40)

        self.go_to_minute(40)
        self.consegna(3, 2, 1)
        self.check_punti_problema(2, expected_base=60)

        self.check_punti_squadra(1, expected=30-10)
        self.check_punti_squadra(2, expected=30-10)
        self.check_punti_squadra(3, expected=30-10)

    def test_n_blocco_null(self):
        self.crea_gara(5, [0, 0, 0], n_blocco=None)

        for i in range(1, 6):
            self.consegna(i, 2, 0)
            self.check_punti_problema(2, expected_base=20*i)
            self.go_to_minute(20*i)

        self.check_punti_squadra(1, expected=30+120+20)
        self.check_punti_squadra(2, expected=30+120+15)
        self.check_punti_squadra(3, expected=30+120+10)
        self.check_punti_squadra(4, expected=30+120+8)
        self.check_punti_squadra(5, expected=30+120+6)

    def test_k_blocco_null(self):
        self.crea_gara(5, [0, 0, 0], k_blocco=None)

        for i in range(1, 6):
            self.consegna(i, 2, 1)
            self.check_punti_problema(2, expected_base=20*i+2*i)
            self.go_to_minute(20*i)

        self.check_punti_squadra(1, expected=30-10)
        self.check_punti_squadra(2, expected=30-10)
        self.check_punti_squadra(3, expected=30-10)
        self.check_punti_squadra(4, expected=30-10)
        self.check_punti_squadra(5, expected=30-10)

    def test_fixed_bonus(self):
        self.crea_gara(20, [42, 0, 0, 0, 0])

        for i in range(20):
            self.consegna(i+1, 1, 42)

        punteggi = [90, 85, 80, 78, 76, 75, 74, 73, 72, 71,
                    70, 70, 70, 70, 70, 70, 70, 70, 70, 70]

        for i in range(20):
            self.check_punti_squadra(i+1, punteggi[i])

    def test_en_plein(self):
        self.crea_gara(20, [0, 0, 0, 0, 0])

        self.assertEqual(self.gara.get_super_mega_bonus_array(), [100, 60, 40, 30, 20, 10])
        self.assertEqual(self.gara.num_problemi, 5)

        for i in range(5):
            self.consegna(1, i+1, 0)
            self.consegna(2, i+1, 0)

        self.check_punti_squadra(1, 50 + 40*5 + 100)
        self.check_punti_squadra(2, 50 + 35*5 + 60)

    # Test squadre ospiti
    def test_n_blocco_ospiti(self):
        self.crea_gara(num_squadre=20, num_ospiti=2, soluzioni=[0, 42, 42, 0, 0], n_blocco=1)
        self.assertEqual(self.gara.n_blocco, 1)

        self.consegna(squadra=1, problema=2, risposta=42)
        self.consegna(squadra=21, problema=3, risposta=42)

        self.go_to_minute(30)

        # La squadra ospite non ha bloccato il punteggio del suo problema
        self.check_punti_squadra(squadra=1, expected=50 + 40)
        self.check_punti_squadra(squadra=21, expected=50 + 70)

        self.consegna(squadra=2, problema=3, risposta=42)

        self.go_to_minute(60)

        # Ora sono bloccati entrambi.
        self.check_punti_squadra(squadra=1, expected=50 + 40)
        self.check_punti_squadra(squadra=21, expected=50 + 70)

    def test_k_blocco_ospiti(self):
        self.crea_gara(num_squadre=20, num_ospiti=2, soluzioni=[0, 42, 42, 0, 0], n_blocco=1)
        self.assertEqual(self.gara.k_blocco, 5)

        # Un errore di una squadra ufficiale fa salire il punteggio di 2
        self.consegna(squadra=1, problema=2, risposta=9999)
        self.check_punti_problema(problema=2, expected_base=22)

        # Un errore di una squadra ospite non fa salire il punteggio di 2
        self.consegna(squadra=21, problema=2, risposta=9999)
        self.check_punti_problema(problema=2, expected_base=22)
        self.check_punti_squadra(squadra=21, expected=50-10)

        # La risposta corretta di un'ospite non fa bloccare k
        self.consegna(squadra=21, problema=2, risposta=42)
        self.check_punti_squadra(squadra=21, expected=50-10+22+20)

        # Altro errore di una squadra ufficiale
        self.consegna(squadra=1, problema=2, risposta=9999)
        self.check_punti_problema(problema=2, expected_base=24)

        # La squadra ospite prende un +2!
        self.check_punti_squadra(squadra=21, expected=50-10+24+20)

        # Ora una squadra risponde correttamente.
        self.consegna(squadra=2, problema=2, risposta=42)
        self.check_punti_squadra(squadra=2, expected=50 + 24 + 20)
        self.check_punti_problema(problema=2, expected_base=24, expected_bonus=15)

        # Il terzo errore non modifica più nulla
        self.consegna(squadra=1, problema=2, risposta=9999)
        self.check_punti_problema(problema=2, expected_base=24)
        self.check_punti_squadra(squadra=21, expected=50 - 10 + 24 + 20)

    def test_bonus_problema_ospiti(self):
        self.crea_gara(num_squadre=20, num_ospiti=2, soluzioni=[0, 42, 42, 0, 0])

        self.check_punti_problema(problema=2, expected_bonus=20)

        # La squadra ufficiale prende il bonus di 20, che poi scende a 15
        self.consegna(squadra=1, problema=2, risposta=42)

        self.check_punti_squadra(squadra=1, expected=50+20+20)
        self.check_punti_problema(problema=2, expected_bonus=15)

        # La squadra ospite prende il bonus di 15, ma questo resta a 15
        self.consegna(squadra=21, problema=2, risposta=42)

        self.check_punti_squadra(squadra=21, expected=50+20+15)
        self.check_punti_problema(problema=2, expected_bonus=15)

        # Come sopra
        self.consegna(squadra=22, problema=2, risposta=42)

        self.check_punti_squadra(squadra=22, expected=50+20+15)
        self.check_punti_problema(problema=2, expected_bonus=15)

        # Consegna ufficiale, il bonus scende a 10
        self.consegna(squadra=2, problema=2, risposta=42)

        self.check_punti_squadra(squadra=2, expected=50+20+15)
        self.check_punti_problema(problema=2, expected_bonus=10)

        # Ancora
        self.consegna(squadra=3, problema=2, risposta=42)

        self.check_punti_squadra(squadra=3, expected=50+20+10)
        self.check_punti_problema(problema=2, expected_bonus=8)

    def test_jolly_presence(self):
        self.crea_gara(num_squadre=5, num_ospiti=0, soluzioni=[0, 0, 0])

        self.put_jolly(squadra=2, problema=2)
        self.put_jolly(squadra=3, problema=3)

        self.consegna(squadra=1, problema=1, risposta=0)

        self.go_to_minute(12)

        self.consegna(squadra=2, problema=2, risposta=1)
        self.consegna(squadra=3, problema=3, risposta=0)

        self.check_punti_squadra(squadra=1, expected=30+2*(20+32))
        self.check_punti_squadra(squadra=2, expected=30+2*(-10))
        self.check_punti_squadra(squadra=3, expected=30+2*(20+32))

    def test_jolly_absence(self):
        self.crea_gara(num_squadre=5, num_ospiti=0, soluzioni=[0, 0, 0], jolly=False)

        self.put_jolly(squadra=2, problema=2)
        self.put_jolly(squadra=3, problema=3)

        self.consegna(squadra=1, problema=1, risposta=0)

        self.go_to_minute(12)

        self.consegna(squadra=2, problema=2, risposta=1)
        self.consegna(squadra=3, problema=3, risposta=0)

        self.check_punti_squadra(squadra=1, expected=30+1*(20+32))
        self.check_punti_squadra(squadra=2, expected=30+1*(-10))
        self.check_punti_squadra(squadra=3, expected=30+1*(20+32))

    def test_gara_full_statica(self):
        """ Test if full static gara works: fixed points to problems, no increments, no bonuses, no jolly"""
        n = 10
        m = 5
        self.crea_gara(num_squadre=n, num_ospiti=0, soluzioni=[0]*m, n_blocco=0, k_blocco=0, jolly=False, fixed_bonus="", super_mega_bonus="")
        problem_points = [10, 20, 30, 50, 100]
        for i in range(m):
            p = Soluzione.objects.get(gara=self.gara, problema=i+1)
            p.punteggio = problem_points[i]
            p.save()

        for i in range(m):
            self.check_punti_problema(problema=i+1, expected_base=problem_points[i], expected_bonus=0)

        points = [m*10]*n
        solved = [set() for _ in range(n)]
        for i in range(25):
            self.go_to_minute(4*(i+1))
            sq = random.randint(1, n)
            prob = random.randint(1, m)
            r = random.randint(0, 1)
            self.consegna(squadra=sq, problema=prob, risposta=r)
            if r != 0:
                points[sq-1] -= 10
            if prob in solved[sq-1]: continue
            if r == 0:
                points[sq-1] += problem_points[prob-1]
                solved[sq-1].add(prob)

        self.go_to_minute(110)
        for i in range(m):
            self.check_punti_problema(problema=i+1, expected_base=problem_points[i], expected_bonus=0)

        for i in range(n):
            self.check_punti_squadra(squadra=i+1, expected=points[i])

    def test_replay_gara_statica(self):
        self.crea_gara(num_squadre=5, num_ospiti=0, soluzioni=[0]*3, n_blocco=0, k_blocco=0, jolly=False, fixed_bonus="", super_mega_bonus="")
        problem_points = [10, 20, 30]
        for i in range(3):
            p = Soluzione.objects.get(gara=self.gara, problema=i+1)
            p.punteggio = problem_points[i]
            p.save()

        self.consegna(squadra=1, problema=1, risposta=1)
        self.consegna(squadra=2, problema=1, risposta=1)
        self.consegna(squadra=3, problema=1, risposta=1)
        self.go_to_minute(150)

        self.check_punti_problema(1,10)
        self.selenium.find_element(By.ID, 'play').click()
        self.assertEqual(self.selenium.find_element(By.ID, 'label-punti-1').text,'10')

    def test_edit_bonus_array(self):
        self.crea_gara(num_squadre=5, n_blocco=10, num_ospiti=0, soluzioni=[0, 0, 0, 0, 0])

        self.consegna(squadra=1, problema=1, risposta=0)
        self.check_punti_squadra(squadra=1, expected=50+20+20)

        self.consegna(squadra=2, problema=1, risposta=0)
        self.check_punti_squadra(squadra=2, expected=50+20+15)

        self.gara.fixed_bonus_array = [40, 5, 0]
        self.gara.save()
        self.updated = False

        self.check_punti_squadra(squadra=1, expected=50+20+40)
        self.check_punti_squadra(squadra=2, expected=50+20+5)

    def test_edit_mega_bonus_array(self):
        self.crea_gara(num_squadre=5, n_blocco=10, num_ospiti=0, soluzioni=[0, 0])

        self.consegna(squadra=1, problema=1, risposta=0)
        self.consegna(squadra=1, problema=2, risposta=0)
        self.check_punti_squadra(squadra=1, expected=20+40+40+100)

        self.consegna(squadra=2, problema=1, risposta=0)
        self.consegna(squadra=2, problema=2, risposta=0)
        self.check_punti_squadra(squadra=2, expected=20+35+35+60)

        self.gara.super_mega_bonus_array = [50]
        self.gara.save()
        self.updated = False

        self.check_punti_squadra(squadra=1, expected=20+40+40+50)
        self.check_punti_squadra(squadra=2, expected=20+35+35+0)

    ###########################
    #        Classifica       #
    ###########################

    def test_classifica_parimerito_gara_statica(self):
        """ Testa se i parimerito vengono risolti controllando l'array ordinato dei punteggi """
        n = 3
        m = 5
        self.crea_gara(num_squadre=n, num_ospiti=0, soluzioni=[0]*m, n_blocco=0, k_blocco=0, jolly=False, fixed_bonus="", super_mega_bonus="")
        problem_points = [10, 20, 30, 50, 100]
        for i in range(m):
            p = Soluzione.objects.get(gara=self.gara, problema=i+1)
            p.punteggio = problem_points[i]
            p.save()

        for i in range(m):
            self.check_punti_problema(problema=i+1, expected_base=problem_points[i], expected_bonus=0)

        consegne = [(1,1,0),(2,4,1),(1,3,0),(2,4,0),(3,5,0)]
        for i, c in enumerate(consegne):
            self.go_to_minute(4*(i+1))
            self.consegna(squadra=c[0], problema=c[1], risposta=c[2])

        self.go_to_minute(110)

        self.check_punti_squadra(squadra=1, expected=m*10+40)
        self.check_punti_squadra(squadra=2, expected=m*10+40)
        self.check_punti_squadra(squadra=3, expected=m*10+100)

        self.check_posizione_squadra(squadra=1, expected=3)
        self.check_posizione_squadra(squadra=2, expected=2)
        self.check_posizione_squadra(squadra=3, expected=1)

    # TODO: test parimerito con jolly

    ###########################
    #  Modifiche agli eventi  #
    ###########################

    def test_simple_amend(self):
        self.crea_gara(num_squadre=20, num_ospiti=2, soluzioni=[0, 42, 0, 0, 0])

        # Registra una risposta sbagliata
        evento = self.consegna(squadra=1, problema=2, risposta=41)
        self.assertIsInstance(evento, Consegna)
        self.check_punti_squadra(squadra=1, expected=50-10)

        # Correggi l'errore: il -10 sparisce
        self.modifica(evento, risposta=42)
        self.check_punti_squadra(squadra=1, expected=50+40)

    def test_abbuono_errori_dopo_modifica(self):
        self.crea_gara(num_squadre=20, num_ospiti=2, soluzioni=[0, 42, 0, 0, 0])

        # Consegna due risposte sbagliate
        evento = self.consegna(squadra=1, problema=2, risposta=41)
        self.consegna(squadra=1, problema=2, risposta=43)
        self.check_punti_squadra(squadra=1, expected=50-10-10)

        # Correggi la prima: la penalità della seconda NON sparisce
        self.modifica(evento, risposta=42)
        self.check_punti_squadra(squadra=1, expected=50+40-10)

        # Un errore successivo viene comunque considerato
        self.consegna(squadra=1, problema=2, risposta=43)
        self.check_punti_squadra(squadra=1, expected=50+40-10-10)

    def test_modifica_consegna_due_squadre(self):
        self.crea_gara(5, n_blocco=10, k_blocco=10, soluzioni=[0, 0])
        evento = self.consegna(squadra=1, problema=1, risposta=1)
        self.consegna(squadra=2, problema=1, risposta=0)
        self.check_punti_squadra(squadra=1, expected=20-10)
        self.check_punti_squadra(squadra=2, expected=20+2+20+20)
        self.modifica(evento, risposta=0)
        self.check_punti_squadra(squadra=1, expected=20+20+20)
        self.check_punti_squadra(squadra=2, expected=20+20+15)

    def test_elimina_consegna_due_squadre(self):
        self.crea_gara(5, n_blocco=10, k_blocco=10, soluzioni=[0, 0])
        evento = self.consegna(squadra=1, problema=1, risposta=1)
        self.consegna(squadra=2, problema=1, risposta=0)
        self.check_punti_squadra(squadra=1, expected=20-10)
        self.check_punti_squadra(squadra=2, expected=20+2+20+20)
        self.elimina(evento)
        self.check_punti_squadra(squadra=1, expected=20)
        self.check_punti_squadra(squadra=2, expected=20+20+20)

    def test_elimina_jolly(self):
        self.crea_gara(5, n_blocco=10, k_blocco=10, soluzioni=[0, 0])
        evento = self.put_jolly(squadra=1, problema=2)
        self.consegna(squadra=1, problema=2, risposta=0)
        self.consegna(squadra=1, problema=1, risposta=1)
        self.check_punti_squadra(squadra=1, expected=20-10+20+20)

        self.go_to_minute(20)
        pt1 = -10
        pt2 = 20+20+20 # base + first blood + derivata
        self.check_punti_squadra(squadra=1, expected=20+pt1+2*pt2)
        self.elimina(evento) # jolly defaults to 1
        self.check_punti_squadra(squadra=1, expected=20+2*pt1+pt2)

    # @skip('Implementare la possibilità di avere delle consegne dopo la fine')
    def test_consegne_finali(self):
        self.crea_gara(20, [0, 42, 0, 0, 0])
        self.go_to_minute(121)
        self.consegna(1, 2, 42)
        self.check_punti_squadra(1, 190)

    def test_json_folder(self):
        test_dir = 'engine/test_gare/'
        for filename in os.listdir(test_dir):
            if filename.endswith(".json"):
                with self.subTest(filename=filename):
                    base, _ = os.path.splitext(filename)
                    with open(os.path.join(test_dir, filename)) as f:
                        self.gara = Gara.create_from_dict(json.load(f))
                    # self.go_to_minute(int(self.gara.durata.seconds / 60))

                    try:
                        with open(os.path.join(test_dir, base + '.score')) as f:
                            scores = json.load(f)
                    except FileNotFoundError: # pragma: no cover
                        scores = [None] * len(self.gara.squadre.all())
                        for s in self.gara.squadre.all():
                            scores[s.num-1] = int(input('Punteggio atteso della squadra {}:'.format(s.nome)))
                        with open(os.path.join(test_dir, base + '.score'), 'w') as f:
                            json.dump(scores, f)

                    for i, score in enumerate(scores):
                        with self.subTest(team_id=i+1):
                            self.check_punti_squadra(i+1, score)

    def test_export_import(self):
        """ Test if exporting a random gara and reimporting it makes sense"""
        n = 20
        m = 8
        self.crea_gara(num_squadre=n, num_ospiti=0, soluzioni=[0]*m)

        for i in range(60):
            self.go_to_minute(2*(i+1))
            sq = random.randint(1, n)
            prob = random.randint(1, m)
            r = random.randint(0, 2)
            self.consegna(squadra=sq, problema=prob, risposta=r)

        self.go_to_minute(130)

        punti_problemi = [0]*m
        for i in range(m):
            punti_problemi[i] = self.check_punti_problema(problema=i+1)

        punti_squadre = [0]*n
        for i in range(n):
            punti_squadre[i] = self.check_punti_squadra(squadra=i+1)

        json_str = self.gara.dump_to_json()
        data = json.loads(json_str)
        self.gara.delete()
        self.gara = Gara.create_from_dict(data)

        for i in range(m):
            self.check_punti_problema(problema=i+1, expected_total=punti_problemi[i])

        for i in range(n):
            self.check_punti_squadra(squadra=i+1, expected=punti_squadre[i])


class HtmlTests(StaticLiveServerTestCase, TuringTests):
    '''Esegue dei test sull'invio dei form'''

    def setUp(self):
        super(HtmlTests, self).setUp()
        chrome_service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1420,1080')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.selenium = webdriver.Chrome(service=chrome_service, options=chrome_options)

        # Crea un utente di test
        self.user = User.objects.create_user('test', 't@e.st', 'test')
        url = self.get_url("login")
        self.selenium.get(url)
        wait_for_element(self.selenium, By.NAME, "username")
        self.selenium.find_element(By.NAME, "username").send_keys("test")
        self.selenium.find_element(By.NAME, "password").send_keys("test")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "a[href='/accounts/password_change/']")

    def tearDown(self):
        self.selenium.quit()
        super().tearDown()

    def get_url(self, name, pk=None):
        if pk:
            return self.live_server_url + reverse(name, kwargs={'pk': pk})
        else:
            return self.live_server_url + reverse(name)

    def test_crea_gara(self):
        self.user.user_permissions.add(Permission.objects.get(codename="add_gara"))
        self.user.save()

        url = self.get_url("engine:gara-new")
        self.selenium.get(url)
        wait_for_element(self.selenium, By.NAME, "nome")
        self.selenium.find_element(By.NAME, "nome").send_keys("prova")
        self.selenium.find_element(By.NAME, "punteggio_iniziale_squadre").send_keys("19")
        self.selenium.find_element(By.NAME, "k_blocco").clear()
        self.selenium.find_element(By.NAME, "k_blocco").send_keys("5")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        gara = Gara.objects.first()
        self.assertEqual(gara.nome, "prova")
        self.assertEqual(gara.punteggio_iniziale_squadre, 19)
        self.assertEqual(gara.k_blocco, 5)

    def test_crea_gara_fail(self):
        self.user.user_permissions.add(Permission.objects.get(codename="add_gara"))
        self.user.save()

        url = self.get_url("engine:gara-new")
        self.selenium.get(url)
        wait_for_element(self.selenium, By.NAME, "nome")
        self.selenium.find_element(By.NAME, "nome").send_keys("prova")
        self.selenium.find_element(By.NAME, "num_problemi").clear()
        self.selenium.find_element(By.ID, "submit").click()
        t.sleep(0.5)

        self.assertEqual(Gara.objects.count(), 0)

    def test_gara_inizia(self):
        self.crea_gara(1, [0], iniziata=False)
        self.gara.admin = self.user
        self.gara.save()

        url = self.get_url("engine:gara-admin", pk=self.gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "submit")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.XPATH, "//p[starts-with(normalize-space(), 'Iniziata')]")
        now = timezone.now()

        self.gara.refresh_from_db()
        self.assertIsInstance(self.gara.inizio, type(timezone.now()))
        self.assertTrue(abs(self.gara.inizio-now) < timedelta(seconds=1))

    def test_inserimento_squadre(self):
        gara = Gara.objects.create(nome="GaraTest", admin=self.user, inizio=timezone.now())
        url = self.get_url("engine:gara-squadre", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "add_more")
        add = self.selenium.find_element(By.ID, "add_more")
        self.selenium.find_element(By.NAME, "form-0-nome").send_keys("sq1")
        add.click()
        self.selenium.find_element(By.NAME, "form-1-nome").send_keys("sq2")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        self.assertEqual(gara.get_squadre(), {
            1: {"nome": "sq1", "ospite": False},
            2: {"nome": "sq2", "ospite": False}
        })

    def test_inserimento_jolly(self):
        self.crea_gara(5, [0, 0, 0])
        self.gara.inseritori.add(self.user)
        url = self.get_url("engine:inserimento", pk=self.gara.pk)
        self.selenium.get(url)

        wait_for_element(self.selenium, By.NAME, "squadra")
        self.selenium.find_element(By.NAME, "squadra").send_keys("01")
        self.selenium.find_element(By.NAME, "problema").send_keys("1")
        self.selenium.find_element(By.NAME, "jolly").send_keys(" ")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-info']")

        jolly = self.gara.get_jolly()
        assert len(jolly) == 1
        # cannot compare IDs reliably with postgres
        jolly[0]['id'] = -1
        self.assertEqual(jolly, [{'id': -1, 'squadra': 1, 'problema': 1}])

    def test_inserimento_bonus(self):
        self.crea_gara(5, [0, 0, 0], admin=self.user)
        url = self.get_url("engine:inserimento", pk=self.gara.pk)
        self.selenium.get(url)

        wait_for_element(self.selenium, By.NAME, "squadra")
        self.selenium.find_element(By.NAME, "squadra").send_keys("01")
        self.selenium.find_element(By.NAME, "risposta").send_keys("-75")
        self.selenium.find_element(By.NAME, "bonus").send_keys(" ")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-info']")

        bonus = self.gara.get_bonus()
        assert len(bonus) == 1
        # cannot compare IDs reliably with postgres
        bonus[0]['id'] = -1
        # do not have an expected timestamp for comparison
        bonus[0].pop('orario')
        self.assertEqual(bonus, [{'id': -1, 'squadra': 1, 'punteggio': -75}])

    def test_inserimento_risposta(self):
        self.crea_gara(5, [0, 0, 0])
        self.gara.inseritori.add(self.user)
        url = self.get_url("engine:inserimento", pk=self.gara.pk)
        self.selenium.get(url)

        wait_for_element(self.selenium, By.NAME, "squadra")
        self.selenium.find_element(By.NAME, "squadra").send_keys("01")
        self.selenium.find_element(By.NAME, "problema").send_keys("1")
        self.selenium.find_element(By.NAME, "risposta").send_keys("0")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-info']")

        c = self.gara.get_consegne()

        self.assertEqual(c[0]["giusta"], True)

    def test_inserimento_vuoto(self):
        self.crea_gara(5, [0, 0, 0])
        self.gara.inseritori.add(self.user)
        url = self.get_url("engine:inserimento", pk=self.gara.pk)
        self.selenium.get(url)

        wait_for_element(self.selenium, By.NAME, "squadra")
        self.selenium.find_element(By.NAME, "squadra").send_keys("01")
        self.selenium.find_element(By.NAME, "problema").send_keys("1")
        self.selenium.find_element(By.ID, "submit").click()
        t.sleep(0.5)

        self.assertFalse(self.gara.eventi.exists())

    def test_inserimento_problema_inesistente(self):
        self.crea_gara(5, [0, 0, 0])
        self.gara.inseritori.add(self.user)
        url = self.get_url("engine:inserimento", pk=self.gara.pk)
        self.selenium.get(url)

        wait_for_element(self.selenium, By.NAME, "squadra")
        self.selenium.find_element(By.NAME, "squadra").send_keys("01")
        self.selenium.find_element(By.NAME, "problema").send_keys("100")
        self.selenium.find_element(By.NAME, "risposta").send_keys("0")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-danger']")

        c = self.gara.get_consegne()

        self.assertEqual(len(c), 0)

    def test_inserimento_problema_negativo(self):
        self.crea_gara(5, [0, 0, 0])
        self.gara.inseritori.add(self.user)
        url = self.get_url("engine:inserimento", pk=self.gara.pk)
        self.selenium.get(url)

        wait_for_element(self.selenium, By.NAME, "squadra")
        self.selenium.find_element(By.NAME, "squadra").send_keys("01")
        self.selenium.find_element(By.NAME, "problema").send_keys("-1")
        self.selenium.find_element(By.NAME, "risposta").send_keys("0")
        self.selenium.find_element(By.ID, "submit").click()
        t.sleep(0.5)

        c = self.gara.get_consegne()

        self.assertEqual(len(c), 0)

    def test_modifica_parametri(self):
        self.crea_gara(num_squadre=3, soluzioni=[1,], num_ospiti=0, n_blocco=2, k_blocco=5, iniziata=True, admin=self.user, durata=timedelta(hours=2), durata_blocco=timedelta(minutes=20))
        gara = Gara.objects.first()

        url = self.get_url("engine:gara-parametri", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.NAME, "nome")
        self.selenium.find_element(By.NAME, "nome").clear()
        self.selenium.find_element(By.NAME, "nome").send_keys("prova")
        self.selenium.find_element(By.NAME, "durata").clear()
        self.selenium.find_element(By.NAME, "durata").send_keys("02:30:00")
        self.selenium.find_element(By.NAME, "durata_blocco").clear()
        self.selenium.find_element(By.NAME, "durata_blocco").send_keys("00:30:00")
        self.selenium.find_element(By.NAME, "k_blocco").clear()
        self.selenium.find_element(By.NAME, "k_blocco").send_keys("6")
        self.selenium.find_element(By.NAME, "num_problemi").clear()
        self.selenium.find_element(By.NAME, "num_problemi").send_keys("7")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        gara = Gara.objects.first()
        self.assertEqual(gara.durata, timedelta(hours=2,minutes=30))
        self.assertEqual(gara.durata_blocco, timedelta(minutes=30))
        self.assertEqual(gara.k_blocco, 6)
        self.assertEqual(gara.num_problemi, 7)
        self.assertEqual(len(Soluzione.objects.filter(gara=gara)), 7)
        self.assertEqual(gara.nome, "prova")

    def test_riduci_problemi(self):
        self.crea_gara(num_squadre=3, soluzioni=[1,2,3,4,5], num_ospiti=0, n_blocco=2, k_blocco=5, iniziata=True, admin=self.user, durata=timedelta(hours=2), durata_blocco=timedelta(minutes=20))
        gara = Gara.objects.first()

        url = self.get_url("engine:gara-parametri", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.NAME, "num_problemi")
        self.selenium.find_element(By.NAME, "num_problemi").clear()
        self.selenium.find_element(By.NAME, "num_problemi").send_keys("3")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        self.assertEqual(len(Soluzione.objects.filter(gara=gara)), 3)

    def test_reset_gara(self):
        self.crea_gara(5, [0,0,0], admin=self.user)
        gara = Gara.objects.first()

        self.put_jolly(1, 3)
        self.put_bonus(2, -98)
        self.consegna(3, 1, 500)

        self.assertEqual(len(Jolly.objects.filter(gara=gara)), 1)
        self.assertEqual(len(Bonus.objects.filter(gara=gara)), 1)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 1)

        url = self.get_url("engine:gara-reset", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "submit")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        self.assertEqual(len(Jolly.objects.filter(gara=gara)), 0)
        self.assertEqual(len(Bonus.objects.filter(gara=gara)), 0)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 0)

    def test_cancellazione_gara(self):
        self.crea_gara(5, [0,0,0], admin=self.user)
        gara = Gara.objects.first()

        self.consegna(1, 1, 500)

        self.assertEqual(len(Gara.objects.filter(pk=gara.pk)), 1)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 1)

        url = self.get_url("engine:gara-delete", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "submit")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        self.assertEqual(len(Gara.objects.filter(pk=gara.pk)), 0)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 0)

    def test_sospensione_ripresa_gara(self):
        self.crea_gara(5, [0,0,0], admin=self.user)

        gara = Gara.objects.first()
        orario_inizio = gara.inizio
        self.assertIsNotNone(orario_inizio)

        sleep_before_events = 1.0
        t.sleep(sleep_before_events)

        orario_jolly = self.put_jolly(1, 3).orario
        orario_bonus = self.put_bonus(2, -98).orario
        orario_consegna = self.consegna(3, 1, 500).orario

        self.assertGreaterEqual((orario_jolly - orario_inizio).total_seconds(), sleep_before_events)
        self.assertGreaterEqual((orario_bonus - orario_inizio).total_seconds(), sleep_before_events)
        self.assertGreaterEqual((orario_consegna - orario_inizio).total_seconds(), sleep_before_events)

        self.assertIsNone(gara.sospensione)

        sleep_before_race_pause = 1.0
        t.sleep(sleep_before_race_pause)

        url = self.get_url("engine:gara-pause", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "submit")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        # Aggiorna l'oggetto gara dopo la modifica dovuta alla sospensione
        gara = Gara.objects.first()

        self.assertIsNotNone(gara.inizio)
        self.assertIsNotNone(gara.sospensione)
        self.assertGreaterEqual(
            (gara.sospensione - orario_inizio).total_seconds(), sleep_before_events + sleep_before_race_pause)

        sleep_before_race_resume = 3.0
        t.sleep(sleep_before_race_resume)

        url = self.get_url("engine:gara-resume", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "submit")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        # Aggiorna l'oggetto gara dopo la modifica dovuta alla ripresa
        gara = Gara.objects.first()

        self.assertIsNone(gara.sospensione)

        nuovo_orario_inizio = gara.inizio
        self.assertIsNotNone(nuovo_orario_inizio)
        self.assertGreaterEqual(
            (nuovo_orario_inizio - orario_inizio).total_seconds(), sleep_before_race_resume)

        nuovo_orario_jolly = Jolly.objects.filter(gara=gara).first().orario
        nuovo_orario_bonus = Bonus.objects.filter(gara=gara).first().orario
        nuovo_orario_consegna = Consegna.objects.filter(gara=gara).first().orario

        self.assertEqual(
            (nuovo_orario_jolly - orario_jolly).total_seconds(),
            (nuovo_orario_inizio - orario_inizio).total_seconds())
        self.assertEqual(
            (nuovo_orario_bonus - orario_bonus).total_seconds(),
            (nuovo_orario_inizio - orario_inizio).total_seconds())
        self.assertEqual(
            (nuovo_orario_consegna - orario_consegna).total_seconds(),
            (nuovo_orario_inizio - orario_inizio).total_seconds())

        self.assertEqual(
            (nuovo_orario_jolly - nuovo_orario_inizio).total_seconds(),
            (orario_jolly - orario_inizio).total_seconds())
        self.assertEqual(
            (nuovo_orario_bonus - nuovo_orario_inizio).total_seconds(),
            (orario_bonus - orario_inizio).total_seconds())
        self.assertEqual(
            (nuovo_orario_consegna - nuovo_orario_inizio).total_seconds(),
            (orario_consegna - orario_inizio).total_seconds())

    def test_doppia_sospensione_gara(self):
        self.crea_gara(5, [0,0,0], admin=self.user)

        gara = Gara.objects.first()
        self.assertIsNone(gara.sospensione)

        url = self.get_url("engine:gara-pause", pk=gara.pk)
        self.selenium.get(url)
        wait_for_element(self.selenium, By.ID, "submit")
        self.selenium.find_element(By.ID, "submit").click()
        wait_for_element(self.selenium, By.CSS_SELECTOR, "div[class*='alert-success']")

        # Interroga di nuovo la pagina di sospensione gara, e conferma che ora non è più presente il bottone
        self.selenium.get(url)
        t.sleep(0.5)
        self.assertEqual(len(self.selenium.find_elements(By.ID, "submit")), 0)

    def test_ripresa_senza_sospensione_gara(self):
        self.crea_gara(5, [0,0,0], admin=self.user)

        gara = Gara.objects.first()
        self.assertIsNone(gara.sospensione)

        url = self.get_url("engine:gara-resume", pk=gara.pk)
        self.selenium.get(url)
        t.sleep(0.5)
        self.assertEqual(len(self.selenium.find_elements(By.ID, "submit")), 0)

    # TODO: test download and reupload


class MyTestCase(TestCase):
    def setUp(self):
        super().setUp()
        # Crea un utente di test
        self.user = User.objects.create_user('test', 't@e.st', 'test')
        self.c = Client()
        self.c.login(username='test', password='test')

    def view_helper(self, get_code=None, post_code=None, follow=True, messages_post=None, form_errors=None):
        if get_code is not None:
            response = self.c.get(self.url, follow=follow)
            self.assertEqual(response.status_code, get_code)

        if post_code is not None:
            response = self.c.post(self.url, self.data, follow=follow)
            self.assertEqual(response.status_code, post_code)
            if messages_post is not None:
                messages = list(response.context["messages"])
                for i, m in enumerate(messages_post):
                    self.assertEqual(messages[i].tags, m["tag"])
                    if "partial" in m and m["partial"]:
                        assert m["message"] in messages[i].message
                    else:
                        self.assertEqual(messages[i].message, m["message"])
            if form_errors is not None:
                form = response.context_data["form"]
                self.assertEqual(dict(form.errors), form_errors)

        return response


class ValidationTests(MyTestCase, TuringTests):
    def test_crea_gara_bonus_negativi(self):
        self.url = reverse('engine:gara-new')
        self.data = {
            "nome": "Prova", "num_problemi": "20", "num_squadre": "10", "durata": "02:00:00", "durata_blocco": "00:20:00", "n_blocco": "2", "punteggio_iniziale_squadre": "", "k_blocco": "5",
            "fixed_bonus_0": "20", "fixed_bonus_1": "15", "fixed_bonus_2": "10", "fixed_bonus_3": "8", "fixed_bonus_4": "6",
            "fixed_bonus_5": "5", "fixed_bonus_6": "4", "fixed_bonus_7": "3", "fixed_bonus_8": "2", "fixed_bonus_9": "-1",
            "super_mega_bonus_0": "100", "super_mega_bonus_1": "60", "super_mega_bonus_2": "40", "super_mega_bonus_3": "30",
            "super_mega_bonus_4": "20", "super_mega_bonus_5": "10", "super_mega_bonus_6": "", "super_mega_bonus_7": "",
            "super_mega_bonus_8": "", "super_mega_bonus_9": ""}

        self.user.user_permissions.add(Permission.objects.get(codename="add_gara"))
        self.user.save()

        self.view_helper(200, 200,
                         messages_post=[{"tag": "danger", "message": "Errore: gara non creata correttamente"}],
                         form_errors = {'fixed_bonus': ['Assicurati che questo valore sia maggiore o uguale a 0.']})

        self.assertFalse(Gara.objects.all().exists())

    def test_inserimento_pregara(self):
        self.crea_gara(5, [0,0,0], iniziata=False)
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'risposta': 76}

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "Gara non ancora iniziata"}])
        self.assertFalse(self.gara.eventi.exists())

    def test_inserimento_gara_futura(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'risposta': 76}

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.go_to_minute(-5)
        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "Non puoi consegnare con un orario precedente all'inizio della gara"}])

    def test_inserimento_durante_sospensione_gara(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'risposta': 76}

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.gara.sospensione = timezone.now()
        self.gara.save()

        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "Gara sospesa"}])
        self.assertFalse(self.gara.eventi.exists())

    def test_inserimento_problema_inesistente(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 100, 'risposta': 76}

        self.view_helper(403, 403)
        self.assertFalse(self.gara.eventi.exists())

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(200, 200,
                         messages_post=[{"tag": "danger", "message": "Inserimento non riuscito. Vedere l'elenco puntato sotto \"Gara: GaraTest - inserimento risposte\" per maggiori dettagli sull'errore."}],
                         form_errors={'__all__': ['Il problema deve esistere']})

        self.assertFalse(self.gara.eventi.exists())

    def test_inserimento_squadra_inesistente(self):
        self.crea_gara(5, [0,0,0])
        altragara = Gara.objects.create(nome="Altra Gara", inizio=timezone.now())
        altrasquadra = Squadra.objects.create(nome="Squadra cusumano", num=1, gara=altragara)
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        self.data = {'squadra': altrasquadra.pk, 'problema': 1, 'risposta': 76}

        self.view_helper(403, 403)
        self.assertFalse(self.gara.eventi.exists())

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(200, 200,
                         messages_post=[{"tag": "danger", "message": "Inserimento non riuscito. Vedere l'elenco puntato sotto \"Gara: GaraTest - inserimento risposte\" per maggiori dettagli sull'errore."}],
                         form_errors={'squadra': ["Scegli un'opzione valida. La scelta effettuata non compare tra quelle disponibili."]})

        self.assertFalse(self.gara.eventi.exists())

    def test_inserimento_jolly_inesistente(self):
        self.crea_gara(5, [0,0,0], jolly=False)
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'jolly': True}

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "Questa gara non prevede l'inserimento di jolly"}])

        self.assertEqual(self.gara.get_jolly(), [])

    def test_modifica_risposta_ok(self):
        self.crea_gara(5, [0,0,0])
        self.gara.inseritori.add(self.user)
        e = self.consegna(1, 1, 500)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq2 = self.gara.squadre.all()[1]
        self.data = {'squadra': sq2.pk, 'problema': 3, 'risposta': 0}

        res = self.gara.get_consegne()
        self.assertEqual(res[0]["squadra"], 1)
        self.assertEqual(res[0]["problema"], 1)
        self.assertEqual(res[0]["giusta"], False)

        self.view_helper(post_code=200)
        res = self.gara.get_consegne()
        self.assertEqual(res[0]["squadra"], 2)
        self.assertEqual(res[0]["problema"], 3)
        self.assertEqual(res[0]["giusta"], True)

    def test_modifica_risposta_vuota(self):
        self.crea_gara(5, [0,0,0])
        self.gara.inseritori.add(self.user)
        e = self.consegna(1, 1, 500)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq1 = self.gara.squadre.all()[0]
        self.data = {'squadra': sq1.pk, 'problema': 1}

        res = self.gara.get_consegne()
        self.assertEqual(res[0]["giusta"], False)

        self.view_helper(post_code=200, form_errors={'risposta': ['Questo campo è obbligatorio.']})
        res = self.gara.get_consegne()
        self.assertEqual(res[0]["giusta"], False)

    def test_modifica_jolly_ok(self):
        self.crea_gara(5, [0,0,0])
        self.gara.inseritori.add(self.user)
        e = self.put_jolly(1, 3)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq4 = self.gara.squadre.all()[3]
        self.data = {'squadra': sq4.pk, 'problema': 2}

        res = self.gara.get_jolly()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 1, 'problema': 3}])

        self.view_helper(post_code=200)
        res = self.gara.get_jolly()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 4, 'problema': 2}])

    def test_modifica_jolly_vuoto(self):
        self.crea_gara(5, [0,0,0])
        self.gara.inseritori.add(self.user)
        e = self.put_jolly(1, 3)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq1 = self.gara.squadre.all()[0]
        self.data = {'squadra': sq1.pk, 'problema': ""}

        res = self.gara.get_jolly()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 1, 'problema': 3}])

        self.view_helper(post_code=200, form_errors={'problema': ['Questo campo è obbligatorio.']})
        res = self.gara.get_jolly()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 1, 'problema': 3}])

    def test_modifica_bonus_ok(self):
        self.crea_gara(5, [0,0,0])
        self.gara.inseritori.add(self.user)
        e = self.put_bonus(1, -98)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq2 = self.gara.squadre.all()[1]
        self.data = {'squadra': sq2.pk, 'risposta': 97}

        res = self.gara.get_bonus()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 1, 'punteggio': -98, 'orario': e.orario}])

        self.view_helper(post_code=200)
        res = self.gara.get_bonus()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 2, 'punteggio': 97, 'orario': e.orario}])

    def test_modifica_bonus_vuoto(self):
        self.crea_gara(5, [0,0,0])
        self.gara.inseritori.add(self.user)
        e = self.put_bonus(1, -98)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq1 = self.gara.squadre.all()[0]
        self.data = {'squadra': sq1.pk, 'risposta': ""}

        res = self.gara.get_bonus()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 1, 'punteggio': -98, 'orario': e.orario}])

        self.view_helper(post_code=200, form_errors={'risposta': ['Questo campo è obbligatorio.']})
        res = self.gara.get_bonus()
        self.assertEqual(res, [{'id': e.pk, 'squadra': 1, 'punteggio': -98, 'orario': e.orario}])


class PermissionTests(MyTestCase, TuringTests):
    def test_crea_gara_permission(self):
        self.url = reverse('engine:gara-new')
        self.data = {
            "nome": "Prova", "num_problemi": "20", "num_squadre": "10", "durata": "02:00:00", "durata_blocco": "00:20:00", "n_blocco": "2", "punteggio_iniziale_squadre": "", "k_blocco": "5",
            "fixed_bonus_0": "20", "fixed_bonus_1": "+15", "fixed_bonus_2": "+10", "fixed_bonus_3": "+8", "fixed_bonus_4": "+6",
            "fixed_bonus_5": "+5", "fixed_bonus_6": "+4", "fixed_bonus_7": "+3", "fixed_bonus_8": "+2", "fixed_bonus_9": "+1",
            "super_mega_bonus_0": "100", "super_mega_bonus_1": "+60", "super_mega_bonus_2": "+40", "super_mega_bonus_3": "+30",
            "super_mega_bonus_4": "+20", "super_mega_bonus_5": "+10", "super_mega_bonus_6": "", "super_mega_bonus_7": "",
            "super_mega_bonus_8": "", "super_mega_bonus_9": ""}

        self.view_helper(403, 403)
        self.assertFalse(Gara.objects.all().exists())

        self.user.user_permissions.add(Permission.objects.get(codename="add_gara"))
        self.user.save()

        self.view_helper(200, 200, messages_post=[{"tag": "success", "message": "Gara creata con successo!"}])

        self.assertTrue(Gara.objects.all().exists())
        gara = Gara.objects.get()
        self.assertEqual(gara.nome, "Prova")
        self.assertEqual(gara.get_super_mega_bonus_array(), [100, 60, 40, 30, 20, 10, 0, 0, 0, 0])

    def test_modifica_parametri_permission(self):
        other = User.objects.create_user('other', 'o@t.her', 'other')
        self.crea_gara(2, [0, 0, 0], admin=other)
        gara = Gara.objects.first()
        self.url = reverse('engine:gara-parametri', kwargs={'pk':gara.pk})
        self.data = {
            "nome": "Prova", "num_problemi": "20", "durata": "02:00:00", "durata_blocco": "00:20:00", "n_blocco": "2", "punteggio_iniziale_squadre": "", "k_blocco": "5",
            "fixed_bonus_0": "20", "fixed_bonus_1": "+15", "fixed_bonus_2": "+10", "fixed_bonus_3": "+8", "fixed_bonus_4": "+6",
            "fixed_bonus_5": "+5", "fixed_bonus_6": "+4", "fixed_bonus_7": "+3", "fixed_bonus_8": "+2", "fixed_bonus_9": "+1",
            "super_mega_bonus_0": "100", "super_mega_bonus_1": "+60", "super_mega_bonus_2": "+40", "super_mega_bonus_3": "+30",
            "super_mega_bonus_4": "+20", "super_mega_bonus_5": "+10", "super_mega_bonus_6": "", "super_mega_bonus_7": "",
            "super_mega_bonus_8": "", "super_mega_bonus_9": ""}
        self.view_helper(403, 403)
        self.assertEqual(gara.nome, 'GaraTest')

    def test_reset_gara(self):
        self.crea_gara(2, [0, 0, 0])
        gara = self.gara
        self.url = reverse('engine:gara-reset', kwargs={'pk': gara.pk})
        self.data = {}

        self.consegna(1, 1, 500)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 1)

        # Un utente a caso non può fare il reset della gara
        self.view_helper(403, 403)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 1)

        # Un inseritore nemmeno
        gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(gara))

        self.view_helper(403, 403)
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 1)

        # Solo l'admin può
        gara.admin = self.user
        gara.save()

        self.view_helper(200, 200, messages_post=[{"tag": "success", "message": "Reset gara avvenuto con successo!"}])
        self.assertEqual(len(Consegna.objects.filter(gara=gara)), 0)

    def test_cancellazione_gara(self):
        self.crea_gara(2, [0, 0, 0])
        gara = self.gara
        self.url = reverse('engine:gara-delete', kwargs={'pk': gara.pk})
        self.data = {}

        self.assertEqual(len(Gara.objects.filter(pk=gara.pk)), 1)

        # Un utente a caso non può cancellare la gara
        self.view_helper(403, 403)
        self.assertEqual(len(Gara.objects.filter(pk=gara.pk)), 1)

        # Un inseritore nemmeno
        gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(gara))

        self.view_helper(403, 403)
        self.assertEqual(len(Gara.objects.filter(pk=gara.pk)), 1)

        # Solo l'admin può
        gara.admin = self.user
        gara.save()

        self.view_helper(200, 200, messages_post=[{"tag": "success", "message": "Gara cancellata con successo!"}])
        self.assertEqual(len(Gara.objects.filter(pk=gara.pk)), 0)

    def test_sospensione_gara(self):
        self.crea_gara(2, [0, 0, 0])
        gara = self.gara
        self.url = reverse('engine:gara-pause', kwargs={'pk': gara.pk})
        self.data = {}

        self.assertIsNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

        # Un utente a caso non può sospendere la gara
        self.view_helper(403, 403)
        self.assertIsNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

        # Un inseritore nemmeno
        gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(gara))

        self.view_helper(403, 403)
        self.assertIsNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

        # Solo l'admin può
        gara.admin = self.user
        gara.save()

        self.view_helper(200, 200, messages_post=[{"tag": "success", "message": "Gara sospesa con successo!"}])
        self.assertIsNotNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

    def test_ripresa_gara(self):
        self.crea_gara(2, [0, 0, 0])
        gara = self.gara
        self.url = reverse('engine:gara-resume', kwargs={'pk': gara.pk})
        self.data = {}

        gara.sospensione = timezone.now()
        gara.save()

        self.assertIsNotNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

        # Un utente a caso non può sospendere la gara
        self.view_helper(403, 403)
        self.assertIsNotNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

        # Un inseritore nemmeno
        gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(gara))

        self.view_helper(403, 403)
        self.assertIsNotNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

        # Solo l'admin può
        gara.admin = self.user
        gara.save()

        self.view_helper(200, 200, messages_post=[{"tag": "success", "message": "Gara ripartita con successo!"}])
        self.assertIsNone(Gara.objects.filter(pk=gara.pk).first().sospensione)

    def test_inserimento_soluzioni(self):
        self.crea_gara(2, [0, 0, 0])
        self.url = reverse('engine:gara-risposte', kwargs={'pk': self.gara.pk})
        self.data = {"form-TOTAL_FORMS": 2, "form-INITIAL_FORMS": 2, "form-0-id": self.gara.soluzioni.get(nome="Problema 1").pk, "form-0-nome": "Problema 1", "form-0-problema": "1", "form-0-risposta": "76", "form-0-punteggio": "20", "form-1-id": self.gara.soluzioni.get(nome="Problema 2").pk, "form-1-nome": "Problema 2", "form-1-problema": "2", "form-1-risposta": "50", "form-1-punteggio": "20"}

        # Un utente a caso non può leggere le soluzioni
        self.view_helper(403, 403)
        self.assertEqual(self.gara.soluzioni.get(nome="Problema 1").risposta, 0)

        # Un inseritore nemmeno
        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(403, 403)
        self.assertEqual(self.gara.soluzioni.get(nome="Problema 1").risposta, 0)

        # Solo l'admin può
        self.gara.admin = self.user
        self.gara.save()

        self.view_helper(200, 200, messages_post=[{"tag": "success", "message": "Soluzioni inserite con successo!"}])
        self.assertEqual(self.gara.soluzioni.get(nome="Problema 1").risposta, 76)
        self.assertEqual(self.gara.soluzioni.get(nome="Problema 2").risposta, 50)
        self.assertEqual(self.gara.soluzioni.get(nome="Problema 3").risposta, 0)

    def test_inserimento_postgara_inseritore(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'risposta': 76}

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.go_to_minute(130)
        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": f"La risposta che hai consegnato è errata.", "partial": True}])
        e = self.gara.eventi.get()
        self.assertEqual(e.as_child().risposta, 76)

    def test_inserimento_postgara_consegnatore(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})

        sq = self.gara.squadre.all()[0]
        sq.consegnatore = self.user
        sq.save()
        self.assertTrue(self.user.can_insert_squadra(sq))

        self.go_to_minute(130)
        self.data = {'squadra': sq.pk, 'problema': 1, 'risposta': 76}
        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "Non puoi consegnare dopo la fine della gara"}])
        self.assertFalse(self.gara.eventi.exists())

    def test_inserimento_risposta(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'risposta': 76}

        self.view_helper(403, 403)
        self.assertFalse(self.gara.eventi.exists())

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": "La risposta che hai consegnato è errata.", "partial": True}])

        self.assertTrue(self.gara.eventi.exists())
        e = self.gara.eventi.get()
        self.assertEqual(e.as_child().risposta, 76)

    def test_inserimento_jolly(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.all()[0]
        self.data = {'squadra': sq.pk, 'problema': 1, 'jolly': True}

        self.view_helper(403, 403)
        self.assertEqual(self.gara.get_jolly(), [])

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": "Inserimento avvenuto", "partial": True}])

        jolly = self.gara.get_jolly()
        assert len(jolly) == 1
        # cannot compare IDs reliably with postgres
        jolly[0]['id'] = -1
        self.assertEqual(jolly, [{'id': -1, 'squadra': 1, 'problema': 1}])

    def test_inserimento_jolly_15min(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})
        sq = self.gara.squadre.get(num=1)
        sq.consegnatore = self.user
        sq.save()
        self.assertTrue(self.user.can_insert_squadra(sq))

        self.go_to_minute(15)
        self.data = {'squadra': sq.pk, 'problema': 1, 'jolly': True}
        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "Non puoi inserire un jolly dopo 15 minuti"}])

        self.assertEqual(self.gara.get_jolly(), [])

    def test_consegnatore(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})

        s1 = Squadra.objects.get(num=1)
        self.data = {'squadra': s1.pk, 'problema': 2, 'jolly': True}

        s2 = Squadra.objects.get(num=2)
        s2.consegnatore = self.user
        s2.save()

        # Status code ok, ma la risposta non è stata validata
        err = {'squadra': ["Scegli un'opzione valida. La scelta effettuata non compare tra quelle disponibili."]}
        self.view_helper(200, 200, form_errors=err)

        self.assertFalse(self.gara.eventi.exists())

        s1.consegnatore = self.user
        s1.save()

        # Stavolta va bene
        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": "Inserimento avvenuto", "partial": True}])
        self.assertTrue(self.gara.eventi.exists())
        self.assertEqual(self.gara.get_jolly(), [{'id': 1, 'squadra': 1, 'problema': 2}])

    def test_filtered_eventi(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})

        u2 = User.objects.create_user('test2','test2@fuffa.com','test2')

        s1 = Squadra.objects.get(num=1)
        s1.consegnatore = self.user
        s1.save()

        s2 = Squadra.objects.get(num=2)
        s2.consegnatore = u2
        s2.save()

        # Inserisce la risposta per la squadra 1
        self.data = {'squadra': s1.pk, 'problema': 2, 'risposta': 76}
        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": "La risposta che hai consegnato è errata.", "partial": True}])

        # Controlla gli eventi visibili
        eventi = self.view_helper(200).context['eventi_recenti']
        self.assertEqual(len(eventi), 1)
        self.assertEqual(eventi[0][1].get_valore(), 76)
        self.assertEqual(eventi[0][1].squadra.num, 1)

        # Si logga come test2
        self.c.login(username='test2',password='test2')

        # Controlla gli eventi visibili
        eventi = self.view_helper(200).context['eventi_recenti']
        self.assertEqual(len(eventi), 0)

        # Inserisce una nuova consegna
        self.data = {'squadra': s2.pk, 'problema': 3, 'jolly': True}
        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": "Inserimento avvenuto", "partial": True}])

        # Controlla gli eventi visibili
        eventi = self.view_helper(200).context['eventi_recenti']
        self.assertEqual(len(eventi), 1)
        self.assertEqual(eventi[0][1].get_valore(), "J")
        self.assertEqual(eventi[0][1].squadra.num, 2)

        # Si logga come test
        self.c.login(username='test',password='test')

        # Continua a vedere solo il suo evento
        eventi = self.view_helper(200).context['eventi_recenti']
        self.assertEqual(len(eventi), 1)
        self.assertEqual(eventi[0][1].get_valore(), 76)
        self.assertEqual(eventi[0][1].squadra.num, 1)

    def test_modifica_evento(self):
        self.crea_gara(5, [0,0,0])
        e = self.consegna(1, 1, 500)
        self.url = reverse('engine:evento-modifica', kwargs={'pk': e.pk})
        sq1 = self.gara.squadre.all()[0]
        self.data = {'squadra': sq1.pk, 'problema': 1, 'risposta': 0}

        self.assertEqual(e.creatore.username, 'test')

        res = self.gara.get_consegne()
        self.assertEqual(res[0]["giusta"], False)

        #Login as other user
        self.user = User.objects.create_user('test2', 't2@e.st', 'test2')
        self.c.login(username='test2', password='test2')

        self.view_helper(403, 403)
        res = self.gara.get_consegne()
        self.assertEqual(res[0]["giusta"], False)

        self.gara.inseritori.add(self.user)

        self.view_helper(403, 403)
        res = self.gara.get_consegne()
        self.assertEqual(res[0]["giusta"], False)

        self.c.login(username='test', password='test')
        self.user = User.objects.get(username='test')
        self.gara.inseritori.add(self.user)
        self.view_helper(post_code=200)
        res = self.gara.get_consegne()
        self.assertEqual(res[0]["giusta"], True)

    def test_elimina_evento(self):
        self.crea_gara(5, [0,0,0])
        e = self.consegna(1, 1, 500)
        self.url = reverse('engine:evento-elimina', kwargs={'pk': e.pk})
        self.data = {}

        self.assertEqual(e.creatore.username, 'test')

        res = self.gara.get_consegne()
        self.assertEqual(len(res), 1)

        #Login come altro utente
        self.user = User.objects.create_user('test2', 't2@e.st', 'test2')
        self.c.login(username='test2', password='test2')

        self.view_helper(post_code=403)
        res = self.gara.get_consegne()
        self.assertEqual(len(res), 1)

        self.gara.inseritori.add(self.user)
        self.view_helper(post_code=403)
        res = self.gara.get_consegne()
        self.assertEqual(len(res), 1)

        # Login come creatore e inseritore
        self.c.login(username='test', password='test')
        self.user = User.objects.get(username='test')
        self.gara.inseritori.add(self.user)
        self.view_helper(post_code=200)
        res = self.gara.get_consegne()
        self.assertEqual(len(res), 0)

    def test_jolly_doppio(self):
        self.crea_gara(5, [0,0,0])
        self.url = reverse('engine:inserimento', kwargs={'pk': self.gara.pk})

        self.gara.inseritori.add(self.user)
        self.assertTrue(self.user.is_inseritore(self.gara))

        sq = self.gara.squadre.all()[0]

        self.data = {'squadra': sq.pk, 'problema': 1, 'jolly': True}
        self.view_helper(200, 200, messages_post=[{"tag": "info", "message": "Inserimento avvenuto", "partial": True}])

        self.data = {'squadra': sq.pk, 'problema': 2, 'jolly': True}
        self.view_helper(200, 200, messages_post=[{"tag": "warning", "message": "È già stato inserito un jolly per la squadra", "partial": True}])

        jolly = self.gara.get_jolly()
        assert len(jolly) == 1
        # cannot compare IDs reliably with postgres
        jolly[0]['id'] = -1
        self.assertEqual(jolly, [{'id': -1, 'squadra': 1, 'problema': 1}])
