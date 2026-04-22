import requests
from bs4 import BeautifulSoup

# Imposta gli URL dell'istanza di Turing
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
# Sostituisci <ID_GARA> con l'id numerico della gara (visibile nell'url)
GARA_ID = 1
INSERISCI_URL = f"{BASE_URL}/engine/inserisci/{GARA_ID}"

# Inizializziamo una Sessione per mantenere i Cookies e il token CSRF
session = requests.Session()

def estrai_csrf_token(html_text):
    """Estrae il token preventivo CSRF obbligatorio nei form di Django."""
    soup = BeautifulSoup(html_text, 'html.parser')
    csrf_input = soup.find('input', dict(name='csrfmiddlewaretoken'))
    if csrf_input:
        return csrf_input['value']
    return None

def login(username, password):
    # 1. Recupera la pagina per generare un token CSRF
    response = session.get(LOGIN_URL)
    csrf_token = estrai_csrf_token(response.text)
    
    # 2. Invia la richiesta di Post
    login_data = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrf_token,
    }
    
    res = session.post(LOGIN_URL, data=login_data, headers={'Referer': LOGIN_URL})
    if "Inserisci" in res.text or res.status_code == 200:
        print(f"Login riuscito per {username}")
        return True
    else:
        print("Login fallito!")
        return False

def invia_risposta(id_squadra, num_problema, risposta, jolly=False):
    # 3. Aggiorna il token CSRF dalla pagina di inserimento
    res_get = session.get(INSERISCI_URL)
    csrf_token = estrai_csrf_token(res_get.text)
    
    # Modella i dati basandoti su turing/engine/forms.py (InserimentoForm)
    data = {
        'csrfmiddlewaretoken': csrf_token,
        'squadra': id_squadra, # Attenzione: questo di solito è il PK nel database di Django, non il numero squadra.
        'problema': num_problema,
        'risposta': risposta,
    }
    
    if jolly:
        data['jolly'] = 'on'
        data['risposta'] = '' # Si lascia invariato in caso di Jolly
        
    res_post = session.post(INSERISCI_URL, data=data, headers={'Referer': INSERISCI_URL})
    
    if res_post.status_code == 200:
        print(f"Risposta {risposta} per il problema {num_problema} elaborata/inviata.")
    else:
        print("Errore nell'invio")

if __name__ == "__main__":
    # In base a Credenziali.csv
    USERNAME = 'kirill01'
    PASSWORD = 'Kirill!2026'
    
    if login(USERNAME, PASSWORD):
        # NOTE: Il valore ID_SQUADRA è l'identificativo Django (Primary Key) passato nella tendina HTML
        # Se non lo conosci o non è il numero della squadra, puoi fare web-scraping sulla pagina INSERISCI_URL 
        # per trovare la giusta opzione (<option value="PK">) utilizzando BeautifulSoup.
        ID_SQUADRA_INTERNO = 1 
        
        invia_risposta(
            id_squadra=ID_SQUADRA_INTERNO,
            num_problema=4,
            risposta=42
        )