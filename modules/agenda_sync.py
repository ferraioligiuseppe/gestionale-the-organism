# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  AGENDA SYNC — legge gli appuntamenti dai Google Calendar (iCal)     ║
║                                                                      ║
║  Strada "B→A→C": gli appuntamenti si creano in Google; qui li        ║
║  LEGGIAMO via feed iCal (.ics) — nessuna credenziale/OAuth — e li    ║
║  trasformiamo in una lista giornaliera, provando a collegare ogni    ║
║  evento al paziente in anagrafica (match per nome nel titolo).       ║
║                                                                      ║
║  iCal URL: in Google Calendar → Impostazioni del calendario →        ║
║  "Integra calendario" → "Indirizzo segreto in formato iCal".         ║
║  Per i calendari pubblici funziona anche il formato:                 ║
║  https://calendar.google.com/calendar/ical/<ID>/public/basic.ics     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import datetime as _dt
import urllib.parse
import urllib.request

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Europe/Rome")
except Exception:
    _TZ = None


def ical_url_pubblico(cal_id: str) -> str:
    """URL iCal in formato pubblico a partire dall'ID calendario."""
    return ("https://calendar.google.com/calendar/ical/"
            + urllib.parse.quote(cal_id, safe="") + "/public/basic.ics")


# ─────────────────────────────────────────────────────────────────────
#  FETCH + PARSE ICS (parser minimale, senza librerie esterne)
# ─────────────────────────────────────────────────────────────────────

def _scarica(url: str, timeout: int = 8) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TheOrganism/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _unfold(text: str) -> list[str]:
    """Riunisce le righe 'foldate' dell'iCal (continuano con spazio/tab)."""
    out = []
    for line in text.splitlines():
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _parse_dt(valore: str, params: str):
    """Interpreta DTSTART/DTEND. Ritorna (datetime|date, is_all_day)."""
    v = valore.strip()
    # All-day: VALUE=DATE oppure 8 cifre
    if "VALUE=DATE" in params or (len(v) == 8 and v.isdigit()):
        try:
            return _dt.date(int(v[0:4]), int(v[4:6]), int(v[6:8])), True
        except Exception:
            return None, True
    # Date-time
    try:
        is_utc = v.endswith("Z")
        vv = v[:-1] if is_utc else v
        dt = _dt.datetime.strptime(vv[:15], "%Y%m%dT%H%M%S")
        if is_utc:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
            if _TZ:
                dt = dt.astimezone(_TZ)
        elif _TZ and "TZID=" in params:
            try:
                dt = dt.replace(tzinfo=_TZ)
            except Exception:
                pass
        return dt, False
    except Exception:
        return None, False


def _eventi_da_ics(text: str) -> list[dict]:
    eventi = []
    cur = None
    for line in _unfold(text):
        if line.startswith("BEGIN:VEVENT"):
            cur = {}
        elif line.startswith("END:VEVENT"):
            if cur is not None:
                eventi.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            chiave, valore = line.split(":", 1)
            nome = chiave.split(";", 1)[0].upper()
            params = chiave
            if nome == "SUMMARY":
                cur["titolo"] = valore.strip()
            elif nome == "DESCRIPTION":
                cur["descrizione"] = valore.replace("\\n", " ").strip()
            elif nome == "LOCATION":
                cur["luogo"] = valore.strip()
            elif nome == "DTSTART":
                d, allday = _parse_dt(valore, params)
                cur["inizio"] = d
                cur["all_day"] = allday
            elif nome == "DTEND":
                d, _ = _parse_dt(valore, params)
                cur["fine"] = d
    return eventi


def _solo_data(x):
    if x is None:
        return None
    if isinstance(x, _dt.datetime):
        return x.date()
    return x


# ─────────────────────────────────────────────────────────────────────
#  MATCH PAZIENTE (per nome nel titolo evento)
# ─────────────────────────────────────────────────────────────────────

def carica_pazienti_match(conn) -> list[dict]:
    """Lista minima pazienti per il matching nome→paziente."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cognome, nome FROM pazienti "
            "WHERE COALESCE(stato_paziente,'ATTIVO')='ATTIVO'"
        )
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append({"id": r.get("id"), "cognome": r.get("cognome") or "",
                            "nome": r.get("nome") or ""})
            else:
                out.append({"id": r[0], "cognome": r[1] or "", "nome": r[2] or ""})
        return out
    except Exception:
        return []


def _match_paziente(titolo: str, descrizione: str, pazienti: list[dict]):
    """Cerca un paziente il cui nome compaia nel titolo/descrizione evento."""
    testo = f"{titolo} {descrizione}".upper()
    best = None
    for p in pazienti:
        cog = (p["cognome"] or "").upper().strip()
        nom = (p["nome"] or "").upper().strip()
        if not cog:
            continue
        # match forte: cognome + nome presenti entrambi
        if cog in testo and nom and nom in testo:
            return p
        # match debole: cognome (almeno 4 lettere) presente
        if len(cog) >= 4 and cog in testo and best is None:
            best = p
    return best


# ─────────────────────────────────────────────────────────────────────
#  API: appuntamenti in un intervallo
# ─────────────────────────────────────────────────────────────────────

def appuntamenti(conn, professionisti: list[dict], giorno_da: _dt.date,
                 giorno_a: _dt.date) -> tuple[list[dict], list[dict]]:
    """Ritorna (eventi, errori).

    eventi: lista di dict ordinati per data/ora con:
       data, ora, titolo, prof_nome, prof_color, paziente(dict|None), all_day
    errori: lista di dict {nome, motivo} per i calendari non leggibili.
    """
    pazienti = carica_pazienti_match(conn)
    eventi = []
    errori = []
    for p in professionisti:
        cid = (p.get("cal_id") or "").strip()
        if not cid:
            continue
        url = p.get("ical_url") or ical_url_pubblico(cid)
        text = _scarica(url)
        if not text or "BEGIN:VCALENDAR" not in text:
            errori.append({"nome": p.get("nome", cid),
                           "motivo": "feed non leggibile (serve l'indirizzo iCal segreto)"})
            continue
        for ev in _eventi_da_ics(text):
            d0 = _solo_data(ev.get("inizio"))
            if d0 is None or d0 < giorno_da or d0 > giorno_a:
                continue
            paz = _match_paziente(ev.get("titolo", ""), ev.get("descrizione", ""), pazienti)
            ora = ""
            if isinstance(ev.get("inizio"), _dt.datetime) and not ev.get("all_day"):
                ora = ev["inizio"].strftime("%H:%M")
            eventi.append({
                "data": d0,
                "ora": ora,
                "all_day": ev.get("all_day", False),
                "titolo": ev.get("titolo", "(senza titolo)"),
                "descrizione": ev.get("descrizione", ""),
                "prof_nome": p.get("nome", ""),
                "prof_color": p.get("color", "777777"),
                "paziente": paz,
            })
    eventi.sort(key=lambda e: (e["data"], e["ora"] or "99:99"))
    return eventi, errori
