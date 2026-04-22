function bestCopy(src) {
    return Object.assign({}, src);
}

function increaseSlider(slider, step) {
    slider.triggerHandler('input');
    slider[0].stepUp();
}


class Gara {
    constructor(data, client) {
        // Costruisce la gara a partire dai dati forniti dal server
        this.inizio = new Date(data.inizio);
        if (data.inizio == null) {
            this.inizio = null;
            this._time = null;
        }
        this.client = client;

        this.n_prob = data.n_prob;
        this.fixed_bonus = data.fixed_bonus;
        this.super_mega_bonus = data.super_mega_bonus;
        this.n_blocco = data.n_blocco;
        this.k_blocco = data.k_blocco;
        this.punteggio_iniziale_squadre = data.punteggio_iniziale_squadre;
        this.jolly_enabled = data.jolly_enabled;

        this.penalita_errore = 10;
        this.coefficiente_derivata = 1;
        this.coefficiente_bonus_errori = 2;
        this.coefficiente_jolly = 2;
        this.calcola_punteggio_tempo_iniziale = function(n_prob, penalita_errore, punteggio_iniziale_squadre) {
            if (punteggio_iniziale_squadre != null)
                return punteggio_iniziale_squadre;
            else
                return n_prob * penalita_errore;
        }
        this._scadenza_jolly = 12 * 60 * 1000; // misurato in millisecondi

        this.problemi = {};
        for (var i in data.problemi)
            this.problemi[i] = new Problema(this, i, data.problemi[i]["nome"], data.problemi[i]["punteggio"]);

        this.squadre = {}
        for (var i in data.squadre)
            this.squadre[i] = new Squadra(this, i, data.squadre[i]["nome"], data.squadre[i]["ospite"]);

        if (data.inizio == null) return;

        this.last_update = new Date(data.last_update);
        this.last_consegna_id = 0;
        this.last_jolly_id = 0;
        this.last_bonus_id = 0;
        this._time = this.inizio; // Parte a calcolare dall'inizio della gara
        this.fine = new Date(data.fine);
        this.tempo_blocco = new Date(data.tempo_blocco);
        this.en_plein = 0;

        for (var i in data.jolly) {
            // Imposta quali risposte valgono doppio
            this.add_jolly(data.jolly[i])
        }

        this.futuro_bonus = [];
        this.passato_bonus = [];
        for (var i in data.bonus) {
            this.add_bonus(data.bonus[i])
        }

        this.futuro_consegne = [];
        this.passato_consegne = [];
        for (var i in data.consegne) {
            this.add_consegna(data.consegne[i]);
        }
        this.futuro_consegne_posizioni = [];
        this.passato_consegne_posizioni = [];
    }

    add_jolly(event) {
        var sq_idx = event.squadra
        var prob = event.problema
        this.squadre[sq_idx].jolly = this.squadre[sq_idx].risposte[prob];
        this.squadre[sq_idx].jolly.is_jolly = true;
        this.last_jolly_id = event.id;
    }

    add_consegna(event) {
        this.futuro_consegne.push(new Consegna(this, event));
        this.last_consegna_id = event.id;
    }

    add_bonus(event) {
        this.futuro_bonus.push(new Bonus(this, event));
        this.last_bonus_id = event.id;
    }

    get time() {
        return this._time
    }

    set time(value) {
        var nel_futuro = (value >= this.time); // necessario memorizzare perchè this.update_events cambia internamente il valore a this.time
        console.log("updating consegne");
        this.update_events(value, nel_futuro, this.futuro_consegne, this.passato_consegne, this.futuro_consegne_posizioni, this.passato_consegne_posizioni);
        console.log("updating bonus");
        this.update_events(value, nel_futuro, this.futuro_bonus, this.passato_bonus, null, null);
        // Finalmente, setta il tempo della gara
        this._time = value;
    }

    update_events(new_time, nel_futuro, futuro, passato, futuro_posizioni, passato_posizioni) {
        // Si sposta al tempo specificato, calcolando gli eventi (consegne e bonus) in mezzo
        if (nel_futuro) {
            // Stiamo andando in avanti
            console.log(futuro.length, passato.length, "futuro");
            if (futuro.length > 0) console.log(futuro[0].orario, new_time, "futuro");
            while (futuro.length > 0 && futuro[0].orario <= new_time) {
                // Processa eventi, finché il prossimo non è troppo avanti
                var e = futuro[0];
                this._time = e.orario // Porta la gara all'ora della consegna

                if (e instanceof Consegna) {
                    e.squadra.risposte[e.problema.id].consegna(e.giusta);
                } else if (e instanceof Bonus) {
                    e.squadra.aggiungi_bonus_manuale(e.punteggio)
                }

                passato.push(e);
                futuro.shift();

                if (passato_posizioni !== null && futuro_posizioni !== null) {
                    var classifica_e;
                    if (futuro_posizioni.length > 0) {
                        classifica_e = futuro_posizioni.shift();
                    } else {
                        classifica_e = this.get_classifica_posizioni(this.classifica);
                    }
                    passato_posizioni.push(classifica_e);
                }
            }
        } else {
            // Stiamo tornando indietro
            console.log(futuro.length, passato.length, "passato");
            if (passato.length > 0) console.log(passato[passato.length - 1].orario, new_time, "passato");
            while (passato.length > 0 && passato[passato.length - 1].orario > new_time) {
                var e = passato[passato.length - 1];
                this._time = e.orario // Porta la gara all'ora della consegna

                if (e instanceof Consegna) {
                    e.squadra.risposte[e.problema.id].undo_consegna(e.giusta);
                } else if (e instanceof Bonus) {
                    e.squadra.rimuovi_bonus_manuale(e.punteggio)
                }

                passato.pop();
                futuro.unshift(e);

                if (passato_posizioni !== null && futuro_posizioni !== null) {
                    if (passato_posizioni.length > 0) {
                        classifica_e = passato_posizioni.pop();
                    } else {
                        classifica_e = this.get_classifica_posizioni(this.classifica);
                    }
                    futuro_posizioni.unshift(classifica_e);
                }
            }
        }
    }

    get progess() {
        if (this.inizio == null) return;
        return (this.time - this.inizio) / (this.fine - this.inizio);
    }

    set progress(value) {
        if (this.inizio == null) return;
        // Si sposta al progress specificato, calcolando gli eventi in mezzo
        if (value == null)
            value = this.client.timer.now();
        this.time = new Date(value);
        console.log("progress at time", this.time);
    }

    get soglia_blocco() {
        // Il momento in cui i problemi smettono di salire
        if (this.inizio == null) return new Date();
        return this.tempo_blocco;
    }

    get scadenza_jolly() {
        // Il momento dopo il quale mostrare i jolly
        if (this.inizio == null) return new Date();
        return new Date(this.inizio.getTime() + this._scadenza_jolly);
    }

    get en_plein_bonus() {
        return this.super_mega_bonus[this.en_plein] || 0;
    }

    custom_sort(a, b) {
        // Confronto rispetto al punteggio totale
        if (a.pts < b.pts) return 1
        if (a.pts > b.pts) return -1;

        // In caso di parità tra due squadre prevale quella che ha totalizzato più punti (compresi bonus e penalizzazioni) nel suo problema jolly.
        if (this.jolly_enabled) {
            if (a.squadra.jolly != null) {
                var jolly_a = a.squadra.jolly;
            } else {
                var jolly_a = a.squadra.risposte[1];
            }
            if (b.squadra.jolly != null) {
                var jolly_b = b.squadra.jolly;
            } else {
                var jolly_b = b.squadra.risposte[1];
            }
            var jolly_diff = jolly_b.punteggio - jolly_a.punteggio;
            if (jolly_diff != 0) return jolly_diff;
        }

        // In caso di ulteriore parità, prevale la squadra che ha ottenuto il maggior punteggio per un singolo problema (compresi bonus e penalizzazioni).
        // In caso di ulteriore parità, si guarda il secondo maggior punteggio, e così via.
        var pba = Object.entries(a.squadra.risposte).map(x => x[1].punteggio).sort().reverse();
        var pbb = Object.entries(b.squadra.risposte).map(x => x[1].punteggio).sort().reverse();
        for (var i = 0; i < pba.length; i++) {
            var va = pba[i];
            var vb = pbb[i];
            if (va < vb) return 1;
            if (va > vb) return -1;
        }

        // Infine, in caso di parità in tutti i punteggi, si procederà ad un sorteggio.
        // Il sorteggio qui è simulato con un ordinamento stabile rispetto all'ID della squadra, che è stato assegnato in un sorteggio precedente.
        return a.squadra.id - b.squadra.id;
    }

    get classifica() {
        var ret = [];
        for (var i in this.squadre) {
            ret.push({
                squadra: this.squadre[i],
                pts: this.squadre[i].punteggio
            })
        }
        // Ordina secondo il regolamento
        ret.sort(this.custom_sort.bind(this));
        return ret
    }

    get_classifica_posizioni(classifica) {
        var posizioni = new Array(classifica.length).fill(null);
        for (var i = 0; i < classifica.length; i++) {
            var sq = classifica[i].squadra;
            posizioni[sq.id - 1] = i + 1;
        }
        return posizioni;
    }

    get punti_problemi() {
        var ret = [];
        for (var i in this.problemi) {
            ret.push({
                id: this.problemi[i].id,
                base: this.problemi[i].punti_base,
                bonus: this.problemi[i].bonus
            })
        }
        return ret
    }

}

class Problema {
    // Descrive lo stato di un problema
    constructor(gara, id, nome, punteggio) {
        this.id = id;
        this.gara = gara;
        this.nome = nome;
        this.punteggio = punteggio;
        this.lock_time = (gara.n_blocco == 0) ? gara.inizio : null; // Tempo a cui il problema si è bloccato
        this._risposte_corrette = 0; // Contatore del numero di risposte corrette
        this._risposte_sbagliate = 0; // Contatore delle risposte sbagliate prima della prima soluzione
    }

    // Segnala al problema una nuova risposta, per adeguare il suo valore
    // NON deve essere chiamata dalla risposta di una squadra ospite
    aggiungi_risposta(giusta) {
        if (giusta) {
            this._risposte_corrette += 1;
            if (this._risposte_corrette == this.gara.n_blocco && this.gara.time <= this.gara.soglia_blocco) {
                this.lock_time = this.gara.time
            }
        } else {
            if (this._risposte_corrette == 0 && this.gara.time <= this.gara.soglia_blocco) {
                this._risposte_sbagliate += 1;
            }
        }
    }

    rimuovi_risposta(giusta) {
        // Annulla l'effetto di aggiungi_risposta
        if (giusta) {
            this._risposte_corrette -= 1;
            if (this._risposte_corrette == this.gara.n_blocco - 1 && this.gara.time <= this.gara.soglia_blocco) {
                this.lock_time = null;
            }
        } else {
            if (this._risposte_corrette == 0 && this.gara.time <= this.gara.soglia_blocco) {
                this._risposte_sbagliate -= 1;
            }
        }
    }

    get bloccato() {
        return this.lock_time != null || this.gara.time > this.gara.soglia_blocco
    }

    get punti_base() {
        // Restituisce il valore base del problema
        if (this.lock_time != null)
            var t = this.lock_time;
        else if (this.gara.time > this.gara.soglia_blocco)
            var t = this.gara.soglia_blocco;
        else
            var t = this.gara.time;

        var derivata = Math.floor((t - this.gara.inizio) / 60000) * this.gara.coefficiente_derivata;
        var bonus_errori = this._risposte_sbagliate * this.gara.coefficiente_bonus_errori;
        return this.punteggio + derivata + bonus_errori;
    }

    get bonus() {
        // Restituisce il bonus corrente
        return this.gara.fixed_bonus[this._risposte_corrette] || 0;
    }
}

class Risposta {
    // Descrive lo stato di un problema per una squadra, e contiene il punteggio ottenuto in quel problema
    constructor(squadra, problema) {
        this.squadra = squadra;
        this.gara = squadra.gara;
        this.problema = problema;
        this.risolto = 0;
        this.errori = 0;
        this._is_jolly = false
        this._bonus = 0;
    }

    get is_jolly() {
        if (!this.gara.jolly_enabled) return false;

        if (this.gara.time < this.gara.scadenza_jolly)
            return false;
        else if (this.squadra.jolly == null)
            return this.problema.id == 1;
        else
            return this._is_jolly
    }

    set is_jolly(value) {
        this._is_jolly = value
    }

    consegna(giusta) {
        if (giusta) {
            this.risolto += 1;
            if (this.risolto == 1) {
                this._bonus = this.problema.bonus;
                this.squadra.aggiungi_risposta(true);
                if (!this.squadra.ospite)
                    this.problema.aggiungi_risposta(true);
            }
        } else {
            // if (this.risolto>=1) return;
            this.errori += 1;
            this.squadra.aggiungi_risposta(false);
            if (!this.squadra.ospite && (this.gara.k_blocco == null || this.errori <= this.gara.k_blocco))
                //Dice al problema che c'è un errore solo se non supera k.
                this.problema.aggiungi_risposta(false);
        }
    }

    undo_consegna(giusta) {
        // Annulla una consegna al tempo corrente
        if (giusta) {
            this.risolto -= 1;
            if (this.risolto == 0) {
                this._bonus = this.problema.bonus;
                this.squadra.rimuovi_risposta(true);
                if (!this.squadra.ospite)
                    this.problema.rimuovi_risposta(true);
            }
        } else {
            // if (this.risolto>=1) return;
            this.errori -= 1;
            this.squadra.rimuovi_risposta(false);
            if (!this.squadra.ospite && (this.gara.k_blocco == null || this.errori < this.gara.k_blocco))
                this.problema.rimuovi_risposta(false);
        }
    }

    get punteggio() {
        var pts = 0;
        if (this.risolto) {
            pts += this.problema.punti_base + this._bonus;
        }

        pts -= this.errori * this.gara.penalita_errore;

        if (this.is_jolly)
            pts = pts * this.gara.coefficiente_jolly;

        return pts
    }

    get punteggio_per_premio() {
        // Come il calcolo del punteggio, ma ignora le risposte errate: ri-aggiungi al punteggio calcolato i punti
        // che sono stati persi per via di errori
        var ignora_errori = 0;
        ignora_errori += this.errori * this.gara.penalita_errore;
        if (this.is_jolly)
            ignora_errori = ignora_errori * this.gara.coefficiente_jolly;
        return this.punteggio + ignora_errori;
    }
}

class Squadra {
    constructor(gara, id, nome, ospite = false) {
        this.id = parseInt(id);
        this.nome = nome;
        this.gara = gara;
        this.ospite = ospite;
        this.jolly = null // Indica il problema jolly scelto dalla squadra
        this.risposte = {}
        for (var i in this.gara.problemi) {
            this.risposte[i] = new Risposta(this, this.gara.problemi[i])
        }
        this.bonus_manuale = 0;
        this._risposte_corrette = 0;
        this._en_plein_bonus = 0;
    }

    aggiungi_risposta(giusta) {
        // Dice alla squadra che è stata data una nuova risposta, per calcolare i bonus en plein
        if (giusta) {
            this._risposte_corrette += 1;
            if (this._risposte_corrette == this.gara.n_prob) {
                this._en_plein_bonus = this.gara.en_plein_bonus;
                if (!this.ospite)
                    // Se la squadra non è ospite, shifta l'array dei bonus en plein
                    this.gara.en_plein += 1;
            }
        }
    }

    rimuovi_risposta(giusta) {
        // Annulla l'effetto di aggiungi_risposta
        if (giusta) {
            this._risposte_corrette -= 1;
            if (this._risposte_corrette == this.gara.n_prob - 1) {
                this._en_plein_bonus = 0;
                if (!this.ospite)
                    // Se la squadra non è ospite, shifta l'array dei bonus en plein
                    this.gara.en_plein -= 1;
            }
        }
    }

    aggiungi_bonus_manuale(punteggio) {
        this.bonus_manuale += punteggio;
    }

    rimuovi_bonus_manuale(punteggio) {
        this.bonus_manuale -= punteggio;
    }

    get punteggio() {
        // Calcola il punteggio della squadra
        var pts = this.gara.calcola_punteggio_tempo_iniziale(this.gara.n_prob, this.gara.penalita_errore, this.gara.punteggio_iniziale_squadre);
        pts += this._en_plein_bonus;
        for (var i in this.risposte) {
            pts += this.risposte[i].punteggio
        }
        pts += this.bonus_manuale;
        return pts
    }
}

class Consegna {
    // Descrive una consegna, e contiene le informazioni necessarie per generare un commento
    constructor(gara, data) {
        this.gara = gara;
        this.orario = new Date(data.orario);
        if (this.orario > gara.fine)
            // Se l'evento è avvenuto dopo la fine, fallo accadere alla fine.
            this.orario = new Date(gara.fine);
        this.squadra = gara.squadre[data.squadra];
        this.problema = gara.problemi[data.problema];
        this.giusta = data.giusta;
    }
}

class Bonus {
    // Descrive un bonus manuale
    constructor(gara, data) {
        this.gara = gara;
        this.orario = new Date(data.orario);
        if (this.orario > gara.fine)
            // Se l'evento è avvenuto dopo la fine, fallo accadere alla fine.
            this.orario = new Date(gara.fine);
        this.squadra = gara.squadre[data.squadra];
        this.punteggio = data.punteggio;
    }
}

class ClassificaClient {
    constructor(url, view, timer, following = []) {
        this.url = url;
        this.view = view;
        this.timer = timer;
        this.following = following;
        this.autoplay = 0;
        this.recalculating = false;
        // Impostazione specifica della classifica unica
        var urlParams = new URLSearchParams(window.location.search);
        var blink = urlParams.get("blink");
        this.blink = (blink && !isNaN(blink) && Number.isInteger(parseFloat(blink))) ? parseInt(blink) : 0;
        var position_warn = urlParams.get("position_warn");
        this.position_warn = (position_warn && !isNaN(position_warn) && Number.isInteger(parseFloat(position_warn))) ? parseInt(position_warn) : 0;
        var prize = urlParams.get("prize");
        this.prize = (prize && !isNaN(prize)) ? 1 : 0;
    }

    init() {
        var self = this;
        $.getJSON(this.url).done(function(data) {
            self.recalculating = true;
            self.gara = new Gara(data, self);
            self.timer.init(self.gara.inizio.getTime());
            self.following = data.consegnatore_per
            self.progress = null;
            self.recalculating = false;
        });
    }

    update(progress = null) {
        var self = this;
        if (this.recalculating) return;
        if (this.gara.inizio == null) {
            this.init();
            return
        }
        var last_consegna_id_before = this.gara.last_consegna_id;
        var last_jolly_id_before = this.gara.last_jolly_id;
        var last_bonus_id_before = this.gara.last_bonus_id;
        console.log("Last consegna ID is", last_consegna_id_before, "- last jolly ID is", last_jolly_id_before, "- last bonus ID is", last_bonus_id_before);
        $.getJSON(this.url, {
            last_consegna_id: last_consegna_id_before,
            last_jolly_id: last_jolly_id_before,
            last_bonus_id: last_bonus_id_before
        }).done(function(data) {
            var new_lu = new Date(data.last_update);
            if (new_lu > self.gara.last_update) {
                // C'è stata una modifica grossa, serve un ricalcolo totale
                self.init();
                return;
            }
            // Evitiamo di riconteggiare alcuni eventi già arrivati; succede se la rete sta laggando
            if (self.gara.last_consegna_id > last_consegna_id_before || self.gara.last_jolly_id > last_jolly_id_before || self.gara.last_bonus_id > last_bonus_id_before) return;

            // Aggiungiamo le nuove consegne e jolly
            for (var i in data.consegne) {
                self.gara.add_consegna(data.consegne[i]);
            }
            for (var i in data.jolly) {
                self.gara.add_jolly(data.jolly[i])
            }
            for (var i in data.bonus) {
                self.gara.add_bonus(data.bonus[i])
            }
            self.progress = progress;
        });
    }

    get progress() {
        return this.gara.progress;
    }

    set progress(value) {
        // Porta la gara al punto specificato, e aggiorna l'HTML
        this.gara.progress = value;
        this._aggiornaHTML();
    }

    _aggiornaHTML() {
        this._stampaOrologio();
        switch (this.view) {
            case 'squadre':
                this._mostraClassifica();
                break;
            case 'problemi':
                this._mostraPuntiProblemi();
                break;
            case 'stato':
                this._mostraStatoProblemi();
                break;
            case 'unica':
                this._mostraUnica();
                break;
            case 'scorrimento':
                this._mostraScorrimento();
                break;
        }
        document.dispatchEvent(new Event('updated'));
    }

    _stampaOrologio() {
        if (this.gara.inizio != null) {
            var inizio = new Date(this.gara.inizio);
            var fine = new Date(this.gara.fine);
            var durata = fine - inizio;
            var t_trascorso = Math.min(this.gara.time - inizio, durata); // Se la gara è finita, restituisce la durata
            var res = new Date(t_trascorso).toISOString().substr(11, 8);
            $("#orologio").text(res);
        }
    }

    _mostraClassifica() {
        var classifica = this.gara.classifica;
        var classifica_posizioni = this.gara.get_classifica_posizioni(classifica);
        var max = classifica.length > 0 ? classifica[0].pts : 0;
        max = Math.max(max, this.gara.n_prob * 10 * 4);

        var sq, pts;
        for (var i in classifica) {
            var sq = classifica[i].squadra;
            var pts = classifica[i].pts;
            var pos = classifica_posizioni[sq.id - 1];
            var elapsed = (this.gara.time - this.gara.inizio) / 1000;
            $("#team-" + sq.id).css('width', Math.round(pts / max * 1000) / 10 + '%');
            $("#label-pos-" + sq.id).text(pos + "°");
            $("#label-points-" + sq.id).text(pts);
            $("#label-points-mobile-" + sq.id).text(pts);
        }

        for (const sq_id of this.following) {
            $("#team-" + sq_id).addClass("following");
        }
    }

    _mostraPuntiProblemi() {
        var punti_problemi = this.gara.punti_problemi
        var max = Math.max(...punti_problemi.map((x) => x.base + x.bonus), 80) // Restituisce il max tra 80 e le somme tra base e bonus
        for (var k in punti_problemi) {
            var id = punti_problemi[k].id
            $("#label-" + id).text((id) + " - " + this.gara.problemi[id].nome);
            $("#punti-" + id).css('width', Math.round(punti_problemi[k].base * 100. / max) + '%');
            $("#label-punti-" + id).text(punti_problemi[k].base);
            if (this.gara.problemi[id].bloccato) {
                $("#punti-" + id).removeClass("progress-bar-light");
                $("#punti-" + id).addClass("progress-bar-dark");
            } else {
                $("#punti-" + id).removeClass("progress-bar-dark");
                $("#punti-" + id).addClass("progress-bar-light");
            }
            $("#bonus-" + id).css('width', Math.round(punti_problemi[k].bonus * 100. / max) + '%');
            if (punti_problemi[k].bonus) $("#label-bonus-" + id).text(punti_problemi[k].bonus);
            $("#label-punti-mobile-" + id).text(punti_problemi[k].base + " + " + punti_problemi[k].bonus);
        }
    }

    _mostraStatoProblemi() {
        for (var i in this.gara.squadre) {
            var sq = this.gara.squadre[i];
            for (var j in sq.risposte) {
                var r = sq.risposte[j];
                var text = "";
                $("#cell-" + i + "-" + j).removeClass("wrong-answer right-answer")

                if (r.risolto) {
                    $("#cell-" + i + "-" + j).addClass("right-answer");
                    if (r.errori) {
                        text += '<b>-' + r.errori + '</b>';
                    } else {
                        text += '<b>0</b>';
                    }
                } else if (r.errori) {
                    $("#cell-" + i + "-" + j).addClass("wrong-answer");
                    text += '<b>-' + r.errori + '</b>';
                }

                if (r.is_jolly) {
                    text += ClassificaClient.stella_jolly;
                }

                $("#cell-" + i + "-" + j).html(text);
            }
        }

        for (const sq_id of this.following) {
            $("#riga-" + sq_id).addClass("following");
        }
    }

    _mostraUnica() {
        var punti_problemi = this.gara.punti_problemi
        for (var i in punti_problemi) {
            var text = ""
            var problema = (parseInt(i) + 1)
            text += "#" + ("0" + problema).slice(-2) + "\n" + punti_problemi[i].base + "+" + punti_problemi[i].bonus
            $("#pr-" + problema).html(text)
            var id = punti_problemi[i].id;
            $("#giuste-" + problema).html(this.gara.problemi[id]._risposte_corrette);
            if (this.gara.problemi[id].bloccato) {
                $("#giuste-" + problema).removeClass("progress-bar-light");
                $("#giuste-" + problema).removeClass("progress-bar-zero");
                $("#giuste-" + problema).addClass("progress-bar-dark");
            } else if (this.gara.problemi[id]._risposte_corrette === 0) {
                $("#giuste-" + problema).removeClass("progress-bar-light");
                $("#giuste-" + problema).removeClass("progress-bar-dark");
                $("#giuste-" + problema).addClass("progress-bar-zero");
            } else {
                // almeno una risposta corretta, ma non ancora bloccato
                $("#giuste-" + problema).removeClass("progress-bar-dark");
                $("#giuste-" + problema).removeClass("progress-bar-zero");
                $("#giuste-" + problema).addClass("progress-bar-light");
            }
        }
        // Chiama l'implementazione comune
        var classifica = this.gara.classifica;
        var classifica_posizioni = this.gara.get_classifica_posizioni(classifica);
        this._mostraUnicaOScorrimento(classifica, classifica_posizioni, false, this.prize > 0);
        // Aggiungi lampeggio alla risposta
        var passato_length = this.gara.passato_consegne.length;
        var oldest_blink = Math.min(this.blink, passato_length);
        for (var i = passato_length - oldest_blink; i < passato_length; i++) {
            var e = this.gara.passato_consegne[i];
            var sq = e.squadra;
            var r = e.problema;
            $("#cell-" + classifica_posizioni[sq.id - 1] + "-" + r.id).addClass("blink");
        }
        // Aggiungi frecce per il cambiamento di posizione in classifica
        if (this.blink > 0) {
            $("#freccia-head").show();
            for (var i in classifica) {
                var riga = parseInt(i) + 1;
                $("#freccia-" + riga).show();
            }
            $("#freccia-foot").show();
        }
        if (oldest_blink > 0) {
            var old_idx = Math.max(0, passato_length - oldest_blink - 1);
            var classifica_posizioni_oldest_blink = this.gara.passato_consegne_posizioni[old_idx];
            for (var i in classifica) {
                var sq = classifica[i].squadra;
                var riga = parseInt(i) + 1;
                var differenza_posizioni = classifica_posizioni_oldest_blink[sq.id - 1] - classifica_posizioni[sq.id - 1];
                var freccia;
                if (differenza_posizioni > 0) {
                    freccia = ClassificaClient.freccia_su;
                } else if (differenza_posizioni < 0) {
                    freccia = ClassificaClient.freccia_giu;
                } else {
                    freccia = ClassificaClient.uguale;
                }
                $("#freccia-" + riga).html(freccia);
            }
        } else {
            $("#freccia-" + riga).html();
        }
        // Abilita l'animazione in position_warn_overlay se la squadra è entrata nelle prime posizioni
        console.log("Position warn is", this.position_warn, "and passato length is", passato_length);
        if (this.position_warn > 0 && passato_length > 1) {
            var classifica_posizioni_consegna_precedente = this.gara.passato_consegne_posizioni[(passato_length - 1) - 1];
            for (var i in classifica) {
                var sq = classifica[i].squadra;
                if (classifica_posizioni[sq.id - 1] <= this.position_warn) {
                    var position_warn_element = $("#position_warn_" + classifica_posizioni[sq.id - 1]);
                    var differenza_posizioni = classifica_posizioni_consegna_precedente[sq.id - 1] - classifica_posizioni[sq.id - 1];
                    if (differenza_posizioni > 0 && position_warn_element.attr("data-previous-occupant") !== sq.id.toString()) {
                        position_warn_element.attr("data-previous-occupant", sq.id.toString());
                        position_warn_element.removeClass("position_warn_hide");
                        position_warn_element.addClass("position_warn_show");
                    }
                }
            }
        }
        // Aggiungi bordo per la risposta che vincerebbe il premio
        if (this.prize > 0) {
            // Pulisci le precedenti classi CSS
            for (var i in classifica) {
                var sq = classifica[parseInt(i)].squadra;
                var riga = parseInt(i) + 1;
                for (var j in sq.risposte) {
                    $("#cell-" + riga + "-" + j).removeClass("prize prize-dashed prize-solid prize-gold prize-silver prize-bronze");
                }
            }

            // Crea una mappa dai punteggi per premio alle celle che li hanno ottenuti
            var scoreMap = new Map();
            for (var i in classifica) {
                var sq = classifica[parseInt(i)].squadra;
                var riga = parseInt(i) + 1;
                for (var j in sq.risposte) {
                    var r = sq.risposte[j];
                    if (!r.risolto) continue;
                    var r_prize = r.punteggio_per_premio;
                    if (!scoreMap.has(r_prize)) scoreMap.set(r_prize, []);
                    scoreMap.get(r_prize).push({
                        riga: riga,
                        colonna: j
                    });
                }
            }

            // Estrai i primi tre punteggi per premio, e aggiungi le classi CSS corrispondenti alle celle che li hanno ottenuti
            var scores = Array.from(scoreMap.keys()).sort((a, b) => b - a);
            var topScores = scores.slice(0, 3);

            var medalClass = ["prize-gold", "prize-silver", "prize-bronze"];
            for (var sidx = 0; sidx < topScores.length; sidx++) {
                var s = topScores[sidx];
                var group = scoreMap.get(s);
                var medal = medalClass[sidx];
                var modifier = group.length > 1 ? "prize-dashed" : "prize-solid";
                var cls = "prize " + medal + " " + modifier;
                for (var k = 0; k < group.length; k++) {
                    var cell = group[k];
                    $("#cell-" + cell.riga + "-" + cell.colonna).addClass(cls);
                }
            }
        }
    }

    _mostraScorrimento() {
        var classifica = this.gara.classifica;
        var classifica_posizioni = this.gara.get_classifica_posizioni(classifica);
        this._mostraUnicaOScorrimento(classifica, classifica_posizioni, true, false);
    }

    _mostraUnicaOScorrimento(classifica, classifica_posizioni, reverse, mostra_punteggio_per_premio) {
        var length = classifica.length;
        for (var i in classifica) {
            var sq = classifica[reverse ? length - 1 - parseInt(i) : parseInt(i)].squadra;
            var riga = parseInt(i) + 1;
            if (sq.ospite) $("#riga-" + riga).addClass("text-muted");
            else $("#riga-" + riga).removeClass("text-muted");
            $("#pos-" + riga).html(classifica_posizioni[sq.id - 1] + "° ");
            $("#nome-" + riga).html(sq.nome);
            $("#num-" + riga).html(sq.id);
            if (!mostra_punteggio_per_premio) {
                $("#punt-" + riga).html("" + sq.punteggio);
            }
            for (var j in sq.risposte) {
                var r = sq.risposte[j];
                var text = "";
                $("#cell-" + riga + "-" + j).removeClass("wrong-answer right-answer blink")

                if (r.risolto) {
                    $("#cell-" + riga + "-" + j).addClass("right-answer");
                } else if (r.errori) {
                    $("#cell-" + riga + "-" + j).addClass("wrong-answer");
                }
                if (r.risolto || r.errori) {
                    text += '<span class="punteggio_unica"><b>';
                    if (mostra_punteggio_per_premio) {
                        text += r.punteggio_per_premio;
                    } else {
                        text += r.punteggio;
                    }
                    text += '</b></span>';
                }

                if (r.is_jolly) {
                    text += ClassificaClient.stella_jolly;
                }

                $("#cell-" + riga + "-" + j).html(text);
            }
            if (sq.bonus_manuale + sq._en_plein_bonus != 0) $("#cell-" + riga + "-bonus").html("<span><b>" + (sq.bonus_manuale + sq._en_plein_bonus) + "</b></span>");
            else $("#cell-" + riga + "-bonus").html("");

            if (this.following.includes(sq.id)) $("#riga-" + riga).addClass("following");
            else $("#riga-" + riga).removeClass("following");
        }
    }

    toggleReplay(button, slider_id) {
        this.autoplay = 1 - this.autoplay;
        if (this.autoplay) {
            button.innerHTML = '<i class="fas fa-pause"></i>';
            var slider = $("#" + slider_id);
            if (slider[0].value == slider[0].max) slider[0].value = 0;
            increaseSlider(slider, 1);
            this.autoplayInterval = setInterval(increaseSlider, 100, slider, 1);
        } else {
            button.innerHTML = '<i class="fas fa-play"></i>';
            clearInterval(this.autoplayInterval);
        }
    }
}

ClassificaClient.stella_jolly = `<span class="jolly-fa-stack">
    <i class="fas fa-star fa-stack-1x fa-inverse" style="color:yellow"></i>
    <i class="far fa-star fa-stack-1x" style="color:black"></i>
</span>`;

ClassificaClient.freccia_su = `<span class="arrow-fa-stack">
    <i class="fas fa-arrow-up" style="color:forestgreen"></i>
</span>`;

ClassificaClient.freccia_giu = `<span class="arrow-fa-stack">
    <i class="fas fa-arrow-down" style="color:firebrick"></i>
</span>`;

ClassificaClient.uguale = `<span class="arrow-fa-stack">
    <i class="fas fa-equals" style="color:#212529"></i>
</span>`;
