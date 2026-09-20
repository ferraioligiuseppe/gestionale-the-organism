# -*- coding: utf-8 -*-
"""Visita oculistica / optometrica — Studio The Organism.

Tabella propria (oculistica_visite): nessuna sovrapposizione con
valutazioni_visive (PNEV Visiva).

╔══════════════════════════════════════════════════════════════════════╗
║  TRE COSE CAMBIATE RISPETTO ALLA PRIMA STESURA                       ║
║                                                                      ║
║  1. Il tipo di visita si sceglie in cima e comanda cosa vedi.        ║
║     Prima era un form unico da seicento righe, identico per una      ║
║     prima visita e per un controllo di cinque minuti: si scorreva    ║
║     tutto ogni volta. Ora un controllo mostra sei campi, una prima   ║
║     visita li mostra tutti, e «mostra tutte le sezioni» resta        ║
║     sempre a portata di mano — nessun campo e' mai irraggiungibile.  ║
║                                                                      ║
║  2. La parte optometrica esisteva a meta': c'erano cover test, PPC   ║
║     e stereopsi, mancavano accomodazione, vergenze, AC/A e           ║
║     dominanza. Se la scheda si chiama anche optometrica, quella      ║
║     parte va riempita. I valori attesi sono accanto al campo: le     ║
║     norme si consultano mentre si misura, non dopo.                  ║
║                                                                      ║
║  3. Il DDL girava a ogni render: un CREATE TABLE e trentacinque      ║
║     ALTER TABLE per ogni caricamento di pagina. Con produzione e     ║
║     staging sullo stesso Postgres e' la ricetta per lock e timeout.  ║
║     Ora gira una volta per processo, dietro un flag di modulo.       ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import datetime

import streamlit as st

AV_OPTIONS = [
    "NV - non vedente", "PL - percezione luce", "ML/HM - moto mano",
    "CF 30 cm", "CF 50 cm", "CF 1 m",
    "1/50", "1/20", "1/10", "2/10", "3/10", "4/10", "5/10", "6/10", "7/10",
    "8/10", "9/10", "10/10", "12/10", "14/10", "16/10",
]

METODI_REFRAZIONE = ["Autorefrattometro", "Schiascopia", "Cicloplegia", "Soggettiva pura", "Altro"]
TIPI_CORREZIONE = ["Nessuna", "Occhiali", "Lenti a contatto", "Occhiali + LAC"]
COVER_TEST_ESITI = ["Ortoforia", "Eteroforia (latente)", "Esoforia", "Exoforia",
                    "Esotropia", "Exotropia", "Ipertropia", "Ipotropia"]

DIREZIONE_FORIA = ["Orto", "Eso", "Exo", "Iper D", "Iper S"]
DOMINANZA = ["", "OD", "OS", "Alternante / non definita"]
METODI_DOMINANZA = ["", "Foro nel cartone (hole-in-card)", "Miles (triangolo con le mani)",
                    "Porta (pollice)", "Sighting con mirino", "Altro"]

# ── Tipo di visita: decide quali sezioni compaiono ────────────────────
TIPI_VISITA = ["Prima visita completa", "Controllo",
               "Solo optometrica", "Solo oculistica"]

SEZIONI_PER_TIPO = {
    "Prima visita completa": {"anamnesi", "av", "abituale", "ogg", "sogg", "prescrizione",
                              "cherato", "tono", "optometria", "strutturali", "obiettivo",
                              "economia"},
    # Un controllo e' poche cose: come vede oggi, cosa e' cambiato nella
    # refrazione, la pressione, e due righe di nota.
    "Controllo": {"av", "sogg", "prescrizione", "tono", "economia"},
    "Solo optometrica": {"anamnesi", "av", "abituale", "ogg", "sogg", "prescrizione",
                         "optometria", "economia"},
    "Solo oculistica": {"anamnesi", "av", "ogg", "cherato", "tono", "strutturali",
                        "obiettivo", "economia"},
}

_SCHEMA_PRONTO = False


# ══════════════════════════════════════════════════════════════════════
#  Utilita'
# ══════════════════════════════════════════════════════════════════════

def _fmt_data_it(iso_or_date):
    if not iso_or_date:
        return ""
    if isinstance(iso_or_date, datetime.date):
        return iso_or_date.strftime("%d/%m/%Y")
    try:
        return datetime.date.fromisoformat(str(iso_or_date)).strftime("%d/%m/%Y")
    except Exception:
        return str(iso_or_date)


def _parse_data_it(s, fallback=None):
    s = (s or "").strip()
    if not s:
        return fallback
    try:
        return datetime.datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return fallback


def _eta_paziente(paziente) -> int | None:
    """Serve per le norme di Hofstetter sull'ampiezza accomodativa."""
    if not isinstance(paziente, dict):
        return None
    dn = None
    for k in ("data_nascita", "Data_nascita", "DataNascita"):
        if paziente.get(k):
            dn = paziente[k]
            break
    if dn is None:
        return None
    try:
        if isinstance(dn, str):
            dn = datetime.date.fromisoformat(dn[:10])
        if hasattr(dn, "date") and not isinstance(dn, datetime.date):
            dn = dn.date()
        oggi = datetime.date.today()
        anni = oggi.year - dn.year - ((oggi.month, oggi.day) < (dn.month, dn.day))
        return anni if 0 <= anni <= 120 else None
    except Exception:
        return None


def _av_select(container, label, current, key):
    opts = AV_OPTIONS.copy()
    if current and current not in opts:
        opts = [current] + opts
    else:
        opts = [""] + opts
    idx = opts.index(current) if current in opts else 0
    return container.selectbox(label, opts, index=idx, key=key)


def _sel(container, label, opzioni, corrente, key):
    idx = opzioni.index(corrente) if corrente in opzioni else 0
    return container.selectbox(label, opzioni, index=idx, key=key)


def _cherato_mm_to_D(r_mm):
    return 337.5 / r_mm if r_mm else 0.0


def _cherato_D_to_mm(D):
    return 337.5 / D if D else 0.0


# ══════════════════════════════════════════════════════════════════════
#  Norme cliniche — il valore atteso accanto a quello misurato
# ══════════════════════════════════════════════════════════════════════

def _correzione_pio(cct_um, pio):
    """Regola pratica: ~0.5 mmHg / 10µm rispetto a 545µm di riferimento."""
    if not cct_um:
        return None, None, None
    delta = (545.0 - cct_um) * 0.05
    pio_corretta = (pio or 0) + delta
    if cct_um < 555:
        rischio = "Elevato — CCT <555µm: fattore di rischio indipendente (OHTS)"
    elif cct_um <= 588:
        rischio = "Intermedio — correlare con PIO, papilla e campo visivo"
    else:
        rischio = "Basso — cornea spessa, PIO misurata tende a sovrastimare"
    return round(delta, 1), round(pio_corretta, 1), rischio


def _valuta_ppc(rottura_cm, recupero_cm):
    """NPC: rottura normale ≤10 cm, recupero normale ≤15 cm."""
    esiti = []
    if rottura_cm:
        if rottura_cm <= 10:
            esiti.append(f"Rottura {rottura_cm:.1f} cm — nella norma (≤10 cm)")
        else:
            esiti.append(f"Rottura {rottura_cm:.1f} cm — RECEDUTA (norma ≤10 cm): "
                         "possibile insufficienza di convergenza")
    if recupero_cm:
        if recupero_cm <= 15:
            esiti.append(f"Recupero {recupero_cm:.1f} cm — nella norma (≤15 cm)")
        else:
            esiti.append(f"Recupero {recupero_cm:.1f} cm — RECEDUTO (norma ≤15 cm): "
                         "possibile insufficienza di convergenza")
    return " · ".join(esiti) if esiti else ""


def _hofstetter(eta):
    """Ampiezza accomodativa attesa per eta' (Hofstetter).
    Ritorna (minima, media) in diottrie."""
    if eta is None:
        return None, None
    return round(15.0 - 0.25 * eta, 2), round(18.5 - 0.30 * eta, 2)


def _valuta_accomodazione(amp_od, amp_os, eta):
    minima, media = _hofstetter(eta)
    if minima is None:
        return "Età del paziente non disponibile: la norma di Hofstetter non è calcolabile."
    parti = [f"Attesa per {eta} anni: minima {minima} D, media {media} D"]
    for occhio, val in (("OD", amp_od), ("OS", amp_os)):
        if not val:
            continue
        if val < minima:
            parti.append(f"{occhio} {val} D — SOTTO la minima: insufficienza accomodativa probabile")
        elif val < media:
            parti.append(f"{occhio} {val} D — sopra la minima ma sotto la media")
        else:
            parti.append(f"{occhio} {val} D — nella norma")
    return " · ".join(parti)


def _valuta_flessibilita(mono, bino):
    """Flipper ±2.00 D. Norme adulto: mono ≥11 cpm, bino ≥8 cpm."""
    parti = []
    if mono:
        parti.append(f"Monoculare {mono} cpm — " +
                     ("nella norma (≥11)" if mono >= 11 else "RIDOTTA (norma ≥11 cpm)"))
    if bino:
        parti.append(f"Binoculare {bino} cpm — " +
                     ("nella norma (≥8)" if bino >= 8 else "RIDOTTA (norma ≥8 cpm)"))
    return " · ".join(parti)


def _valuta_mem(mem_od, mem_os):
    """MEM atteso +0.25 / +0.75 D. Sotto = lag basso (spasmo),
    sopra = lag alto (ritardo accomodativo)."""
    parti = []
    for occhio, val in (("OD", mem_od), ("OS", mem_os)):
        if val is None:
            continue
        if val < 0.25:
            parti.append(f"{occhio} {val:+.2f} D — lag basso / eccesso accomodativo")
        elif val <= 0.75:
            parti.append(f"{occhio} {val:+.2f} D — nella norma (+0.25/+0.75)")
        else:
            parti.append(f"{occhio} {val:+.2f} D — lag alto: ritardo accomodativo")
    return " · ".join(parti)


def _foria_segno(direzione, valore):
    """Converte in valore con segno: eso positivo, exo negativo.
    E' la convenzione con cui si calcola l'AC/A."""
    if not valore or direzione in ("", "Orto"):
        return 0.0
    if direzione == "Eso":
        return float(valore)
    if direzione == "Exo":
        return -float(valore)
    return 0.0


def _valuta_forie(dir_lon, val_lon, dir_vic, val_vic):
    """Norme di Morgan: lontano 1 exo ±2 · vicino 3 exo ±3."""
    parti = []
    if dir_lon and dir_lon != "Orto":
        s = _foria_segno(dir_lon, val_lon)
        parti.append(f"Lontano {val_lon}Δ {dir_lon.lower()} — " +
                     ("nella norma (1 exo ±2)" if -3 <= s <= 1 else "fuori norma (attesa 1 exo ±2)"))
    if dir_vic and dir_vic != "Orto":
        s = _foria_segno(dir_vic, val_vic)
        parti.append(f"Vicino {val_vic}Δ {dir_vic.lower()} — " +
                     ("nella norma (3 exo ±3)" if -6 <= s <= 0 else "fuori norma (attesa 3 exo ±3)"))
    return " · ".join(parti)


def _aca_calcolato(dip_mm, dist_lavoro_cm, dir_lon, val_lon, dir_vic, val_vic):
    """AC/A calcolato = DIP(cm) + d(m) × (foria vicino − foria lontano),
    con eso positiva ed exo negativa. Norma 3–5 : 1."""
    if not dip_mm or not dist_lavoro_cm:
        return None, ""
    dip_cm = dip_mm / 10.0
    d_m = dist_lavoro_cm / 100.0
    aca = dip_cm + d_m * (_foria_segno(dir_vic, val_vic) - _foria_segno(dir_lon, val_lon))
    aca = round(aca, 1)
    if aca < 3:
        nota = "BASSO (norma 3–5:1) — insufficienza di convergenza da escludere"
    elif aca <= 5:
        nota = "nella norma (3–5:1)"
    else:
        nota = "ALTO (norma 3–5:1) — eccesso di convergenza da escludere"
    return aca, nota


# ══════════════════════════════════════════════════════════════════════
#  Schema
# ══════════════════════════════════════════════════════════════════════

_COLONNE_EXTRA = [
    ("sf_abit_od", "REAL"), ("cil_abit_od", "REAL"), ("ax_abit_od", "INT"), ("add_abit_od", "REAL"),
    ("sf_abit_os", "REAL"), ("cil_abit_os", "REAL"), ("ax_abit_os", "INT"), ("add_abit_os", "REAL"),
    ("metodo_ogg", "TEXT"),
    ("sf_fin_od", "REAL"), ("cil_fin_od", "REAL"), ("ax_fin_od", "INT"), ("add_fin_od", "REAL"),
    ("sf_fin_os", "REAL"), ("cil_fin_os", "REAL"), ("ax_fin_os", "INT"), ("add_fin_os", "REAL"),
    ("tipo_correzione_fin", "TEXT"), ("note_prescrizione", "TEXT"),
    ("cover_test_od", "TEXT"), ("cover_test_os", "TEXT"),
    ("fondo_od", "TEXT"), ("fondo_os", "TEXT"),
    ("campo_visivo_od", "TEXT"), ("campo_visivo_os", "TEXT"),
    ("oct_od", "TEXT"), ("oct_os", "TEXT"),
    ("ppc_rottura_cm", "REAL"), ("ppc_recupero_cm", "REAL"),
    ("an_motivo", "TEXT"), ("an_storia_oculare", "TEXT"), ("an_storia_sistemica", "TEXT"),
    ("an_familiarita", "TEXT"), ("an_farmaci", "TEXT"), ("an_allergie", "TEXT"),
    ("an_uso_attuale", "TEXT"), ("an_lavoro_hobby", "TEXT"), ("an_note", "TEXT"),
    # ── parte optometrica ──────────────────────────────────────────────
    ("acc_amp_od", "REAL"), ("acc_amp_os", "REAL"), ("acc_amp_metodo", "TEXT"),
    ("acc_flip_mono", "REAL"), ("acc_flip_bino", "REAL"), ("acc_flip_lente", "TEXT"),
    ("mem_od", "REAL"), ("mem_os", "REAL"),
    ("foria_lon_dir", "TEXT"), ("foria_lon_val", "REAL"),
    ("foria_vic_dir", "TEXT"), ("foria_vic_val", "REAL"),
    ("rf_bo_lon", "TEXT"), ("rf_bi_lon", "TEXT"),
    ("rf_bo_vic", "TEXT"), ("rf_bi_vic", "TEXT"),
    ("aca_dip_mm", "REAL"), ("aca_dist_cm", "REAL"),
    ("aca_calcolato", "REAL"), ("aca_gradiente", "REAL"),
    ("dominanza_oculare", "TEXT"), ("dominanza_metodo", "TEXT"),
    ("worth_lontano", "TEXT"), ("worth_vicino", "TEXT"),
    ("maddox_lontano", "TEXT"), ("maddox_vicino", "TEXT"),
    ("van_orden", "TEXT"),
    ("optom_note", "TEXT"),
]


def _ensure_table(conn):
    """CREATE + ALTER una volta per processo. Prima girava a ogni render:
    trentasei istruzioni DDL per ogni caricamento della pagina."""
    global _SCHEMA_PRONTO
    if _SCHEMA_PRONTO:
        return
    try:
        conn.rollback()
    except Exception:
        pass
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS oculistica_visite (
                id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                paziente_id BIGINT NOT NULL REFERENCES pazienti(id) ON DELETE CASCADE,
                data_visita DATE,
                tipo_visita TEXT,
                professionista TEXT,
                ac_nat_od TEXT, ac_nat_os TEXT, ac_nat_oo TEXT,
                ac_cor_od TEXT, ac_cor_os TEXT, ac_cor_oo TEXT,
                sf_ogg_od REAL, cil_ogg_od REAL, ax_ogg_od INT,
                sf_ogg_os REAL, cil_ogg_os REAL, ax_ogg_os INT,
                sf_sogg_od REAL, cil_sogg_od REAL, ax_sogg_od INT,
                sf_sogg_os REAL, cil_sogg_os REAL, ax_sogg_os INT,
                k1_od_mm REAL, k1_od_d REAL, k2_od_mm REAL, k2_od_d REAL,
                k1_os_mm REAL, k1_os_d REAL, k2_os_mm REAL, k2_os_d REAL,
                tono_od REAL, tono_os REAL,
                motilita TEXT, cover_test TEXT, stereopsi TEXT, ppc_cm REAL,
                ishihara TEXT, pachim_od REAL, pachim_os REAL,
                fondo TEXT, campo_visivo TEXT, oct TEXT, topo TEXT,
                cornea TEXT, camera_ant TEXT, cristallino TEXT,
                congiuntiva TEXT, iride_pupilla TEXT, vitreo TEXT,
                costo NUMERIC(10,2) DEFAULT 0, pagato BIGINT DEFAULT 0,
                note TEXT,
                creato_il TIMESTAMP DEFAULT now()
            )
        """)
        for col, tipo in _COLONNE_EXTRA:
            cur.execute(f"ALTER TABLE oculistica_visite ADD COLUMN IF NOT EXISTS {col} {tipo}")
        conn.commit()
        _SCHEMA_PRONTO = True
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


def _salva(conn, paz_id, d):
    cur = conn.cursor()
    try:
        cols = list(d.keys())
        ph = ",".join(["%s"] * len(cols))
        cur.execute(
            f"INSERT INTO oculistica_visite (paziente_id,{','.join(cols)}) VALUES (%s,{ph})",
            [paz_id] + list(d.values()))
        conn.commit()
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


def _aggiorna(conn, vid, d):
    cur = conn.cursor()
    try:
        set_clause = ",".join([f"{k}=%s" for k in d.keys()])
        cur.execute(f"UPDATE oculistica_visite SET {set_clause} WHERE id=%s",
                    list(d.values()) + [vid])
        conn.commit()
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


def _storico(conn, paz_id):
    cur = conn.cursor()
    try:
        cur.execute("""SELECT id, data_visita, tipo_visita, professionista,
                              ac_cor_od, ac_cor_os
                       FROM oculistica_visite WHERE paziente_id=%s
                       ORDER BY data_visita DESC, id DESC""", (paz_id,))
        return cur.fetchall()
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


def _carica_visita(conn, vid):
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM oculistica_visite WHERE id=%s", (vid,))
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row
        if hasattr(row, "keys"):
            return dict(row)
        cols = [c[0] for c in cur.description]
        return dict(zip(cols, row))
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


# ══════════════════════════════════════════════════════════════════════
#  Testo per la stampa
# ══════════════════════════════════════════════════════════════════════

def _testo_visita(d: dict, eta=None) -> str:
    def g(k, default=""):
        v = d.get(k, default)
        return v if v not in (None, "") else default

    _, pio_od, risk_od = _correzione_pio(g("pachim_od", 0) or 0, g("tono_od", 0) or 0)
    _, pio_os, risk_os = _correzione_pio(g("pachim_os", 0) or 0, g("tono_os", 0) or 0)

    blocchi = [
        f"Data: {_fmt_data_it(g('data_visita'))}    Tipo: {g('tipo_visita')}    "
        f"Professionista: {g('professionista')}",
        "",
        "ANAMNESI",
        f"- Motivo della visita: {g('an_motivo','—')}",
        f"- Storia oculare: {g('an_storia_oculare','—')}",
        f"- Storia sistemica/generale: {g('an_storia_sistemica','—')}",
        f"- Familiarità oculare: {g('an_familiarita','—')}",
        f"- Farmaci in uso: {g('an_farmaci','—')}",
        f"- Allergie: {g('an_allergie','—')}",
        f"- Uso attuale occhiali/LAC: {g('an_uso_attuale','—')}",
        f"- Lavoro/attività visive: {g('an_lavoro_hobby','—')}",
        f"- Altre note anamnestiche: {g('an_note','—')}",
        "",
        "ACUITÀ VISIVA",
        f"- Naturale: OD {g('ac_nat_od','—')} | OS {g('ac_nat_os','—')} | OO {g('ac_nat_oo','—')}",
        f"- Corretta: OD {g('ac_cor_od','—')} | OS {g('ac_cor_os','—')} | OO {g('ac_cor_oo','—')}",
        "",
        "CORREZIONE ABITUALE",
        f"- OD: {g('sf_abit_od',0)} ({g('cil_abit_od',0)} x {g('ax_abit_od',0)}°) Add. {g('add_abit_od',0)}",
        f"- OS: {g('sf_abit_os',0)} ({g('cil_abit_os',0)} x {g('ax_abit_os',0)}°) Add. {g('add_abit_os',0)}",
        "",
        f"REFRAZIONE OGGETTIVA — metodo: {g('metodo_ogg','—')}",
        f"- OD: {g('sf_ogg_od',0)} ({g('cil_ogg_od',0)} x {g('ax_ogg_od',0)}°)",
        f"- OS: {g('sf_ogg_os',0)} ({g('cil_ogg_os',0)} x {g('ax_ogg_os',0)}°)",
        "",
        "REFRAZIONE SOGGETTIVA",
        f"- OD: {g('sf_sogg_od',0)} ({g('cil_sogg_od',0)} x {g('ax_sogg_od',0)}°)",
        f"- OS: {g('sf_sogg_os',0)} ({g('cil_sogg_os',0)} x {g('ax_sogg_os',0)}°)",
        "",
        f"PRESCRIZIONE FINALE — {g('tipo_correzione_fin','—')}",
        f"- OD: {g('sf_fin_od',0)} ({g('cil_fin_od',0)} x {g('ax_fin_od',0)}°) Add. {g('add_fin_od',0)}",
        f"- OS: {g('sf_fin_os',0)} ({g('cil_fin_os',0)} x {g('ax_fin_os',0)}°) Add. {g('add_fin_os',0)}",
        f"Note prescrizione: {g('note_prescrizione','—')}",
        "",
        "ESAME OPTOMETRICO",
        f"- Ampiezza accomodativa ({g('acc_amp_metodo','—')}): "
        f"OD {g('acc_amp_od',0)} D | OS {g('acc_amp_os',0)} D",
        f"  {_valuta_accomodazione(g('acc_amp_od',0) or 0, g('acc_amp_os',0) or 0, eta) or '—'}",
        f"- Flessibilità accomodativa (flipper {g('acc_flip_lente','±2.00')}): "
        f"mono {g('acc_flip_mono',0)} cpm | bino {g('acc_flip_bino',0)} cpm",
        f"  {_valuta_flessibilita(g('acc_flip_mono',0) or 0, g('acc_flip_bino',0) or 0) or '—'}",
        f"- MEM / retinoscopia dinamica: OD {g('mem_od',0)} D | OS {g('mem_os',0)} D",
        f"  {_valuta_mem(g('mem_od'), g('mem_os')) or '—'}",
        f"- Forie: lontano {g('foria_lon_val',0)}Δ {g('foria_lon_dir','—')} · "
        f"vicino {g('foria_vic_val',0)}Δ {g('foria_vic_dir','—')}",
        f"  {_valuta_forie(g('foria_lon_dir',''), g('foria_lon_val',0) or 0, g('foria_vic_dir',''), g('foria_vic_val',0) or 0) or '—'}",
        f"- Riserve fusionali (annebbiamento/rottura/recupero):",
        f"  Lontano  BE {g('rf_bo_lon','—')}  ·  BI {g('rf_bi_lon','—')}",
        f"  Vicino   BE {g('rf_bo_vic','—')}  ·  BI {g('rf_bi_vic','—')}",
        f"- Rapporto AC/A: calcolato {g('aca_calcolato','—')} : 1 · "
        f"gradiente {g('aca_gradiente','—')} : 1  (norma 3–5:1)",
        f"- Dominanza oculare: {g('dominanza_oculare','—')} ({g('dominanza_metodo','—')})",
        f"- Worth: lontano {g('worth_lontano','—')} · vicino {g('worth_vicino','—')}",
        f"- Maddox: lontano {g('maddox_lontano','—')} · vicino {g('maddox_vicino','—')}",
        f"- Van Orden: {g('van_orden','—')}",
        f"- Note optometriche: {g('optom_note','—')}",
        "",
        "MOTILITÀ / COVER TEST / STEREOPSI / PPC",
        f"- Motilità: {g('motilita','—')}",
        f"- Cover test OD: {g('cover_test_od','—')}   Cover test OS: {g('cover_test_os','—')}",
        f"- Stereopsi: {g('stereopsi','—')}",
        f"- PPC rottura: {g('ppc_rottura_cm',0)} cm · recupero: {g('ppc_recupero_cm',0)} cm"
        f" ({_valuta_ppc(g('ppc_rottura_cm',0) or 0, g('ppc_recupero_cm',0) or 0) or 'n.d.'})",
        f"- Ishihara: {g('ishihara','—')}",
        "",
        "CHERATOMETRIA",
        f"- OD: K1 {g('k1_od_mm',0)}mm/{g('k1_od_d',0)}D  K2 {g('k2_od_mm',0)}mm/{g('k2_od_d',0)}D",
        f"- OS: K1 {g('k1_os_mm',0)}mm/{g('k1_os_d',0)}D  K2 {g('k2_os_mm',0)}mm/{g('k2_os_d',0)}D",
        "",
        "TONOMETRIA E SPESSORE CORNEALE (CCT)",
        f"- OD: {g('tono_od',0)} mmHg · CCT {g('pachim_od',0)}µm · "
        f"PIO corretta ≈ {pio_od if pio_od is not None else '—'} mmHg · Rischio: {risk_od or '—'}",
        f"- OS: {g('tono_os',0)} mmHg · CCT {g('pachim_os',0)}µm · "
        f"PIO corretta ≈ {pio_os if pio_os is not None else '—'} mmHg · Rischio: {risk_os or '—'}",
        "",
        "ESAMI STRUTTURALI/FUNZIONALI",
        f"- Fondo oculare: OD {g('fondo_od','—')} | OS {g('fondo_os','—')}",
        f"- Campo visivo: OD {g('campo_visivo_od','—')} | OS {g('campo_visivo_os','—')}",
        f"- OCT: OD {g('oct_od','—')} | OS {g('oct_os','—')}",
        f"- Topografia corneale: {g('topo','—')}",
        "",
        "ESAME OBIETTIVO",
        f"- Cornea: {g('cornea','—')}",
        f"- Camera anteriore: {g('camera_ant','—')}",
        f"- Cristallino: {g('cristallino','—')}",
        f"- Congiuntiva/Sclera: {g('congiuntiva','—')}",
        f"- Iride/Pupilla: {g('iride_pupilla','—')}",
        f"- Vitreo: {g('vitreo','—')}",
        "",
        "NOTE",
        g("note", "—"),
    ]
    return "\n".join(blocchi)


# ══════════════════════════════════════════════════════════════════════
#  Schermata
# ══════════════════════════════════════════════════════════════════════

def render_oculistica(conn, paz_id: int, paziente: dict = None) -> None:
    st.subheader("👁️ Visita oculistica / optometrica")
    try:
        _ensure_table(conn)
    except Exception as e:
        st.error(f"Impossibile preparare la tabella: {e}")
        return

    eta = _eta_paziente(paziente)

    _blocco_storico(conn, paz_id)
    _blocco_stampa(conn, paziente, eta)

    edit_id = st.session_state.get("ocul_edit_id")
    dv = _carica_visita(conn, edit_id) if edit_id else None
    if edit_id and not dv:
        st.session_state.pop("ocul_edit_id", None)
        edit_id = None
    dv = dv or {}

    if edit_id:
        if st.button("✖️ Annulla modifica / torna a nuova visita", key="ocul_cancel_edit"):
            st.session_state.pop("ocul_edit_id", None)
            st.rerun()

    # ── Tipo di visita: fuori dal form, perche' comanda cosa compare ──
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        tipo_visita = _sel(st, "Tipo di visita", TIPI_VISITA,
                           dv.get("tipo_visita") if dv.get("tipo_visita") in TIPI_VISITA
                           else "Prima visita completa",
                           "ocul_tipo_visita")
    with c2:
        st.write("")
        tutto = st.checkbox("Mostra tutte le sezioni", key="ocul_mostra_tutto",
                            help="Il tipo di visita nasconde le sezioni che di solito non "
                                 "servono. Nessun campo è mai irraggiungibile: da qui li vedi tutti.")

    attive = SEZIONI_PER_TIPO.get(tipo_visita, SEZIONI_PER_TIPO["Prima visita completa"])
    nascoste = sum(1 for s in SEZIONI_PER_TIPO["Prima visita completa"] if s not in attive)
    if nascoste and not tutto:
        st.caption(f"«{tipo_visita}»: {nascoste} sezioni non pertinenti sono nascoste.")

    def on(sezione):
        return tutto or sezione in attive

    # La cheratometria sta fuori dal form: mm e D si aggiornano a vicenda,
    # e dentro un form nessun widget puo' reagire prima dell'invio.
    if on("cherato"):
        _blocco_cheratometria(dv)

    _form_visita(conn, paz_id, dv, edit_id, tipo_visita, on, eta)

    st.markdown("---")
    _blocco_strumenti(conn, paz_id, paziente)


def _blocco_storico(conn, paz_id):
    try:
        rows = _storico(conn, paz_id)
    except Exception as e:
        st.error(f"Errore nella lettura dello storico: {e}")
        return
    if not rows:
        return
    st.markdown("#### Storico visite")
    for r in rows:
        if isinstance(r, dict):
            rid, data_v, tipo, prof = r.get("id"), r.get("data_visita"), r.get("tipo_visita"), r.get("professionista")
            od, os_ = r.get("ac_cor_od"), r.get("ac_cor_os")
        else:
            rid, data_v, tipo, prof, od, os_ = r
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.caption(f"📅 {_fmt_data_it(data_v)} · {tipo or 'Visita'} · {prof or ''} · "
                   f"OD {od or '—'} / OS {os_ or '—'}")
        if c2.button("✏️ Modifica", key=f"ocul_edit_{rid}"):
            st.session_state["ocul_edit_id"] = rid
            st.rerun()
        if c3.button("🖨️ Stampa", key=f"ocul_print_{rid}"):
            st.session_state["ocul_print_id"] = rid
            st.rerun()


def _blocco_stampa(conn, paziente, eta):
    print_id = st.session_state.get("ocul_print_id")
    if not print_id:
        return
    st.markdown("---")
    dv = _carica_visita(conn, print_id)
    if dv:
        try:
            from modules.pdf_templates import genera_carta_intestata
            try:
                from .timbri import carica_timbro, _username_corrente
                timbro = carica_timbro(conn, _username_corrente())
            except Exception:
                timbro = None
            cog = (paziente or {}).get("cognome") or (paziente or {}).get("Cognome") or ""
            nom = (paziente or {}).get("nome") or (paziente or {}).get("Nome") or ""
            pdf_bytes = genera_carta_intestata(
                professionista=dv.get("professionista", ""), titolo="Studio The Organism",
                paziente=f"{cog} {nom}", data=_fmt_data_it(dv.get("data_visita")),
                titolo_doc="Visita oculistica / optometrica",
                corpo_testo=_testo_visita(dv, eta), timbro_bytes=timbro)
            st.download_button("⬇️ Scarica PDF della visita", data=pdf_bytes,
                               file_name=f"visita_{cog}_{nom}_{dv.get('data_visita','')}.pdf",
                               mime="application/pdf", key="ocul_dl_print", type="primary")
        except Exception as e:
            st.error(f"Errore generazione PDF: {e}")
    if st.button("Chiudi anteprima stampa", key="ocul_close_print"):
        st.session_state.pop("ocul_print_id", None)
        st.rerun()


def _blocco_cheratometria(dv):
    CK = 337.5

    def sync(key_mm, key_D):
        def da_mm():
            v = st.session_state.get(key_mm, 0)
            if v and v > 0:
                st.session_state[key_D] = round(CK / v, 2)

        def da_D():
            v = st.session_state.get(key_D, 0)
            if v and v > 0:
                st.session_state[key_mm] = round(CK / v, 2)
        return da_mm, da_D

    for k, default in [("ocul_k1_od_mm", 7.80), ("ocul_k1_od_d", round(CK / 7.80, 2)),
                       ("ocul_k2_od_mm", 7.80), ("ocul_k2_od_d", round(CK / 7.80, 2)),
                       ("ocul_k1_os_mm", 7.80), ("ocul_k1_os_d", round(CK / 7.80, 2)),
                       ("ocul_k2_os_mm", 7.80), ("ocul_k2_os_d", round(CK / 7.80, 2))]:
        if k not in st.session_state:
            raw = dv.get(k.replace("ocul_", ""))
            st.session_state[k] = float(raw) if raw is not None else default

    @st.fragment
    def _fragment():
        st.markdown("**Cheratometria** — mm e diottrie si aggiornano a vicenda")
        f1 = sync("ocul_k1_od_mm", "ocul_k1_od_d")
        f2 = sync("ocul_k2_od_mm", "ocul_k2_od_d")
        f3 = sync("ocul_k1_os_mm", "ocul_k1_os_d")
        f4 = sync("ocul_k2_os_mm", "ocul_k2_os_d")
        a, b, c, d = st.columns(4)
        a.number_input("OD K1 (mm)", 3.5, 9.5, step=0.01, format="%.2f",
                       key="ocul_k1_od_mm", on_change=f1[0])
        b.number_input("OD K1 (D)", 20.0, 90.0, step=0.25, format="%.2f",
                       key="ocul_k1_od_d", on_change=f1[1])
        c.number_input("OD K2 (mm)", 3.5, 9.5, step=0.01, format="%.2f",
                       key="ocul_k2_od_mm", on_change=f2[0])
        d.number_input("OD K2 (D)", 20.0, 90.0, step=0.25, format="%.2f",
                       key="ocul_k2_od_d", on_change=f2[1])
        e, f, g, h = st.columns(4)
        e.number_input("OS K1 (mm)", 3.5, 9.5, step=0.01, format="%.2f",
                       key="ocul_k1_os_mm", on_change=f3[0])
        f.number_input("OS K1 (D)", 20.0, 90.0, step=0.25, format="%.2f",
                       key="ocul_k1_os_d", on_change=f3[1])
        g.number_input("OS K2 (mm)", 3.5, 9.5, step=0.01, format="%.2f",
                       key="ocul_k2_os_mm", on_change=f4[0])
        h.number_input("OS K2 (D)", 20.0, 90.0, step=0.25, format="%.2f",
                       key="ocul_k2_os_d", on_change=f4[1])

    _fragment()


def _form_visita(conn, paz_id, dv, edit_id, tipo_visita, on, eta):
    """Un solo form. I valori non mostrati restano quelli precedenti
    (in modifica) o i default (in inserimento): nascondere una sezione
    non cancella mai quello che c'e' gia' dentro."""

    def num(k, d=0.0):
        try:
            return float(dv.get(k) if dv.get(k) is not None else d)
        except Exception:
            return d

    def ent(k, d=0):
        try:
            return int(dv.get(k) if dv.get(k) is not None else d)
        except Exception:
            return d

    def txt(k):
        return dv.get(k) or ""

    v = {}
    form_key = f"ocul_edit_{edit_id}" if edit_id else f"ocul_nuova_{paz_id}"

    with st.form(form_key):
        st.markdown(f"**{'Modifica' if edit_id else 'Nuova'} — {tipo_visita.lower()}**")
        c1, c2 = st.columns(2)
        data_str = c1.text_input("Data visita (gg/mm/aaaa)",
                                 _fmt_data_it(dv.get("data_visita"))
                                 or datetime.date.today().strftime("%d/%m/%Y"))
        prof = c2.text_input("Professionista", txt("professionista"),
                             help="Chi ha eseguito la visita. Compilalo anche quando la "
                                  "scheda la riempie un oculista esterno.")

        # ── Anamnesi ──────────────────────────────────────────────────
        if on("anamnesi"):
            st.markdown("##### Anamnesi")
            v["an_motivo"] = st.text_area("Motivo della visita", txt("an_motivo"), height=68)
            c1, c2 = st.columns(2)
            v["an_storia_oculare"] = c1.text_area(
                "Storia oculare (traumi, interventi, patologie)", txt("an_storia_oculare"), height=68)
            v["an_storia_sistemica"] = c2.text_area(
                "Storia sistemica (diabete, ipertensione…)", txt("an_storia_sistemica"), height=68)
            c1, c2 = st.columns(2)
            v["an_familiarita"] = c1.text_area(
                "Familiarità oculare (glaucoma, maculopatia, strabismo)", txt("an_familiarita"), height=68)
            v["an_farmaci"] = c2.text_area("Farmaci in uso", txt("an_farmaci"), height=68)
            c1, c2 = st.columns(2)
            v["an_allergie"] = c1.text_input("Allergie", txt("an_allergie"))
            uso = ["Nessuno", "Occhiali", "Lenti a contatto", "Occhiali + LAC"]
            v["an_uso_attuale"] = _sel(c2, "Uso attuale", uso, txt("an_uso_attuale"), "ocul_an_uso")
            v["an_lavoro_hobby"] = st.text_input(
                "Lavoro / attività visive (video, guida, sport, lettura prolungata)",
                txt("an_lavoro_hobby"))
            v["an_note"] = st.text_area("Altre note anamnestiche", txt("an_note"), height=68)

        # ── Acuita' visiva ────────────────────────────────────────────
        if on("av"):
            st.markdown("##### Acuità visiva")
            c1, c2, c3 = st.columns(3)
            v["ac_nat_od"] = _av_select(c1, "OD naturale", txt("ac_nat_od"), "ocul_nat_od")
            v["ac_nat_os"] = _av_select(c2, "OS naturale", txt("ac_nat_os"), "ocul_nat_os")
            v["ac_nat_oo"] = _av_select(c3, "OO naturale", txt("ac_nat_oo"), "ocul_nat_oo")
            c1, c2, c3 = st.columns(3)
            v["ac_cor_od"] = _av_select(c1, "OD corretta", txt("ac_cor_od"), "ocul_cor_od")
            v["ac_cor_os"] = _av_select(c2, "OS corretta", txt("ac_cor_os"), "ocul_cor_os")
            v["ac_cor_oo"] = _av_select(c3, "OO corretta", txt("ac_cor_oo"), "ocul_cor_oo")

        # ── Correzione abituale ───────────────────────────────────────
        if on("abituale"):
            st.markdown("##### Correzione abituale — quello che porta già")
            c1, c2, c3, c4 = st.columns(4)
            v["sf_abit_od"] = c1.number_input("OD SF (D)", -30.0, 30.0, num("sf_abit_od"), 0.25, key="o_sfa_od")
            v["cil_abit_od"] = c2.number_input("OD CIL (D)", -10.0, 10.0, num("cil_abit_od"), 0.25, key="o_cia_od")
            v["ax_abit_od"] = c3.number_input("OD AX (°)", 0, 180, ent("ax_abit_od"), 1, key="o_axa_od")
            v["add_abit_od"] = c4.number_input("OD Add. (D)", 0.0, 6.0, num("add_abit_od"), 0.25, key="o_ada_od")
            c1, c2, c3, c4 = st.columns(4)
            v["sf_abit_os"] = c1.number_input("OS SF (D)", -30.0, 30.0, num("sf_abit_os"), 0.25, key="o_sfa_os")
            v["cil_abit_os"] = c2.number_input("OS CIL (D)", -10.0, 10.0, num("cil_abit_os"), 0.25, key="o_cia_os")
            v["ax_abit_os"] = c3.number_input("OS AX (°)", 0, 180, ent("ax_abit_os"), 1, key="o_axa_os")
            v["add_abit_os"] = c4.number_input("OS Add. (D)", 0.0, 6.0, num("add_abit_os"), 0.25, key="o_ada_os")

        # ── Refrazione oggettiva ──────────────────────────────────────
        if on("ogg"):
            st.markdown("##### Refrazione oggettiva")
            prec = [m.strip() for m in (txt("metodo_ogg")).split(",") if m.strip()]
            metodi = st.multiselect("Metodo/i usati", METODI_REFRAZIONE,
                                    default=[m for m in prec if m in METODI_REFRAZIONE],
                                    key="ocul_metodo_ogg")
            v["metodo_ogg"] = ", ".join(metodi)
            c1, c2, c3 = st.columns(3)
            v["sf_ogg_od"] = c1.number_input("OD SF (D)", -30.0, 30.0, num("sf_ogg_od"), 0.25, key="o_sfo_od")
            v["cil_ogg_od"] = c2.number_input("OD CIL (D)", -10.0, 10.0, num("cil_ogg_od"), 0.25, key="o_cio_od")
            v["ax_ogg_od"] = c3.number_input("OD AX (°)", 0, 180, ent("ax_ogg_od"), 1, key="o_axo_od")
            c1, c2, c3 = st.columns(3)
            v["sf_ogg_os"] = c1.number_input("OS SF (D)", -30.0, 30.0, num("sf_ogg_os"), 0.25, key="o_sfo_os")
            v["cil_ogg_os"] = c2.number_input("OS CIL (D)", -10.0, 10.0, num("cil_ogg_os"), 0.25, key="o_cio_os")
            v["ax_ogg_os"] = c3.number_input("OS AX (°)", 0, 180, ent("ax_ogg_os"), 1, key="o_axo_os")

        # ── Refrazione soggettiva ─────────────────────────────────────
        if on("sogg"):
            st.markdown("##### Refrazione soggettiva")
            c1, c2, c3 = st.columns(3)
            v["sf_sogg_od"] = c1.number_input("OD SF (D)", -30.0, 30.0, num("sf_sogg_od"), 0.25, key="o_sfs_od")
            v["cil_sogg_od"] = c2.number_input("OD CIL (D)", -10.0, 10.0, num("cil_sogg_od"), 0.25, key="o_cis_od")
            v["ax_sogg_od"] = c3.number_input("OD AX (°)", 0, 180, ent("ax_sogg_od"), 1, key="o_axs_od")
            c1, c2, c3 = st.columns(3)
            v["sf_sogg_os"] = c1.number_input("OS SF (D)", -30.0, 30.0, num("sf_sogg_os"), 0.25, key="o_sfs_os")
            v["cil_sogg_os"] = c2.number_input("OS CIL (D)", -10.0, 10.0, num("cil_sogg_os"), 0.25, key="o_cis_os")
            v["ax_sogg_os"] = c3.number_input("OS AX (°)", 0, 180, ent("ax_sogg_os"), 1, key="o_axs_os")

        # ── Prescrizione ──────────────────────────────────────────────
        if on("prescrizione"):
            st.markdown("##### Prescrizione finale")
            if st.form_submit_button("📋 Copia soggettiva → prescrizione finale"):
                for a, b in (("o_sfs_od", "o_sff_od"), ("o_cis_od", "o_cif_od"),
                             ("o_axs_od", "o_axf_od"), ("o_sfs_os", "o_sff_os"),
                             ("o_cis_os", "o_cif_os"), ("o_axs_os", "o_axf_os")):
                    if a in st.session_state:
                        st.session_state[b] = st.session_state[a]
                st.rerun()
            v["tipo_correzione_fin"] = _sel(st, "Tipo correzione prescritta", TIPI_CORREZIONE,
                                            txt("tipo_correzione_fin"), "ocul_tipo_corr_fin")
            c1, c2, c3, c4 = st.columns(4)
            v["sf_fin_od"] = c1.number_input("OD SF (D)", -30.0, 30.0, num("sf_fin_od"), 0.25, key="o_sff_od")
            v["cil_fin_od"] = c2.number_input("OD CIL (D)", -10.0, 10.0, num("cil_fin_od"), 0.25, key="o_cif_od")
            v["ax_fin_od"] = c3.number_input("OD AX (°)", 0, 180, ent("ax_fin_od"), 1, key="o_axf_od")
            v["add_fin_od"] = c4.number_input("OD Add. (D)", 0.0, 6.0, num("add_fin_od"), 0.25, key="o_adf_od")
            c1, c2, c3, c4 = st.columns(4)
            v["sf_fin_os"] = c1.number_input("OS SF (D)", -30.0, 30.0, num("sf_fin_os"), 0.25, key="o_sff_os")
            v["cil_fin_os"] = c2.number_input("OS CIL (D)", -10.0, 10.0, num("cil_fin_os"), 0.25, key="o_cif_os")
            v["ax_fin_os"] = c3.number_input("OS AX (°)", 0, 180, ent("ax_fin_os"), 1, key="o_axf_os")
            v["add_fin_os"] = c4.number_input("OS Add. (D)", 0.0, 6.0, num("add_fin_os"), 0.25, key="o_adf_os")
            v["note_prescrizione"] = st.text_input("Note prescrizione (add. vicino, prismi…)",
                                                   txt("note_prescrizione"))

        # ── Optometria ────────────────────────────────────────────────
        if on("optometria"):
            v.update(_sezione_optometria(dv, num, ent, txt, eta))

        # ── Tonometria ────────────────────────────────────────────────
        if on("tono"):
            st.markdown("##### Tonometria e spessore corneale")
            c1, c2 = st.columns(2)
            v["tono_od"] = c1.number_input("OD tonometria (mmHg)", 0.0, 60.0, num("tono_od", 15.0), 0.5, key="o_tono_od")
            v["pachim_od"] = c1.number_input("OD CCT (µm)", 400.0, 700.0, num("pachim_od", 540.0), 1.0, key="o_pac_od")
            v["tono_os"] = c2.number_input("OS tonometria (mmHg)", 0.0, 60.0, num("tono_os", 15.0), 0.5, key="o_tono_os")
            v["pachim_os"] = c2.number_input("OS CCT (µm)", 400.0, 700.0, num("pachim_os", 540.0), 1.0, key="o_pac_os")
            _, corr_od, risk_od = _correzione_pio(v["pachim_od"], v["tono_od"])
            _, corr_os, risk_os = _correzione_pio(v["pachim_os"], v["tono_os"])
            if corr_od is not None:
                st.caption(f"📐 PIO corretta OD ≈ {corr_od} mmHg — {risk_od}")
            if corr_os is not None:
                st.caption(f"📐 PIO corretta OS ≈ {corr_os} mmHg — {risk_os}")

        # ── Esami strutturali ─────────────────────────────────────────
        if on("strutturali"):
            st.markdown("##### Esami strutturali e funzionali")
            c1, c2 = st.columns(2)
            v["fondo_od"] = c1.text_area("Fondo oculare OD", txt("fondo_od"), height=68)
            v["fondo_os"] = c2.text_area("Fondo oculare OS", txt("fondo_os"), height=68)
            c1, c2 = st.columns(2)
            v["campo_visivo_od"] = c1.text_area("Campo visivo OD", txt("campo_visivo_od"), height=68)
            v["campo_visivo_os"] = c2.text_area("Campo visivo OS", txt("campo_visivo_os"), height=68)
            c1, c2 = st.columns(2)
            v["oct_od"] = c1.text_area("OCT OD", txt("oct_od"), height=68)
            v["oct_os"] = c2.text_area("OCT OS", txt("oct_os"), height=68)
            v["topo"] = st.text_area("Topografia corneale", txt("topo"), height=68)

        # ── Esame obiettivo ───────────────────────────────────────────
        if on("obiettivo"):
            st.markdown("##### Esame obiettivo")
            c1, c2 = st.columns(2)
            v["cornea"] = c1.text_area("Cornea", txt("cornea"), height=68)
            v["camera_ant"] = c2.text_area("Camera anteriore", txt("camera_ant"), height=68)
            c1, c2 = st.columns(2)
            v["cristallino"] = c1.text_area("Cristallino", txt("cristallino"), height=68)
            v["congiuntiva"] = c2.text_area("Congiuntiva / Sclera", txt("congiuntiva"), height=68)
            c1, c2 = st.columns(2)
            v["iride_pupilla"] = c1.text_area("Iride / Pupilla", txt("iride_pupilla"), height=68)
            v["vitreo"] = c2.text_area("Vitreo", txt("vitreo"), height=68)
            st.markdown("**Motilità, cover test, stereopsi, PPC**")
            v["motilita"] = st.text_input("Motilità oculare", txt("motilita"))
            c1, c2 = st.columns(2)
            v["cover_test_od"] = _sel(c1, "Cover test OD", [""] + COVER_TEST_ESITI,
                                      txt("cover_test_od"), "ocul_cover_od")
            v["cover_test_os"] = _sel(c2, "Cover test OS", [""] + COVER_TEST_ESITI,
                                      txt("cover_test_os"), "ocul_cover_os")
            v["stereopsi"] = st.text_input("Stereopsi", txt("stereopsi"))
            c1, c2 = st.columns(2)
            v["ppc_rottura_cm"] = c1.number_input("PPC rottura (cm)", 0.0, 30.0,
                                                  num("ppc_rottura_cm", 6.0), 0.5, key="o_ppc_r")
            v["ppc_recupero_cm"] = c2.number_input("PPC recupero (cm)", 0.0, 30.0,
                                                   num("ppc_recupero_cm", 10.0), 0.5, key="o_ppc_rec")
            esito = _valuta_ppc(v["ppc_rottura_cm"], v["ppc_recupero_cm"])
            if esito:
                st.caption(f"📐 {esito}")
            v["ishihara"] = st.text_input("Ishihara (esito)", txt("ishihara"))

        # ── Economia e note ───────────────────────────────────────────
        if on("economia"):
            st.markdown("##### Costo e note")
            c1, c2 = st.columns(2)
            v["costo"] = c1.number_input("Costo visita €", min_value=0.0, step=5.0,
                                         value=num("costo"), key="ocul_costo")
            pagato = c2.checkbox("Pagato", value=bool(dv.get("pagato")), key="ocul_pagato")
            v["pagato"] = 1 if pagato else 0
            v["note"] = st.text_area("Note cliniche", txt("note"), height=70)

        salva = st.form_submit_button(
            "💾 Salva modifiche" if edit_id else "💾 Salva visita",
            type="primary", use_container_width=True)

    if not salva:
        return

    v["data_visita"] = _parse_data_it(data_str, datetime.date.today()).isoformat()
    v["tipo_visita"] = tipo_visita
    v["professionista"] = prof
    if on("cherato"):
        for k in ("k1_od_mm", "k1_od_d", "k2_od_mm", "k2_od_d",
                  "k1_os_mm", "k1_os_d", "k2_os_mm", "k2_os_d"):
            v[k] = st.session_state.get(f"ocul_{k}")
    for k in ("ax_abit_od", "ax_abit_os", "ax_ogg_od", "ax_ogg_os",
              "ax_sogg_od", "ax_sogg_os", "ax_fin_od", "ax_fin_os"):
        if k in v:
            v[k] = int(v[k])

    try:
        if edit_id:
            _aggiorna(conn, edit_id, v)
            st.success("Visita aggiornata.")
            st.session_state.pop("ocul_edit_id", None)
        else:
            _salva(conn, paz_id, v)
            st.success("Visita salvata.")
        st.rerun()
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")


def _sezione_optometria(dv, num, ent, txt, eta):
    """Accomodazione, vergenze, AC/A, dominanza. I valori attesi stanno
    accanto al campo: le norme servono mentre misuri, non dopo."""
    v = {}
    st.markdown("##### Esame optometrico")

    minima, media = _hofstetter(eta)
    if minima is not None:
        st.caption(f"Paziente di {eta} anni · ampiezza accomodativa attesa (Hofstetter): "
                   f"minima {minima} D, media {media} D")

    st.markdown("**Accomodazione**")
    c1, c2, c3 = st.columns(3)
    v["acc_amp_od"] = c1.number_input("Ampiezza OD (D)", 0.0, 25.0, num("acc_amp_od"), 0.25, key="o_amp_od")
    v["acc_amp_os"] = c2.number_input("Ampiezza OS (D)", 0.0, 25.0, num("acc_amp_os"), 0.25, key="o_amp_os")
    v["acc_amp_metodo"] = _sel(c3, "Metodo", ["", "Push-up (Donders)", "Push-down", "Lenti negative"],
                               txt("acc_amp_metodo"), "o_amp_met")
    esito = _valuta_accomodazione(v["acc_amp_od"], v["acc_amp_os"], eta)
    if esito:
        st.caption(f"📐 {esito}")

    c1, c2, c3 = st.columns(3)
    v["acc_flip_mono"] = c1.number_input("Flessibilità monoculare (cpm)", 0.0, 30.0,
                                         num("acc_flip_mono"), 0.5, key="o_flip_mono")
    v["acc_flip_bino"] = c2.number_input("Flessibilità binoculare (cpm)", 0.0, 30.0,
                                         num("acc_flip_bino"), 0.5, key="o_flip_bino")
    v["acc_flip_lente"] = c3.text_input("Flipper usato", txt("acc_flip_lente") or "±2.00",
                                        key="o_flip_lente")
    esito = _valuta_flessibilita(v["acc_flip_mono"], v["acc_flip_bino"])
    if esito:
        st.caption(f"📐 {esito}")

    c1, c2 = st.columns(2)
    v["mem_od"] = c1.number_input("MEM / retinoscopia dinamica OD (D)", -2.0, 3.0,
                                  num("mem_od", 0.50), 0.25, key="o_mem_od")
    v["mem_os"] = c2.number_input("MEM / retinoscopia dinamica OS (D)", -2.0, 3.0,
                                  num("mem_os", 0.50), 0.25, key="o_mem_os")
    esito = _valuta_mem(v["mem_od"], v["mem_os"])
    if esito:
        st.caption(f"📐 {esito}")

    st.markdown("**Forie** — norme di Morgan: lontano 1 exo ±2 · vicino 3 exo ±3")
    c1, c2, c3, c4 = st.columns(4)
    v["foria_lon_dir"] = _sel(c1, "Lontano", DIREZIONE_FORIA, txt("foria_lon_dir"), "o_for_ld")
    v["foria_lon_val"] = c2.number_input("Δ lontano", 0.0, 60.0, num("foria_lon_val"), 0.5, key="o_for_lv")
    v["foria_vic_dir"] = _sel(c3, "Vicino", DIREZIONE_FORIA, txt("foria_vic_dir"), "o_for_vd")
    v["foria_vic_val"] = c4.number_input("Δ vicino", 0.0, 60.0, num("foria_vic_val"), 0.5, key="o_for_vv")
    esito = _valuta_forie(v["foria_lon_dir"], v["foria_lon_val"],
                          v["foria_vic_dir"], v["foria_vic_val"])
    if esito:
        st.caption(f"📐 {esito}")

    st.markdown("**Riserve fusionali** — scrivi annebbiamento / rottura / recupero, es. `12/18/10`")
    c1, c2 = st.columns(2)
    v["rf_bo_lon"] = c1.text_input("Base esterna, lontano", txt("rf_bo_lon"), key="o_rf_bol")
    v["rf_bi_lon"] = c2.text_input("Base interna, lontano", txt("rf_bi_lon"), key="o_rf_bil")
    c1, c2 = st.columns(2)
    v["rf_bo_vic"] = c1.text_input("Base esterna, vicino", txt("rf_bo_vic"), key="o_rf_bov")
    v["rf_bi_vic"] = c2.text_input("Base interna, vicino", txt("rf_bi_vic"), key="o_rf_biv")

    st.markdown("**Rapporto AC/A** — norma 3–5 : 1")
    c1, c2, c3 = st.columns(3)
    v["aca_dip_mm"] = c1.number_input("Distanza interpupillare (mm)", 0.0, 90.0,
                                      num("aca_dip_mm", 60.0), 0.5, key="o_aca_dip")
    v["aca_dist_cm"] = c2.number_input("Distanza di lavoro (cm)", 10.0, 100.0,
                                       num("aca_dist_cm", 40.0), 1.0, key="o_aca_dist")
    v["aca_gradiente"] = c3.number_input("AC/A a gradiente (misurato)", 0.0, 20.0,
                                         num("aca_gradiente"), 0.1, key="o_aca_grad")
    aca, nota = _aca_calcolato(v["aca_dip_mm"], v["aca_dist_cm"],
                               v["foria_lon_dir"], v["foria_lon_val"],
                               v["foria_vic_dir"], v["foria_vic_val"])
    v["aca_calcolato"] = aca
    if aca is not None:
        st.caption(f"📐 AC/A calcolato ≈ {aca} : 1 — {nota}")

    st.markdown("**Dominanza, Worth, Maddox, Van Orden**")
    c1, c2 = st.columns(2)
    v["dominanza_oculare"] = _sel(c1, "Dominanza oculare", DOMINANZA,
                                  txt("dominanza_oculare"), "o_dom")
    v["dominanza_metodo"] = _sel(c2, "Metodo", METODI_DOMINANZA,
                                 txt("dominanza_metodo"), "o_dom_met")
    c1, c2 = st.columns(2)
    v["worth_lontano"] = c1.text_input("Worth / filtro rosso — lontano", txt("worth_lontano"), key="o_worth_l")
    v["worth_vicino"] = c2.text_input("Worth / filtro rosso — vicino", txt("worth_vicino"), key="o_worth_v")
    c1, c2 = st.columns(2)
    v["maddox_lontano"] = c1.text_input("Maddox — lontano", txt("maddox_lontano"), key="o_mad_l")
    v["maddox_vicino"] = c2.text_input("Maddox — vicino", txt("maddox_vicino"), key="o_mad_v")
    v["van_orden"] = st.text_area("Van Orden / mappatura", txt("van_orden"), height=68, key="o_van")
    v["optom_note"] = st.text_area("Note optometriche", txt("optom_note"), height=68, key="o_optnote")
    return v


def _blocco_strumenti(conn, paz_id, paziente):
    with st.expander("📸 Stima refrazione rapida (Photoref AI)"):
        try:
            from .photoref_ai.ui_photoref import render_photoref
            render_photoref(conn, paz_id, paziente)
        except Exception as e:
            st.error(f"Photoref AI non disponibile: {e}")

    with st.expander("📊 Calcolatore PIO / CCT"):
        st.caption("Regola pratica: ~0,5 mmHg ogni 10µm di scostamento da 545µm. "
                   "Positivo = PIO vera più alta (cornea sottile).")
        c1, c2 = st.columns(2)
        with c1:
            pio = st.number_input("PIO misurata OD", 0.0, 60.0, 15.0, 0.5, key="ocul_calc_pio_od")
            cct = st.number_input("CCT OD (µm)", 400.0, 700.0, 540.0, 1.0, key="ocul_calc_cct_od")
            delta, corr, rischio = _correzione_pio(cct, pio)
            if delta is not None:
                st.info(f"Correzione: {delta:+.1f} mmHg → PIO ≈ {corr:.1f} mmHg\n\n{rischio}")
        with c2:
            pio2 = st.number_input("PIO misurata OS", 0.0, 60.0, 15.0, 0.5, key="ocul_calc_pio_os")
            cct2 = st.number_input("CCT OS (µm)", 400.0, 700.0, 540.0, 1.0, key="ocul_calc_cct_os")
            delta2, corr2, rischio2 = _correzione_pio(cct2, pio2)
            if delta2 is not None:
                st.info(f"Correzione: {delta2:+.1f} mmHg → PIO ≈ {corr2:.1f} mmHg\n\n{rischio2}")

    with st.expander("🧮 Cheratometria rapida (mm ⇄ diottrie)"):
        modo = st.radio("Conversione", ["mm → diottrie", "diottrie → mm"],
                        key="ocul_cherato_modo", horizontal=True)
        if modo == "mm → diottrie":
            r = st.number_input("Raggio corneale (mm)", 6.0, 9.5, 7.80, 0.01, key="ocul_cherato_r")
            if st.button("Calcola potere (D)", key="ocul_btn_cherato1"):
                st.success(f"Potere corneale ≈ {_cherato_mm_to_D(r):.2f} D")
        else:
            D = st.number_input("Potere corneale (D)", 35.0, 50.0, 43.0, 0.25, key="ocul_cherato_D")
            if st.button("Calcola raggio (mm)", key="ocul_btn_cherato2"):
                st.success(f"Raggio corneale ≈ {_cherato_D_to_mm(D):.2f} mm")
