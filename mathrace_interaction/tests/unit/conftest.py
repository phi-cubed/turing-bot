# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""pytest configuration file for unit tests."""

import datetime
import io

import pytest

import mathrace_interaction.test
import mathrace_interaction.typing

read_score_file = mathrace_interaction.test.read_score_file_fixture
run_entrypoint = mathrace_interaction.test.run_entrypoint_fixture
runtime_error_contains = mathrace_interaction.test.runtime_error_contains_fixture
ssh_server = mathrace_interaction.test.ssh_server_fixture

_journal_r5539 = """\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
120 022 aggiorna punteggio esercizi, orologio: 2
180 022 aggiorna punteggio esercizi, orologio: 3
240 022 aggiorna punteggio esercizi, orologio: 4
243 010 1 2 squadra 1 sceglie 2 come jolly
251 010 2 3 squadra 2 sceglie 3 come jolly
259 010 3 4 squadra 3 sceglie 4 come jolly
300 022 aggiorna punteggio esercizi, orologio: 5
302 021 timeout jolly
330 011 5 5 1 squadra 5, quesito 5: giusto
341 011 6 6 0 squadra 6, quesito 6: sbagliato
360 022 aggiorna punteggio esercizi, orologio: 6
420 022 aggiorna punteggio esercizi, orologio: 7
435 011 2 3 1 squadra 2, quesito 3: giusto
450 011 3 4 0 squadra 3, quesito 4: sbagliato
480 022 aggiorna punteggio esercizi, orologio: 8
510 011 8 2 0 squadra 8, quesito 2: sbagliato
520 091 7 43 squadra 7 bonus 43
540 022 aggiorna punteggio esercizi, orologio: 9
570 011 9 3 1 squadra 9, quesito 3: giusto
600 022 aggiorna punteggio esercizi, orologio: 10
600 029 termine gara
--- 999 fine simulatore
"""

_journal_r11167 = """\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 squadra 1 sceglie 2 come jolly
251 120 2 3 squadra 2 sceglie 3 come jolly
259 120 3 4 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 squadra 5, quesito 5: giusto
341 110 6 6 0 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 squadra 2, quesito 3: giusto
450 110 3 4 0 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r11184 = """\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
251 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
259 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
341 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
450 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r11189 = """\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
251 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
259 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
341 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
450 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
# the following event 901 differentiates this file from the r11184 one
600 901 avanzamento estrapolato orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r17497 = """\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4.1 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
251 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
259 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
341 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
450 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r17505 = """\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4.1 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
--- 005 1 0 Squadra 1
--- 005 2 0 Squadra 2
--- 005 3 0 Squadra 3
--- 005 4 0 Squadra 4
--- 005 5 0 Squadra 5
--- 005 6 0 Squadra 6
--- 005 7 0 Squadra 7
--- 005 8 0 Squadra 8
--- 005 9 0 Squadra 9
--- 005 10 0 Squadra 10
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
251 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
259 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
341 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
450 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r17548 = """\
--- 001 inizializzazione simulatore
--- 002 10+0:70 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
--- 005 1 0 Squadra 1
--- 005 2 0 Squadra 2
--- 005 3 0 Squadra 3
--- 005 4 0 Squadra 4
--- 005 5 0 Squadra 5
--- 005 6 0 Squadra 6
--- 005 7 0 Squadra 7
--- 005 8 0 Squadra 8
--- 005 9 0 Squadra 9
--- 005 10 0 Squadra 10
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
251 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
259 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
341 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
450 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r20642 = """\
--- 001 inizializzazione simulatore
--- 002 10+0:70 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
--- 011 10 20 15 10 8 6 5 4 3 2 1 definizione dei 10 livelli di bonus
--- 012 6 100 60 40 30 20 10 definizione dei 6 livelli di superbonus
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
--- 005 1 0 Squadra 1
--- 005 2 0 Squadra 2
--- 005 3 0 Squadra 3
--- 005 4 0 Squadra 4
--- 005 5 0 Squadra 5
--- 005 6 0 Squadra 6
--- 005 7 0 Squadra 7
--- 005 8 0 Squadra 8
--- 005 9 0 Squadra 9
--- 005 10 0 Squadra 10
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
120 101 aggiorna punteggio esercizi, orologio: 2
180 101 aggiorna punteggio esercizi, orologio: 3
240 101 aggiorna punteggio esercizi, orologio: 4
243 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
251 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
259 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
300 101 aggiorna punteggio esercizi, orologio: 5
302 121 timeout jolly
330 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
341 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
360 101 aggiorna punteggio esercizi, orologio: 6
420 101 aggiorna punteggio esercizi, orologio: 7
435 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
450 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
480 101 aggiorna punteggio esercizi, orologio: 8
510 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
520 130 7 43 squadra 7 bonus 43
540 101 aggiorna punteggio esercizi, orologio: 9
570 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
600 101 aggiorna punteggio esercizi, orologio: 10
600 210 termine gara
--- 999 fine simulatore
"""

_journal_r20644 = """\
--- 001 inizializzazione simulatore
--- 002 10+0:70 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
--- 011 10 20 15 10 8 6 5 4 3 2 1 definizione dei 10 livelli di bonus
--- 012 6 100 60 40 30 20 10 definizione dei 6 livelli di superbonus
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 20 quesito 7 punteggio iniziale 20
--- 005 1 0 Squadra 1
--- 005 2 0 Squadra 2
--- 005 3 0 Squadra 3
--- 005 4 0 Squadra 4
--- 005 5 0 Squadra 5
--- 005 6 0 Squadra 6
--- 005 7 0 Squadra 7
--- 005 8 0 Squadra 8
--- 005 9 0 Squadra 9
--- 005 10 0 Squadra 10
00:00:00.000 200 inizio gara
00:01:00.000 101 aggiorna punteggio esercizi, orologio: 1
00:02:00.000 101 aggiorna punteggio esercizi, orologio: 2
00:03:00.000 101 aggiorna punteggio esercizi, orologio: 3
00:04:00.000 101 aggiorna punteggio esercizi, orologio: 4
00:04:03.000 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
00:04:11.000 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
00:04:19.000 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
00:05:00.000 101 aggiorna punteggio esercizi, orologio: 5
00:05:02.000 121 timeout jolly
00:05:30.000 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
00:05:41.000 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
00:06:00.000 101 aggiorna punteggio esercizi, orologio: 6
00:07:00.000 101 aggiorna punteggio esercizi, orologio: 7
00:07:15.000 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
00:07:30.000 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
00:08:00.000 101 aggiorna punteggio esercizi, orologio: 8
00:08:30.000 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
00:08:40.000 130 7 43 squadra 7 bonus 43
00:09:00.000 101 aggiorna punteggio esercizi, orologio: 9
00:09:30.000 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
00:10:00.000 101 aggiorna punteggio esercizi, orologio: 10
00:10:00.000 210 termine gara
--- 999 fine simulatore
"""

_journal_r25013 = """\
--- 001 inizializzazione simulatore
--- 002 10+0:70 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
--- 011 10 20 15 10 8 6 5 4 3 2 1 definizione dei 10 livelli di bonus
--- 012 6 100 60 40 30 20 10 definizione dei 6 livelli di superbonus
--- 004 1 20 0000 quesito 1
--- 004 2 20 0000 quesito 2
--- 004 3 20 0000 quesito 3
--- 004 4 20 0000 quesito 4
--- 004 5 20 0000 quesito 5
--- 004 6 20 0000 quesito 6
--- 004 7 20 0000 quesito 7
--- 005 1 0 Squadra 1
--- 005 2 0 Squadra 2
--- 005 3 0 Squadra 3
--- 005 4 0 Squadra 4
--- 005 5 0 Squadra 5
--- 005 6 0 Squadra 6
--- 005 7 0 Squadra 7
--- 005 8 0 Squadra 8
--- 005 9 0 Squadra 9
--- 005 10 0 Squadra 10
00:00:00.000 200 inizio gara
00:01:00.000 101 aggiorna punteggio esercizi, orologio: 1
00:02:00.000 101 aggiorna punteggio esercizi, orologio: 2
00:03:00.000 101 aggiorna punteggio esercizi, orologio: 3
00:04:00.000 101 aggiorna punteggio esercizi, orologio: 4
00:04:03.000 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
00:04:11.000 120 2 3 PROT:2 squadra 2 sceglie 3 come jolly
00:04:19.000 120 3 4 PROT:3 squadra 3 sceglie 4 come jolly
00:05:00.000 101 aggiorna punteggio esercizi, orologio: 5
00:05:02.000 121 timeout jolly
00:05:30.000 110 5 5 1 PROT:4 squadra 5, quesito 5: giusto
00:05:41.000 110 6 6 0 PROT:5 squadra 6, quesito 6: sbagliato
00:06:00.000 101 aggiorna punteggio esercizi, orologio: 6
00:07:00.000 101 aggiorna punteggio esercizi, orologio: 7
00:07:15.000 110 2 3 1 PROT:6 squadra 2, quesito 3: giusto
00:07:30.000 110 3 4 0 PROT:7 squadra 3, quesito 4: sbagliato
00:08:00.000 101 aggiorna punteggio esercizi, orologio: 8
00:08:30.000 110 8 2 0 PROT:8 squadra 8, quesito 2: sbagliato
00:08:40.000 130 7 43 squadra 7 bonus 43
00:09:00.000 101 aggiorna punteggio esercizi, orologio: 9
00:09:30.000 110 9 3 1 PROT:9 squadra 9, quesito 3: giusto
00:10:00.000 101 aggiorna punteggio esercizi, orologio: 10
00:10:00.000 210 termine gara
--- 999 fine simulatore
"""

_journals = {
    "r5539": _journal_r5539, "r11167": _journal_r11167, "r11184": _journal_r11184, "r11189": _journal_r11189,
    "r17497": _journal_r17497, "r17505": _journal_r17505, "r17548": _journal_r17548, "r20642": _journal_r20642,
    "r20644": _journal_r20644, "r25013":_journal_r25013
}


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize tests with journal fixture over journals corresponding to different versions."""
    mathrace_interaction.test.parametrize_journal_fixtures(
        lambda: {journal_version: io.StringIO(journal) for (journal_version, journal) in _journals.items()},
        lambda: {journal_version: journal_version for journal_version in _journals},
        metafunc
    )


@pytest.fixture
def race_name() -> str:
    """Return the name of the race represented by any journal in the journal fixture."""
    return "sample_journal"


@pytest.fixture
def race_date() -> datetime.datetime:
    """Return the date of the race represented by any journal in the journal fixture."""
    return datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)


@pytest.fixture
def turing_dict(race_name: str, race_date: datetime.datetime) -> mathrace_interaction.typing.TuringDict:
    """Return the turing dict associated with the race represented by any journal in the journal fixture."""
    return {
        "nome": race_name,
        "inizio": race_date.isoformat(),
        "durata": 10,
        "durata_blocco": 2,
        "n_blocco": 4,
        "k_blocco": 1,
        "punteggio_iniziale_squadre": 70,
        "fixed_bonus": "20,15,10,8,6,5,4,3,2,1",
        "super_mega_bonus": "100,60,40,30,20,10",
        "jolly": True,
        "num_problemi": 7,
        "soluzioni": [
            {"nome": f"Problema {p}", "problema": p, "punteggio": 20, "risposta": 1} for p in range(1, 8)],
        "squadre": [{"nome": f"Squadra {s}", "num": s, "ospite": False} for s in range(1, 11)],
        "eventi": [
            {
                "subclass": "Jolly",
                "orario": (race_date + datetime.timedelta(minutes=4, seconds=3)).isoformat(),
                "squadra_id": 1,
                "problema": 2
            },
            {
                "subclass": "Jolly",
                "orario": (race_date + datetime.timedelta(minutes=4, seconds=11)).isoformat(),
                "squadra_id": 2,
                "problema": 3
            },
            {
                "subclass": "Jolly",
                "orario": (race_date + datetime.timedelta(minutes=4, seconds=19)).isoformat(),
                "squadra_id": 3,
                "problema": 4
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=5, seconds=30)).isoformat(),
                "squadra_id": 5,
                "problema": 5,
                "risposta": 1
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=5, seconds=41)).isoformat(),
                "squadra_id": 6,
                "problema": 6,
                "risposta": 0
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=7, seconds=15)).isoformat(),
                "squadra_id": 2,
                "problema": 3,
                "risposta": 1
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=7, seconds=30)).isoformat(),
                "squadra_id": 3,
                "problema": 4,
                "risposta": 0
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=8, seconds=30)).isoformat(),
                "squadra_id": 8,
                "problema": 2,
                "risposta": 0
            },
            {
                "subclass": "Bonus",
                "orario": (race_date + datetime.timedelta(minutes=8, seconds=40)).isoformat(),
                "squadra_id": 7,
                "punteggio": 43
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=9, seconds=30)).isoformat(),
                "squadra_id": 9,
                "problema": 3,
                "risposta": 1
            }
        ]
    }
