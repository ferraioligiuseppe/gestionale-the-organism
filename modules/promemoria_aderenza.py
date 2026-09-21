# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  PROMEMORIA ADERENZA — il cron che chiude il cerchio                 ║
║                                                                      ║
║  Il cruscotto dice chi sta mollando, ma bisogna aprirlo per saperlo. ║
║  Questo modulo manda il messaggio da solo, una volta al giorno.      ║
║                                                                      ║
║  Perche' un cron e non un controllo all'apertura dell'app: Streamlit ║
║  non esegue niente se nessuno apre la pagina. Un promemoria legato   ║
║  all'accesso parte quando capita, e nel fine settimana non parte     ║
║  affatto — proprio quando serve. Lo stesso meccanismo degli ascolti  ║
║  MAPS e dei promemoria eventi: GitHub Actions chiama uno script,     ║
║  lo script chiama questa funzione.                                   ║
║                                                                      ║
║  Due messaggi diversi, perche' sono due problemi diversi:            ║
║    • SOTTO SOGLIA — registrano ma fanno poco. Il messaggio nomina    ║
║      la procedura che salta e chiede se e' quella a non funzionare.  ║
║    • SILENZIO — non segnano piu' niente. Il messaggio chiede solo    ║
║      se stanno continuando: non si da' per scontato che abbiano      ║
║      smesso, perche' spesso hanno solo smesso di registrare.         ║
║                                                                      ║
║  Nessuna famiglia riceve piu' di un messaggio ogni COOLDOWN giorni.  ║
║  Un promemoria che arriva ogni mattina si smette di leggere.         ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import datetime

SOGLIA = 70
FINESTRA = 30
SILENZIO = 7
COOLDOWN = 7          # giorni minimi fra due messaggi alla stessa famiglia
FIRMA = "Studio The Organism — Metodo PNEV"

_LOG_PRONTO = False


# ══════════════════════════════════════════════════════════════════════
#  Registro degli invii
# ══════════════════════════════════════════════════════════════════════

def _assicura_log(conn) -> None:
    global _LOG_PRONTO
    if _LOG_PRONTO:
        return
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS promemoria_aderenza_log (
                id           BIGSERIAL PRIMARY KEY,
                paziente_id  BIGINT NOT NULL,
                email        TEXT,
                tipo         TEXT,
                aderenza     INT,
                inviato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_prom_ader_paz
                       ON promemoria_aderenza_log (paziente_id, inviato_il);""")
        conn.commit()
        _LOG_PRONTO = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _gia_avvisati(conn, giorni=COOLDOWN):
    """Chi ha gia' ricevuto un messaggio negli ultimi giorni."""
    cur = conn.cursor()
    try:
        da = datetime.datetime.now() - datetime.timedelta(days=giorni)
        cur.execute("""SELECT DISTINCT paziente_id FROM promemoria_aderenza_log
                       WHERE inviato_il >= %s""", (da,))
        return {r[0] for r in cur.fetchall()}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return set()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _registra(conn, paziente_id, email, tipo, aderenza):
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO promemoria_aderenza_log
                       (paziente_id, email, tipo, aderenza) VALUES (%s,%s,%s,%s)""",
                    (paziente_id, email, tipo, aderenza))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            cur.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Chi va avvisato
# ══════════════════════════════════════════════════════════════════════

def _candidati(conn, soglia, finestra, silenzio):
    """Pazienti attivi con lavoro a casa, con email del portale, che sono
    sotto soglia o in silenzio. L'email arriva da portale_accessi: senza
    credenziali non c'e' nessuno da avvisare."""
    oggi = datetime.date.today()
    da = oggi - datetime.timedelta(days=finestra)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id, p.cognome, p.nome, a.email,
                   COUNT(*) FILTER (WHERE f.fatto) AS fatti,
                   COUNT(f.id)                     AS totali,
                   MAX(f.data)                     AS ultimo
            FROM pazienti p
            JOIN portale_accessi a ON a.paziente_id = p.id
            LEFT JOIN programma_casa_feedback f
                   ON f.paziente_id = p.id AND f.data >= %s
            WHERE COALESCE(p.stato_paziente, 'ATTIVO') = 'ATTIVO'
            GROUP BY p.id, p.cognome, p.nome, a.email
        """, (da,))
        righe = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    finally:
        try:
            cur.close()
        except Exception:
            pass

    out = []
    for pid, cog, nom, email, fatti, totali, ultimo in righe:
        if not email:
            continue
        nome = f"{(cog or '').strip()} {(nom or '').strip()}".strip() or f"ID {pid}"
        giorni_silenzio = (oggi - ultimo).days if ultimo else None
        pct = round(100 * (fatti or 0) / totali) if totali else None

        if giorni_silenzio is None or giorni_silenzio >= silenzio:
            # Mai nessun feedback in assoluto: puo' essere una famiglia
            # appena registrata. Non la si sollecita al primo giorno.
            if giorni_silenzio is None and not totali:
                continue
            out.append({"id": pid, "nome": nome, "email": email, "tipo": "silenzio",
                        "pct": pct, "silenzio": giorni_silenzio})
        elif pct is not None and pct < soglia:
            out.append({"id": pid, "nome": nome, "email": email, "tipo": "sotto_soglia",
                        "pct": pct, "silenzio": giorni_silenzio})
    return out


def _procedura_debole(conn, paz_id, giorni=21):
    """La procedura piu' saltata, se ce n'e' una che spicca. Serve a
    scrivere un messaggio che parla di qualcosa di preciso invece di
    un generico «fate gli esercizi»."""
    cur = conn.cursor()
    try:
        da = datetime.date.today() - datetime.timedelta(days=giorni)
        cur.execute("""SELECT procedura, COUNT(*) FILTER (WHERE fatto), COUNT(*)
            FROM programma_casa_feedback
            WHERE paziente_id=%s AND data >= %s
            GROUP BY procedura""", (paz_id, da))
        righe = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None, False
    if not righe:
        return None, False
    quote = [(p, (f or 0) / t) for p, f, t in righe if t]
    if not quote:
        return None, False
    quote.sort(key=lambda x: x[1])
    peggiore, q_peggiore = quote[0]
    # «Le altre reggono» solo se e' vero: serve a non accusare la famiglia
    # quando invece e' l'intero carico a essere troppo.
    altre_reggono = len(quote) > 1 and all(q >= 0.6 for _, q in quote[1:])
    if q_peggiore >= 0.5:
        return None, altre_reggono
    return _nome_pulito(peggiore), altre_reggono


def _nome_pulito(proc: str) -> str:
    import re
    p = re.sub(r"^\[[^\]]*\]\s*", "", (proc or "").strip())
    p = re.sub(r"^S\d+\s*·\s*", "", p)
    p = re.sub(r"\s*\([^)]*\)\s*$", "", p)
    return p.strip() or proc


# ══════════════════════════════════════════════════════════════════════
#  Testi
# ══════════════════════════════════════════════════════════════════════

def _testo_silenzio(c):
    giorni = c["silenzio"]
    quando = f"da {giorni} giorni" if giorni else "da un po'"
    return (
        f"Buongiorno,\n\n"
        f"sul portale non risultano aggiornamenti {quando} sugli esercizi a casa.\n\n"
        f"Ci interessa sapere come sta andando, non controllare: capita spesso di "
        f"continuare a fare il lavoro e smettere solo di segnarlo, e per noi sono "
        f"due situazioni diverse.\n\n"
        f"Se ci sono difficolta' a incastrare gli esercizi nella giornata, "
        f"scrivetecelo: il programma si puo' alleggerire o spostare. Meglio poco "
        f"e costante che molto e interrotto.\n\n"
        f"{FIRMA}"
    )


def _testo_sotto_soglia(c, procedura, altre_reggono):
    apertura = (f"Buongiorno,\n\n"
                f"dal portale vediamo che nell'ultimo mese gli esercizi a casa sono "
                f"stati fatti circa {c['pct']} volte su 100.\n\n")
    if procedura and altre_reggono:
        corpo = (f"A saltare e' quasi sempre lo stesso esercizio: «{procedura}». "
                 f"Gli altri procedono regolarmente.\n\n"
                 f"Quando succede cosi', di solito non e' una questione di tempo: "
                 f"e' quell'esercizio che da' fastidio, annoia o non e' chiaro. "
                 f"Ditecelo e lo cambiamo — ci sono altri modi per allenare la "
                 f"stessa cosa.\n\n")
    elif procedura:
        corpo = (f"L'esercizio piu' saltato e' «{procedura}».\n\n"
                 f"Se il programma nel suo insieme e' troppo per le vostre giornate, "
                 f"possiamo ridurlo: meglio due esercizi fatti davvero che quattro "
                 f"sulla carta.\n\n")
    else:
        corpo = ("Se il programma e' troppo pesante per le vostre giornate, possiamo "
                 "ridurlo. Meglio poco e costante che molto e interrotto: e' la "
                 "regolarita' a fare il lavoro, non la quantita' del singolo giorno.\n\n")
    return apertura + corpo + f"Un saluto,\n{FIRMA}"


def _riepilogo_studio(inviati, saltati, soglia):
    righe = []
    silenzio = [c for c in inviati if c["tipo"] == "silenzio"]
    bassi = [c for c in inviati if c["tipo"] == "sotto_soglia"]
    if silenzio:
        righe.append("IN SILENZIO — nessun feedback da giorni:")
        for c in silenzio:
            g = f"{c['silenzio']} giorni" if c["silenzio"] else "mai"
            righe.append(f"  - {c['nome']} (ultimo segno: {g})")
        righe.append("")
    if bassi:
        righe.append(f"SOTTO IL {soglia}% — registrano ma fanno poco:")
        for c in bassi:
            righe.append(f"  - {c['nome']} — {c['pct']}%")
        righe.append("")
    if saltati:
        righe.append(f"Non ricontattati (gia' avvisati negli ultimi {COOLDOWN} giorni): "
                     f"{len(saltati)}")
        righe.append("")
    righe.append("Il dettaglio per paziente, con le singole procedure, e' in "
                 "«Pazienti → Panoramica → Aderenza dello studio».")
    righe.append("")
    righe.append(FIRMA)
    return "\n".join(righe)


# ══════════════════════════════════════════════════════════════════════
#  Esecuzione
# ══════════════════════════════════════════════════════════════════════

def processa_promemoria_aderenza(conn, dry_run: bool = False, email_studio: str = None,
                                 soglia: int = SOGLIA, finestra: int = FINESTRA,
                                 silenzio: int = SILENZIO) -> dict:
    """Manda i promemoria e ritorna un report.

    dry_run=True calcola tutto e non invia niente: e' il modo per vedere
    cosa partirebbe prima di farlo partire davvero."""
    report = {"candidati": 0, "email_inviate": 0, "email_fallite": 0,
              "saltati_cooldown": 0, "dettaglio": [], "errori": []}
    try:
        _assicura_log(conn)
    except Exception as e:
        report["errori"].append(f"Registro invii non disponibile: {e}")
        return report

    candidati = _candidati(conn, soglia, finestra, silenzio)
    report["candidati"] = len(candidati)
    if not candidati:
        return report

    gia = _gia_avvisati(conn)
    inviati, saltati = [], []

    for c in candidati:
        if c["id"] in gia:
            saltati.append(c)
            report["saltati_cooldown"] += 1
            continue

        if c["tipo"] == "silenzio":
            oggetto = "Come vanno gli esercizi a casa?"
            corpo = _testo_silenzio(c)
        else:
            procedura, altre = _procedura_debole(conn, c["id"])
            oggetto = "Un aggiornamento sul lavoro a casa"
            corpo = _testo_sotto_soglia(c, procedura, altre)

        voce = {"paziente": c["nome"], "email": c["email"], "tipo": c["tipo"],
                "aderenza": c["pct"], "oggetto": oggetto}

        if dry_run:
            voce["esito"] = "DRY RUN — non inviata"
            report["dettaglio"].append(voce)
            inviati.append(c)
            continue

        try:
            from modules.ui_questionari import _invia_email
            _invia_email(c["email"], oggetto, corpo)
            _registra(conn, c["id"], c["email"], c["tipo"], c["pct"])
            report["email_inviate"] += 1
            voce["esito"] = "inviata"
            inviati.append(c)
        except Exception as e:
            report["email_fallite"] += 1
            voce["esito"] = f"errore: {e}"
            report["errori"].append(f"{c['nome']}: {e}")
        report["dettaglio"].append(voce)

    if email_studio and inviati:
        try:
            from modules.ui_questionari import _invia_email
            testo = _riepilogo_studio(inviati, saltati, soglia)
            oggetto = f"Aderenza — {len(inviati)} famiglie contattate oggi"
            if not dry_run:
                _invia_email(email_studio, oggetto, testo)
            report["riepilogo_studio"] = testo
        except Exception as e:
            report["errori"].append(f"Riepilogo allo studio non inviato: {e}")

    return report
