"""
Modulo Genetica PNEV · proposte automatiche dai dati già nel gestionale.

SOLO LETTURA: legge le valutazioni salvate dagli altri moduli e PROPONE segni HPO «presenti».
Non scrive nulla negli altri moduli e non salva nulla da solo: il clinico conferma ogni proposta.

Regole generali
- Si propongono solo segni PRESENTI, mai «assenti»: molti moduli salvano 0 / valori di default anche
  quando un campo non è stato compilato, quindi un valore normale non dimostra l'assenza del segno.
- Per ogni fonte si usa la valutazione più recente del paziente; la proposta riporta fonte e data.
- Ogni lettore è isolato: se una tabella non esiste o cambia formato, quella fonte viene saltata.

Soglie concordate con il Dott. Ferraioli (1/11/2026)
- INPP: punteggio ≥ 2 su 4 (riflesso primitivo residuo / disfunzione moderata). Le prove dei riflessi
  posturali (scala invertita) sono escluse.
- Stereopsi: Randot/Titmus > 100″.  Refrazione in cicloplegia: ipermetropia ≥ +2,00, miopia ≤ −0,50,
  astigmatismo ≥ 1,00 cil.  PPC: rottura > 10 cm o recupero > 15 cm.
- Udito: media 500-1000-2000-4000 Hz per via aerea > 25 dB HL; gap aereo-osseo medio ≥ 15 dB = trasmissiva.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime

# ---------------------------------------------------------------- soglie
INPP_SOGLIA = 2
STEREO_MAX = 100          # secondi d'arco: oltre = stereopsi anomala
IPERMETROPIA = 2.0        # diottrie (sfera ≥)
MIOPIA = -0.5             # diottrie (sfera ≤)
ASTIGMATISMO = 1.0        # diottrie (|cilindro| ≥)
PPC_ROTTURA = 10.0        # cm
PPC_RECUPERO = 15.0       # cm
PTA_SOGLIA = 25.0         # dB HL
GAP_TRASMISSIVO = 15.0    # dB


@dataclass
class Proposta:
    hpo: str
    fonte: str                       # es. "INPP"
    data: str = ""                   # gg/mm/aaaa
    dettaglio: str = ""              # perché viene proposto
    extra: list = field(default_factory=list)


# ---------------------------------------------------------------- utilità
def _cur(conn):
    return conn.cursor()


def _riga(conn, sql: str, params: tuple):
    """Prima riga o None. Se la tabella non esiste o la query fallisce, None (senza bloccare la pagina)."""
    try:
        cur = _cur(conn)
        try:
            cur.execute(sql, params)
            return cur.fetchone()
        finally:
            try:
                cur.close()
            except Exception:
                pass
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _json(v) -> dict:
    if v is None:
        return {}
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return {}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _data(v) -> str:
    if not v:
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    s = str(v)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


# ---------------------------------------------------------------- INPP
def _inpp(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT risultati, data_valutazione FROM inpp_valutazioni WHERE paziente_id = %s "
                    "ORDER BY data_valutazione DESC NULLS LAST, id DESC LIMIT 1", (pid,))
    if not r:
        return []
    ris, quando = _json(r[0]), _data(r[1])
    if not isinstance(ris, dict):
        return []
    try:
        from modules.inpp.protocollo import itera_prove
        prove = [(s, g, p) for s, g, p in itera_prove("0-4") if not p.get("posturale")]
    except Exception:
        return []

    def alti(filtro) -> list[str]:
        out = []
        for s, g, p in prove:
            if filtro(s, g, p["id"]):
                v = _num(ris.get(p["id"]))
                if v is not None and v >= INPP_SOGLIA:
                    out.append(f"{g} {p.get('label') or p['id']} = {int(v)}")
        return out

    regole = [
        ("HP:0032549", lambda s, g, i: g == "rtac", "RTAC"),
        ("HP:0002476", lambda s, g, i: s == "riflessi" and g in
         ("rtac", "rtsc", "galant", "rtl", "moro", "rooting", "suzione", "prensile_mano", "prensile_piede",
          "rotazione_seg"), "riflessi primitivi"),
        ("HP:0003487", lambda s, g, i: g == "babinsky", "Babinski"),
        ("HP:0002172", lambda s, g, i: g in ("romberg", "mann"), "Romberg / Mann"),
        ("HP:0000617", lambda s, g, i: i == "oc_inseguimento", "inseguimento"),
        ("HP:0025404", lambda s, g, i: i == "oc_fissazione", "fissazione"),
        ("HP:0000619", lambda s, g, i: i in ("oc_conv_latente", "oc_conv_sx", "oc_conv_dx"), "convergenza"),
    ]
    out = []
    for hpo, filtro, nome in regole:
        a = alti(filtro)
        if a:
            out.append(Proposta(hpo, "INPP", quando, f"{nome}: " + "; ".join(a[:4]) + (" …" if len(a) > 4 else "")))
    # Coordinazione: servono almeno 2 prove alterate nella sezione
    for hpo, sez, nome in (("HP:0007015", "coordinazione_equilibrio", "coordinazione globale"),
                           ("HP:0007010", "disdiadococinesia", "disdiadococinesia")):
        a = alti(lambda s, g, i, sez=sez: s == sez and g not in ("romberg", "mann"))
        if len(a) >= 2:
            out.append(Proposta(hpo, "INPP", quando, f"{nome}: {len(a)} prove ≥ {INPP_SOGLIA}"))
    return out


# ---------------------------------------------------------------- visione
_TROPIE = ("esotropia", "exotropia", "ipertropia", "ipotropia")


def _refrazione(rx_od: dict, rx_os: dict, fonte: str, quando: str) -> list[Proposta]:
    out = []
    for occhio, rx in (("OD", rx_od), ("OS", rx_os)):
        if not isinstance(rx, dict):
            continue
        sf, cil = _num(rx.get("sf")), _num(rx.get("cil"))
        if sf is not None and sf >= IPERMETROPIA:
            out.append(Proposta("HP:0000540", fonte, quando, f"cicloplegia {occhio} sf {sf:+.2f}"))
        if sf is not None and sf <= MIOPIA:
            out.append(Proposta("HP:0000545", fonte, quando, f"cicloplegia {occhio} sf {sf:+.2f}"))
        if cil is not None and abs(cil) >= ASTIGMATISMO:
            out.append(Proposta("HP:0000483", fonte, quando, f"cicloplegia {occhio} cil {cil:+.2f}"))
    return out


def _ppc(rot, rec, fonte, quando) -> list[Proposta]:
    rot, rec = _num(rot), _num(rec)
    if (rot and rot > PPC_ROTTURA) or (rec and rec > PPC_RECUPERO):
        return [Proposta("HP:0000619", fonte, quando, f"PPC rottura {rot or '—'} cm, recupero {rec or '—'} cm")]
    return []


def _visuo_percettiva(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT visita_json, data_valutazione FROM valutazioni_visive WHERE paziente_id = %s "
                    "ORDER BY id DESC LIMIT 1", (pid,))
    if not r:
        return []
    v, quando, F = _json(r[0]), _data(r[1]), "Valutazione visuo-percettiva"
    if not isinstance(v, dict):
        return []
    a, b, d = v.get("sez_a") or {}, v.get("sez_b") or {}, v.get("sez_d") or {}
    out = _refrazione(a.get("rc_od") or {}, a.get("rc_os") or {}, F, quando)
    for k, nome in (("ct_l", "lontano"), ("ct_v", "vicino")):
        if str(b.get(k) or "").strip().lower() in _TROPIE:
            out.append(Proposta("HP:0000486", F, quando, f"cover test {nome}: {b.get(k)}"))
    out += _ppc(b.get("ppc_acc_rot"), b.get("ppc_acc_rec"), F, quando)
    for k in ("randot", "titmus"):
        s = _num(b.get(k))
        if s and s > STEREO_MAX:
            out.append(Proposta("HP:0011515", F, quando, f"{k.capitalize()} {int(s)}″"))
    # NSUCO: solo se è stato compilato davvero (i cursori partono tutti da 3)
    compilato = any(_num(d.get(f"{t}_{c}")) not in (None, 3.0)
                    for t in ("sac", "pur") for c in ("ab", "pr", "te", "co"))
    if compilato:
        for k, hpo, nome in (("sacc_pass", "HP:0000570", "saccadi"), ("purs_pass", "HP:0000617", "inseguimenti")):
            n = _num(d.get(k))
            if n is not None and n < 2:
                out.append(Proposta(hpo, F, quando, f"NSUCO {nome}: {int(n)}/4 parametri nella norma"))
    return out


def _oculistica(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT cover_test, ppc_rottura_cm, ppc_recupero_cm, data_visita FROM oculistica_visite "
                    "WHERE paziente_id = %s ORDER BY data_visita DESC NULLS LAST, id DESC LIMIT 1", (pid,))
    if not r:
        return []
    F, quando = "Visita oculistica/optometrica", _data(r[3])
    out = []
    if str(r[0] or "").strip().lower() in _TROPIE:
        out.append(Proposta("HP:0000486", F, quando, f"cover test: {r[0]}"))
    return out + _ppc(r[1], r[2], F, quando)


def _anamnesi_visiva(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT dati_json, data_visita FROM anamnesi_visiva WHERE paziente_id = %s "
                    "ORDER BY id DESC LIMIT 1", (pid,))
    if not r:
        return []
    sint = (_json(r[0]) or {}).get("sintomi") or []
    if "Fotofobia" in sint:
        return [Proposta("HP:0000613", "Anamnesi visiva", _data(r[1]), "sintomo «Fotofobia»")]
    return []


# ---------------------------------------------------------------- udito
def _audiogramma(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT dati_json, data_esame FROM diagnostica_uditiva WHERE paziente_id = %s "
                    "AND tipo = 'Audiogramma' ORDER BY id DESC LIMIT 1", (pid,))
    if not r:
        return []
    d, quando, F = _json(r[0]), _data(r[1]), "Audiogramma"
    idx = (2, 4, 6, 8)   # 500, 1000, 2000, 4000 Hz in FREQS_TON

    def media(lista):
        try:
            vals = [_num(lista[i]) for i in idx]
        except (TypeError, IndexError):
            return None
        vals = [x for x in vals if x is not None]
        return sum(vals) / len(vals) if len(vals) >= 3 else None

    out = []
    for occhio, ac_k, bc_k in (("OD", "od_ac", "od_bc"), ("OS", "os_ac", "os_bc")):
        ac, bc = media(d.get(ac_k)), media(d.get(bc_k))
        if ac is None or ac <= PTA_SOGLIA:
            continue
        orecchio = "dx" if occhio == "OD" else "sx"
        if bc is not None and ac - bc >= GAP_TRASMISSIVO:
            out.append(Proposta("HP:0000405", F, quando, f"orecchio {orecchio}: via aerea {ac:.0f} dB, gap {ac - bc:.0f} dB"))
        elif bc is not None and bc > PTA_SOGLIA:
            out.append(Proposta("HP:0000407", F, quando, f"orecchio {orecchio}: aerea {ac:.0f} dB, ossea {bc:.0f} dB"))
        else:
            out.append(Proposta("HP:0000365", F, quando, f"orecchio {orecchio}: via aerea {ac:.0f} dB (ossea non misurata)"))
    return out


# ---------------------------------------------------------------- anamnesi
def _prima_infanzia(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT dati, aggiornato_il FROM anamnesi_prima_infanzia WHERE paziente_id = %s", (pid,))
    if not r:
        return []
    d, quando, F = _json(r[0]), _data(r[1]), "Anamnesi prima infanzia"
    if not isinstance(d, dict):
        return []
    lista = lambda k: d.get(k) or []
    out = []

    def p(hpo, motivo):
        out.append(Proposta(hpo, F, quando, motivo))

    if d.get("neo_tono") == "Ipotonico":
        p("HP:0001252", "tono alla nascita «Ipotonico»")
    all_ = lista("all_presenti")
    for voce, hpo in (("Nessuna parola a 18 mesi", "HP:0000750"), ("Nessuna frase a 24 mesi", "HP:0000750"),
                      ("Regressione del linguaggio", "HP:0000750"),
                      ("Contatto oculare scarso", "HP:0000729"), ("Non risponde al nome", "HP:0000729"),
                      ("Movimenti ripetitivi", "HP:0031432"), ("Cadute molto frequenti", "HP:0002312")):
        if voce in all_:
            p(hpo, f"segnale di allerta «{voce}»")
    if d.get("com_occhi") == "Assente":
        p("HP:0000729", "contatto oculare «Assente»")
    reatt = lista("com_reattivita")
    for voce, hpo in (("Ipersensibilità tattile", "HP:5200061"), ("Ipersensibilità uditiva", "HP:5200060"),
                      ("Ricerca di stimoli sensoriali", "HP:4000079")):
        if voce in reatt:
            p(hpo, f"reattività sensoriale «{voce}»")
    if d.get("com_suoni") == "Esagerata":
        p("HP:5200060", "risposta ai suoni «Esagerata»")
    neo = lista("neo_difficolta")
    if "Difficoltà di deglutizione" in neo:
        p("HP:0002015", "«Difficoltà di deglutizione» nel neonato")
    if "Rifiuto seno / biberon" in neo or d.get("neo_suzione") in ("Debole", "Difficoltosa"):
        p("HP:0011968", "suzione debole/difficoltosa o rifiuto seno/biberon")
    if d.get("neo_sonno") in ("Difficoltà ad addormentarsi", "Risvegli frequenti"):
        p("HP:0002360", f"sonno nel neonato: «{d.get('neo_sonno')}»")
    if d.get("mot_cadute") == "Sì, frequenti":
        p("HP:0002312", "cadute frequenti")
    return out


def _sviluppo(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT dati, aggiornato_il FROM anamnesi_sviluppo WHERE paziente_id = %s", (pid,))
    if not r:
        return []
    d, quando, F = _json(r[0]), _data(r[1]), "Anamnesi dello sviluppo"
    if not isinstance(d, dict):
        return []
    out = []

    def p(hpo, motivo):
        out.append(Proposta(hpo, F, quando, motivo))

    if d.get("balbuzie") == "sì, attuale":
        p("HP:0025268", "balbuzie «sì, attuale»")
    if d.get("motricita_globale") == "impacciato, cadeva spesso":
        p("HP:0002312", "motricità globale «impacciato, cadeva spesso»")
    if d.get("motricita_globale") == "in ritardo":
        p("HP:0001270", "motricità globale «in ritardo»")
    if d.get("motricita_fine") in ("fatica", "evita queste attività"):
        p("HP:0007010", f"motricità fine «{d.get('motricita_fine')}»")
    if d.get("comprensibilita") in ("comprensibile solo ai familiari", "poco comprensibile"):
        p("HP:0000750", f"a 3-4 anni parlava in modo «{d.get('comprensibilita')}»")
    cert = d.get("certificazioni") or []
    if "ADHD" in cert:
        p("HP:0007018", "certificazione ADHD")
    if "DSA" in cert:
        p("HP:0001328", "certificazione DSA")
    if d.get("attenzione") == "si distrae facilmente":
        p("HP:0000736", "attenzione «si distrae facilmente»")
    if d.get("attenzione") == "agitato, impulsivo":
        p("HP:0000752", "comportamento «agitato, impulsivo»")
    if "respira a bocca aperta" in (d.get("respirazione") or []):
        p("HP:6000463", "«respira a bocca aperta»")
    sonno = d.get("sonno_qualita") or []
    if "digrigna i denti" in sonno:
        p("HP:0003763", "«digrigna i denti»")
    if any(x in sonno for x in ("fatica ad addormentarsi", "risvegli notturni")):
        p("HP:0002360", "sonno: " + ", ".join(x for x in sonno if x in ("fatica ad addormentarsi", "risvegli notturni")))
    return out


# ---------------------------------------------------------------- logopedia, DSA, NPS
def _logopedia(conn, pid) -> list[Proposta]:
    r = _riga(conn, "SELECT dati, data FROM logopedia_valutazioni WHERE paziente_id = %s "
                    "ORDER BY data DESC NULLS LAST, id DESC LIMIT 1", (pid,))
    if not r:
        return []
    d, quando, F = _json(r[0]), _data(r[1]), "Logopedia / SMOF"
    if not isinstance(d, dict):
        return []
    mf, fl = d.get("mf") or {}, d.get("fl") or {}
    out = []
    if mf.get("respirazione") == "Orale":
        out.append(Proposta("HP:6000463", F, quando, "respirazione «Orale»"))
    if mf.get("deglutizione") in ("Atipica", "Con interposizione linguale"):
        out.append(Proposta("HP:0100703", F, quando, f"deglutizione «{mf.get('deglutizione')}»"))
    if mf.get("tono_orofacciale") == "Ipotono":
        out.append(Proposta("HP:0030190", F, quando, "tono oro-facciale «Ipotono»"))
    if fl.get("presente") == "Sì":
        out.append(Proposta("HP:0025268", F, quando, "disfluenza presente «Sì»"))
    return out


def _ultimo_tipo(conn, tabella, pid, tipo):
    return _riga(conn, f"SELECT dati_json, data_valutazione FROM {tabella} WHERE paziente_id = %s AND tipo = %s "
                       "ORDER BY created_at DESC LIMIT 1", (pid, tipo))


def _dsa(conn, pid) -> list[Proposta]:
    out = []
    r = _ultimo_tipo(conn, "dsa_valutazioni", pid, "AC-MT-3")
    if r:
        clin = [x for x in (_json(r[0]).get("risultati") or []) if isinstance(x, dict) and x.get("livello") == "clin"]
        if clin:
            out.append(Proposta("HP:0002442", "DSA · AC-MT 3", _data(r[1]),
                                "prove ≤ 5° percentile: " + ", ".join(str(x.get("prova")) for x in clin[:4])))
    r = _ultimo_tipo(conn, "dsa_valutazioni", pid, "DDE-2")
    if r and "Lenta e inaccurata" in (_json(r[0]).get("profilo_lettura") or []):
        out.append(Proposta("HP:0010522", "DSA · DDE-2", _data(r[1]), "profilo di lettura «Lenta e inaccurata»"))
    return out


def _nps(conn, pid) -> list[Proposta]:
    out = []
    r = _ultimo_tipo(conn, "nps_valutazioni", pid, "WISC-IV")
    if r:
        qi = _num(_json(r[0]).get("qi_totale"))
        if qi and qi < 70:
            out.append(Proposta("HP:0001249", "NPS · WISC-IV", _data(r[1]), f"QI totale {qi:.0f}"))
    r = _ultimo_tipo(conn, "nps_valutazioni", pid, "K-SADS")
    if r:
        quando = _data(r[1])
        for diag in _json(r[0]).get("diagnosi_presenti") or []:
            low = str(diag).lower()
            if "adhd" in low:
                out.append(Proposta("HP:0007018", "NPS · K-SADS", quando, diag))
                hpo = "HP:0000736" if "inattenzione" in low else "HP:0000752"
                out.append(Proposta(hpo, "NPS · K-SADS", quando, diag))
            elif any(k in low for k in ("fobia", "panico", "agorafobia", "ansia")):
                out.append(Proposta("HP:0000739", "NPS · K-SADS", quando, diag))
            elif "autis" in low:
                out.append(Proposta("HP:0000729", "NPS · K-SADS", quando, diag))
    for tipo in ("CBCL-618", "CBCL-15"):
        r = _ultimo_tipo(conn, "nps_valutazioni", pid, tipo)
        if not r:
            continue
        j = _json(r[0])
        scale = j.get("scale_sindromiche") or j.get("scale") or {}
        for chiave, hpo, nome in (("attention", "HP:0000736", "attenzione"), ("anx_dep", "HP:0000739", "ansioso/depresso")):
            t = _num(scale.get(chiave)) if isinstance(scale, dict) else None
            if t and t >= 70:
                out.append(Proposta(hpo, f"NPS · {tipo}", _data(r[1]), f"scala {nome} T = {t:.0f}"))
    return out


# ---------------------------------------------------------------- raccolta
LETTORI = [_inpp, _visuo_percettiva, _oculistica, _anamnesi_visiva, _audiogramma,
           _prima_infanzia, _sviluppo, _logopedia, _dsa, _nps]


def raccogli_proposte(conn, paziente_id: int) -> dict[str, list[Proposta]]:
    """{hpo_id: [Proposta, ...]} con tutte le fonti che suggeriscono quel segno."""
    out: dict[str, list[Proposta]] = {}
    if conn is None:
        return out
    for lettore in LETTORI:
        try:
            for p in lettore(conn, int(paziente_id)):
                out.setdefault(p.hpo, []).append(p)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    return out
