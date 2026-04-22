#!/usr/bin/env python3
"""Avvia una gara Turing e rigioca in tempo reale le consegne dal file bot.

Flusso:
  1. Login come admin, POST su /engine/gara/<id>/admin con 'inizia=1' per far
     partire la gara.
  2. Logout; login come utente bot.
  3. Scrape /engine/inserisci/<id> per ricavare la mappa num->PK delle squadre.
  4. Per ogni evento nel JSON (Consegna/Jolly/Bonus), dorme fino a
     race_start + offset/speed e POSTa su /engine/inserisci/<id>.

Esempio (dopo aver eseguito setup_gara_bot.py):
  python Testfiles/avvia_gara_bot.py --speed 10
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from dateutil.parser import isoparse

from turing_client import TuringClient, TuringError, die


MARKER_FILE = Path(__file__).parent / ".ultima_gara_bot"


def read_marker(key: str) -> str | None:
    if not MARKER_FILE.exists():
        return None
    for line in MARKER_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()
    return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gara_id", nargs="?", type=int, default=None,
                   help="ID gara. Se omesso, letto da Testfiles/.ultima_gara_bot.")
    p.add_argument("--base-url", default=None)
    p.add_argument("--admin-username", default=None)
    p.add_argument("--admin-password", default=None)
    p.add_argument("--bot-username", default=None)
    p.add_argument("--bot-password", default=None)
    p.add_argument("--bot-file", type=Path, default=None,
                   help="Path JSON gara. Default letto dal marker.")
    p.add_argument("-N", "--num-squadre-reali", type=int, default=None,
                   help="Numero di squadre reali (offset per le bot). Default letto dal marker.")
    p.add_argument("--speed", type=float, default=1.0,
                   help="Fattore di velocità (>1 accelera il replay)")
    p.add_argument("--dry-run", action="store_true",
                   help="Mostra la timeline senza far partire la gara né POSTare")
    p.add_argument("--skip-start", action="store_true",
                   help="Non far partire la gara (gara già iniziata; usa 'now' come riferimento)")
    return p.parse_args()


@dataclass
class ReplayEvent:
    idx: int
    subclass: str  # "Consegna" | "Jolly" | "Bonus"
    offset_s: float
    orig_squadra_num: int
    problema: int | None
    risposta: int | None
    punteggio: int | None


def build_events(bot_json: dict, speed: float) -> list[ReplayEvent]:
    if not bot_json.get("inizio"):
        raise TuringError("Il file bot non ha un campo 'inizio' (serve per calcolare gli offset).")
    inizio = isoparse(bot_json["inizio"])
    eventi_raw = sorted(
        bot_json.get("eventi", []),
        key=lambda e: (e["orario"], e.get("subclass", ""), e.get("squadra_id", 0),
                       e.get("problema", 0)),
    )
    events: list[ReplayEvent] = []
    for i, e in enumerate(eventi_raw):
        offset_s = (isoparse(e["orario"]) - inizio).total_seconds() / max(speed, 1e-9)
        events.append(ReplayEvent(
            idx=i,
            subclass=e.get("subclass", ""),
            offset_s=offset_s,
            orig_squadra_num=int(e.get("squadra_id", 0)),
            problema=e.get("problema"),
            risposta=e.get("risposta"),
            punteggio=e.get("punteggio"),
        ))
    return events


def scrape_squadra_map(client: TuringClient, gara_id: int) -> dict[int, str]:
    """Return {squadra_num: pk} from the squadra dropdown at /engine/inserisci/<id>."""
    path = f"/engine/inserisci/{gara_id}"
    r = client.get(path)
    if r.status_code != 200:
        raise TuringError(f"GET {path} -> {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")
    select = soup.find("select", attrs={"name": "squadra"})
    if select is None:
        raise TuringError(f"Select 'squadra' non trovata in {path}")
    mapping: dict[int, str] = {}
    for opt in select.find_all("option"):
        val = opt.get("value", "").strip()
        txt = opt.get_text(strip=True)
        # Formato da get_id_nome(): "NN - nome"
        m = re.match(r"^(\d+)\s*-\s*", txt)
        if not val or not m:
            continue
        mapping[int(m.group(1))] = val
    if not mapping:
        raise TuringError(f"Nessuna opzione squadra valida in {path}")
    return mapping


def fmt_offset(secs: float) -> str:
    sign = "-" if secs < 0 else ""
    s = int(abs(secs))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{sign}{h:02d}:{m:02d}:{s:02d}"


def start_gara(client: TuringClient, gara_id: int) -> None:
    """POST inizia=1 to start the race. Confirms via following GET."""
    path = f"/engine/gara/{gara_id}/admin"
    token, soup = client.get_csrf(path)
    # Se la gara risulta già iniziata, abort.
    if "Gara ancora da iniziare" not in soup.get_text():
        raise TuringError(
            f"La gara {gara_id} risulta già iniziata (o sospesa). "
            f"Usa --skip-start per eseguire comunque il replay da 'now'.")
    data = {"csrfmiddlewaretoken": token, "inizia": "1"}
    r = client.post(path, data=data, referer=path, allow_redirects=False)
    if r.status_code not in (200, 301, 302):
        raise TuringError(f"POST {path} inizia=1 -> {r.status_code}")


def build_post_data(event: ReplayEvent, csrf: str, squadra_pk: str) -> list[tuple[str, str]]:
    data = [
        ("csrfmiddlewaretoken", csrf),
        ("squadra", squadra_pk),
    ]
    if event.subclass == "Consegna":
        data.append(("problema", str(event.problema)))
        data.append(("risposta", str(event.risposta)))
    elif event.subclass == "Jolly":
        data.append(("problema", str(event.problema)))
        data.append(("risposta", ""))
        data.append(("jolly", "on"))
    elif event.subclass == "Bonus":
        data.append(("problema", ""))
        data.append(("risposta", str(event.punteggio)))
        data.append(("bonus", "on"))
    else:
        raise TuringError(f"Subclass sconosciuta: {event.subclass!r}")
    return data


def summarize_response(resp) -> str:
    """Extract a short outcome from a POST response to /engine/inserisci/."""
    if resp.status_code in (301, 302):
        return "submitted"
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        errs = [e.get_text(" ", strip=True) for e in soup.find_all(class_="errorlist")]
        if errs:
            return f"form errors: {'; '.join(errs)[:200]}"
        return "200 (form invalid; see page)"
    return f"http {resp.status_code}"


def main() -> int:
    args = parse_args()

    gara_id = args.gara_id
    if gara_id is None:
        marker_val = read_marker("gara_id")
        if marker_val is None:
            die("gara_id non specificato e marker .ultima_gara_bot non trovato")
        gara_id = int(marker_val)

    bot_file = args.bot_file
    if bot_file is None:
        marker_val = read_marker("bot_file")
        if marker_val is None:
            die("--bot-file non specificato e marker .ultima_gara_bot non trovato")
        bot_file = Path(marker_val)

    N = args.num_squadre_reali
    if N is None:
        marker_val = read_marker("num_squadre_reali")
        if marker_val is None:
            die("-N non specificato e marker .ultima_gara_bot non trovato")
        N = int(marker_val)

    base_url = args.base_url or read_marker("base_url") or os.environ.get("TURING_BASE_URL", "http://localhost:8000")
    admin_username = args.admin_username or read_marker("admin_username") or os.environ.get("TURING_ADMIN_USER")
    admin_password = args.admin_password or read_marker("admin_password") or os.environ.get("TURING_ADMIN_PASS")
    bot_username = args.bot_username or read_marker("bot_username") or "bot_driver"
    bot_password = args.bot_password or read_marker("bot_password") or os.environ.get("TURING_BOT_PASS")

    if not args.dry_run:
        if not admin_username or not admin_password:
            die("Servono --admin-username e --admin-password")
        if not bot_password:
            die("Serve --bot-password")

    try:
        bot_json = json.loads(Path(bot_file).read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Impossibile leggere {bot_file}: {e}")

    try:
        events = build_events(bot_json, args.speed)
    except TuringError as e:
        die(str(e))

    # --- Dry-run: stampa timeline e esci ---
    if args.dry_run:
        print(f"[dry-run] Gara {gara_id}, {len(events)} eventi, speed={args.speed}, N={N}")
        print(f"[dry-run] {'idx':>4}  {'offset':>9}  subclass  num_orig -> num_bot  payload")
        for e in events:
            remap = e.orig_squadra_num + N
            payload = ""
            if e.subclass == "Consegna":
                payload = f"problema={e.problema} risposta={e.risposta}"
            elif e.subclass == "Jolly":
                payload = f"problema={e.problema}"
            elif e.subclass == "Bonus":
                payload = f"punteggio={e.punteggio}"
            print(f"[dry-run] {e.idx:>4}  {fmt_offset(e.offset_s):>9}  "
                  f"{e.subclass:<8}  {e.orig_squadra_num:>3} -> {remap:>3}  {payload}")
        return 0

    # --- Login admin + avvio gara ---
    admin_client = TuringClient(base_url=base_url)
    try:
        admin_client.login(admin_username, admin_password)
    except TuringError as e:
        die(f"Login admin fallito: {e}")
    print(f"[avvio] Admin {admin_username!r} loggato.")

    if args.skip_start:
        print("[avvio] --skip-start: uso 'now' come race_start.")
        race_start = time.time()
    else:
        try:
            start_gara(admin_client, gara_id)
        except TuringError as e:
            die(str(e))
        race_start = time.time()
        print(f"[avvio] Gara {gara_id} avviata.")

    # --- Login bot user ---
    bot_client = TuringClient(base_url=base_url)
    try:
        bot_client.login(bot_username, bot_password)
    except TuringError as e:
        die(f"Login bot user {bot_username!r} fallito: {e}")
    print(f"[avvio] Bot user {bot_username!r} loggato.")

    # --- Mapping squadra_num -> PK ---
    try:
        pk_by_num = scrape_squadra_map(bot_client, gara_id)
    except TuringError as e:
        die(str(e))
    print(f"[avvio] Trovate {len(pk_by_num)} squadre accessibili al bot user.")

    num_problemi_gara = int(bot_json.get("num_problemi", 0))  # best-effort
    # Se il JSON ha num_problemi diverso dalla gara reale, l'utente può
    # sovrascriverlo; qui usiamo l'hint dal JSON per filtrare.
    # (Gli eventi che eccedono verranno rifiutati dal server comunque.)

    # --- Preparazione CSRF per il primo POST ---
    insert_path = f"/engine/inserisci/{gara_id}"
    csrf_token, _ = bot_client.get_csrf(insert_path)
    csrf_refresh_every = 10  # rinfresca CSRF ogni N POST per sicurezza

    stopping = {"flag": False}

    def on_sigint(signum, frame):  # noqa: ARG001
        if not stopping["flag"]:
            print("\n[avvio] SIGINT ricevuto, interruzione al prossimo evento...", file=sys.stderr)
        stopping["flag"] = True

    signal.signal(signal.SIGINT, on_sigint)

    # --- Loop principale ---
    n_submitted = 0
    n_skipped = 0
    n_errors = 0
    posts_since_refresh = 0

    print(f"[avvio] Inizio replay di {len(events)} eventi (speed={args.speed})")
    for e in events:
        if stopping["flag"]:
            break

        # Filtri pre-POST
        remapped_num = e.orig_squadra_num + N
        if remapped_num not in pk_by_num:
            print(f"  [skip] idx={e.idx} {e.subclass}: squadra remap num={remapped_num} non trovata")
            n_skipped += 1
            continue
        if e.subclass in ("Consegna", "Jolly") and num_problemi_gara and (e.problema or 0) > num_problemi_gara:
            print(f"  [skip] idx={e.idx} {e.subclass}: problema={e.problema} > num_problemi={num_problemi_gara}")
            n_skipped += 1
            continue

        # Sleep fino al target
        target_wall = race_start + e.offset_s
        delay = target_wall - time.time()
        if delay > 0:
            # sleep interruptible checking stopping flag every ~1s
            end = time.time() + delay
            while True:
                if stopping["flag"]:
                    break
                remaining = end - time.time()
                if remaining <= 0:
                    break
                time.sleep(min(1.0, remaining))
        if stopping["flag"]:
            break

        # Refresh CSRF periodicamente
        if posts_since_refresh >= csrf_refresh_every:
            try:
                csrf_token, _ = bot_client.get_csrf(insert_path)
            except TuringError as err:
                print(f"  [warn] refresh CSRF fallito: {err}", file=sys.stderr)
            posts_since_refresh = 0

        data = build_post_data(e, csrf_token, pk_by_num[remapped_num])
        try:
            r = bot_client.post(insert_path, data=data, referer=insert_path,
                                allow_redirects=False)
        except Exception as err:
            print(f"  [err ] idx={e.idx} {e.subclass}: eccezione HTTP: {err}",
                  file=sys.stderr)
            n_errors += 1
            continue

        posts_since_refresh += 1
        outcome = summarize_response(r)
        now_offset = time.time() - race_start
        print(f"  [ok  ] idx={e.idx:>4} @+{fmt_offset(now_offset)} "
              f"{e.subclass:<8} num={remapped_num:>3} -> {outcome}")

        if r.status_code in (301, 302):
            n_submitted += 1
        elif r.status_code == 200:
            # Form invalid (probabilmente rifiutato da maybe_save - es jolly duplicato)
            n_skipped += 1
        else:
            n_errors += 1

    # --- Summary ---
    elapsed = time.time() - race_start
    print()
    print(f"[fine] Eventi inviati: {n_submitted}")
    print(f"[fine] Eventi saltati: {n_skipped}")
    print(f"[fine] Errori HTTP:    {n_errors}")
    print(f"[fine] Tempo trascorso: {fmt_offset(elapsed)}")
    if stopping["flag"]:
        print("[fine] Interrotto da SIGINT prima della fine.")
    return 0 if n_errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
