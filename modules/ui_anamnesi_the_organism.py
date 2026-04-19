# -*- coding: utf-8 -*-
"""
Scheda Anamnesi Neuropsicologica - The Organism
9 sezioni: gravidanza, parto, neonatale, alimentazione,
sviluppo motorio (Teitelbaum), sensoriale, segnali allerta,
contesto familiare, motivo invio.
"""
from __future__ import annotations
import json
import datetime
import streamlit as st


# ══════════════════════════════════════════════════════════════════════
#  UTILITY
# ══════════════════════════════════════════════════════════════════════

def _salva(conn, paz_id: int, dati: dict) -> None:
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM anamnesi WHERE paziente_id=%s "
            "ORDER BY data_anamnesi DESC, id DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        dump = json.dumps(dati, ensure_ascii=False, default=str)

        if row:
            an_id = int(row["id"] if isinstance(row, dict) else row[0])
            cur.execute(
                "UPDATE anamnesi SET pnev_json = pnev_json || %s::jsonb "
                "WHERE id = %s",
                (dump, an_id)
            )
        else:
            cur.execute(
                "INSERT INTO anamnesi "
                "(paziente_id, data_anamnesi, motivo, pnev_json) "
                "VALUES (%s, %s, %s, %s::jsonb)",
                (paz_id, datetime.date.today().isoformat(),
                 "Anamnesi The Organism", dump)
            )
        conn.commit()
        st.success("Salvato.")
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore: {e}")


def _carica(conn, paz_id: int) -> dict:
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT pnev_json FROM anamnesi WHERE paziente_id=%s "
            "ORDER BY data_anamnesi DESC, id DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if not row:
            return {}
        raw = row["pnev_json"] if isinstance(row, dict) else row[0]
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        return json.loads(raw)
    except Exception:
        return {}


def _sk(sezione: str, campo: str, paz_id: int) -> str:
    """Chiave session_state univoca."""
    return f"anam_{paz_id}_{sezione}_{campo}"


def _scala(label: str, key: str, default: int = 3,
           min_label: str = "1 Min",
           max_label: str = "5 Max") -> int:
    """Slider 1-5 con etichette."""
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"**{label}**")
        st.caption(f"{min_label}  →  {max_label}")
    with col2:
        val = st.select_slider(
            label, options=[1, 2, 3, 4, 5],
            value=default, key=key,
            label_visibility="collapsed"
        )
    colore = (
        "🔴" if val <= 2 else
        "🟡" if val == 3 else
        "🟢"
    )
    st.caption(f"Valore: {val}/5 {colore}")
    return val


def _radio(label: str, opzioni: list, key: str, default: str = None) -> str:
    idx = opzioni.index(default) if default in opzioni else 0
    return st.radio(label, opzioni, index=idx, horizontal=True, key=key)


def _check(label: str, key: str, default: bool = False) -> bool:
    return st.checkbox(label, value=default, key=key)


def _campo(label: str, key: str, default: str = "", height: int = None) -> str:
    if height:
        return st.text_area(label, value=default, key=key, height=height)
    return st.text_input(label, value=default, key=key)


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 1 — GRAVIDANZA
# ══════════════════════════════════════════════════════════════════════

def _s1_gravidanza(paz_id: int, stored: dict) -> dict:
    st.markdown("### 1. Gravidanza")
    d = stored.get("gravidanza", {})
    s = lambda c, v=3: _sk("s1", c, paz_id)

    st.markdown("#### Dati oggettivi")
    termine = _radio("Termine gestazionale",
        ["Termine (38-42 sett.)", "Pre-termine (<38)", "Post-termine (>42)"],
        s("termine"), d.get("termine"))
    sett = _campo("N. settimane (se noto)", s("sett"), d.get("sett", ""))
    tipo_grav = _radio("Tipo gravidanza",
        ["Singola", "Gemellare", "Altro"],
        s("tipo_grav"), d.get("tipo_grav"))

    st.markdown("**Complicanze fisiche:**")
    compl_opts = [
        "Ipertensione/pre-eclampsia", "Diabete gestazionale",
        "Infezioni (TORCH)", "Sanguinamenti", "Placenta previa",
        "Oligoidramnios/polidramnios", "Cadute/traumi", "Ricoveri",
        "Farmaci (vedi note)", "Fumo/alcol/sostanze",
    ]
    complicanze = []
    cols = st.columns(2)
    for i, c in enumerate(compl_opts):
        with cols[i % 2]:
            if st.checkbox(c, value=c in d.get("complicanze", []),
                           key=s(f"compl_{i}")):
                complicanze.append(c)

    movimenti = _radio("Movimenti fetali",
        ["Normali", "Ridotti", "Eccessivi", "Non valutabili"],
        s("movimenti"), d.get("movimenti"))
    controlli = _radio("Controlli prenatali",
        ["Regolari", "Parziali", "Assenti"],
        s("controlli"), d.get("controlli"))

    st.markdown("---")
    st.markdown("#### Profilo emotivo e relazionale — The Organism")
    stato_em = _scala(
        "Stato emotivo della madre",
        s("stato_em"), d.get("stato_em", 3),
        "1 Molto disturbato", "5 Sereno"
    )
    qualita_coppia = _scala(
        "Qualita' della relazione di coppia",
        s("qualita_coppia"), d.get("qualita_coppia", 3),
        "1 Conflittuale/assente", "5 Stabile"
    )
    supporto = _scala(
        "Supporto familiare e sociale",
        s("supporto"), d.get("supporto", 3),
        "1 Assente", "5 Ottimo"
    )

    st.markdown("**Checklist eventi stressanti:**")
    eventi_opts = [
        "Lutto in famiglia", "Separazione/divorzio",
        "Violenza domestica", "Perdita del lavoro",
        "Trasloco/cambio paese", "Conflitti familiari gravi",
        "Gravidanza non desiderata", "Problemi economici",
        "Malattia grave familiare", "Altro",
    ]
    eventi = []
    cols2 = st.columns(2)
    for i, e in enumerate(eventi_opts):
        with cols2[i % 2]:
            if st.checkbox(e, value=e in d.get("eventi", []),
                           key=s(f"ev_{i}")):
                eventi.append(e)

    pianificata = _radio("Gravidanza",
        ["Pianificata", "Inaspettata ma accettata", "Non desiderata"],
        s("pianificata"), d.get("pianificata"))
    note = _campo("Note cliniche gravidanza", s("note"),
                  d.get("note", ""), height=80)

    return {
        "gravidanza": {
            "termine": termine, "sett": sett, "tipo_grav": tipo_grav,
            "complicanze": complicanze, "movimenti": movimenti,
            "controlli": controlli, "stato_em": stato_em,
            "qualita_coppia": qualita_coppia, "supporto": supporto,
            "eventi": eventi, "pianificata": pianificata, "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 2 — PARTO
# ══════════════════════════════════════════════════════════════════════

def _s2_parto(paz_id: int, stored: dict) -> dict:
    st.markdown("### 2. Parto")
    d = stored.get("parto", {})
    s = lambda c: _sk("s2", c, paz_id)

    tipo = _radio("Tipo di parto",
        ["Naturale", "Cesareo programmato", "Cesareo emergenza", "Ventosa/forcipe"],
        s("tipo"), d.get("tipo"))
    sett = _campo("Settimane effettive", s("sett"), d.get("sett", ""))
    durata = _campo("Durata travaglio (ore circa)", s("durata"), d.get("durata", ""))
    pres = _radio("Presentazione",
        ["Cefalica", "Podalica", "Trasversa", "Altro"],
        s("pres"), d.get("pres"))

    st.markdown("**Complicanze al parto:**")
    compl_opts = [
        "Distress fetale", "Cordone al collo", "Emorragia materna",
        "Anestesia generale", "Prolasso del cordone",
        "Rottura prematura membrane", "Distocia di spalla", "Altro",
    ]
    complicanze = []
    cols = st.columns(2)
    for i, c in enumerate(compl_opts):
        with cols[i % 2]:
            if st.checkbox(c, value=c in d.get("complicanze", []),
                           key=s(f"compl_{i}")):
                complicanze.append(c)

    apgar1 = _campo("Apgar a 1 minuto (0-10)", s("apgar1"), d.get("apgar1", ""))
    apgar5 = _campo("Apgar a 5 minuti (0-10)", s("apgar5"), d.get("apgar5", ""))
    pianto = _radio("Pianto immediato",
        ["Si", "No", "Tardivo"], s("pianto"), d.get("pianto"))
    contatto = _radio("Contatto pelle-pelle",
        ["Si", "No", "Ritardato"], s("contatto"), d.get("contatto"))
    suzione = _radio("Suzione immediata",
        ["Efficace", "Debole", "Difficoltosa", "Assente"],
        s("suzione"), d.get("suzione"))
    note = _campo("Note parto", s("note"), d.get("note", ""), height=80)

    return {
        "parto": {
            "tipo": tipo, "sett": sett, "durata": durata, "pres": pres,
            "complicanze": complicanze, "apgar1": apgar1, "apgar5": apgar5,
            "pianto": pianto, "contatto": contatto, "suzione": suzione,
            "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 3 — PERIODO NEONATALE
# ══════════════════════════════════════════════════════════════════════

def _s3_neonatale(paz_id: int, stored: dict) -> dict:
    st.markdown("### 3. Periodo Neonatale (0-3 mesi)")
    d = stored.get("neonatale", {})
    s = lambda c: _sk("s3", c, paz_id)

    tono = _radio("Tono muscolare generale",
        ["Normale", "Ipotonia", "Ipertonia", "Misto"],
        s("tono"), d.get("tono"))
    pianto = _radio("Pianto",
        ["Normale", "Eccessivo/inconsolabile", "Scarso/assente"],
        s("pianto"), d.get("pianto"))

    st.markdown("**Riflessi primitivi (osservati o riferiti):**")
    rifl = {
        "moro":     _radio("Riflesso di Moro",
            ["Presente normale", "Esagerato", "Ridotto/assente"],
            s("moro"), d.get("moro")),
        "prensione": _radio("Prensione",
            ["Presente normale", "Esagerato", "Ridotto/assente"],
            s("prensione"), d.get("prensione")),
        "suzione":  _radio("Suzione",
            ["Presente normale", "Debole", "Assente"],
            s("suzione"), d.get("suzione")),
        "rooting":  _radio("Radice (rooting)",
            ["Presente normale", "Ridotto", "Assente"],
            s("rooting"), d.get("rooting")),
    }
    note = _campo("Note neonatale", s("note"), d.get("note", ""), height=80)

    return {"neonatale": {"tono": tono, "pianto": pianto,
                          "riflessi": rifl, "note": note}}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 4 — ALIMENTAZIONE
# ══════════════════════════════════════════════════════════════════════

def _s4_alimentazione(paz_id: int, stored: dict) -> dict:
    st.markdown("### 4. Alimentazione")
    d = stored.get("alimentazione", {})
    s = lambda c: _sk("s4", c, paz_id)

    allatt = _radio("Allattamento",
        ["Seno esclusivo", "Misto", "Artificiale", "Non avviato"],
        s("allatt"), d.get("allatt"))
    durata_allatt = _campo("Durata allattamento al seno (mesi)",
        s("durata_allatt"), d.get("durata_allatt", ""))
    suzione = _radio("Qualita' suzione",
        ["Efficace", "Debole", "Difficoltosa", "Con dolore madre"],
        s("suzione"), d.get("suzione"))
    svez = _radio("Modalita' svezzamento",
        ["Tradizionale", "BLW", "Misto", "Non ancora"],
        s("svez"), d.get("svez"))
    eta_svez = _campo("Eta' inizio svezzamento (mesi)",
        s("eta_svez"), d.get("eta_svez", ""))

    st.markdown("**Difficolta' alimentari:**")
    diff_opts = [
        "Reflusso gastroesofageo", "Coliche intense",
        "Vomito frequente", "Rifiuto seno/biberon",
        "Difficolta' deglutizione", "Masticazione difficoltosa",
        "Selettivita' alimentare", "Texture rifiutate",
        "Ipersensibilita' orale", "Soffocamento frequente",
    ]
    difficolta = []
    cols = st.columns(2)
    for i, dd in enumerate(diff_opts):
        with cols[i % 2]:
            if st.checkbox(dd, value=dd in d.get("difficolta", []),
                           key=s(f"diff_{i}")):
                difficolta.append(dd)

    selettivita = _scala(
        "Selettivita' alimentare",
        s("selettivita"), d.get("selettivita", 1),
        "1 Nessuna", "5 Grave"
    )
    note = _campo("Note alimentazione", s("note"), d.get("note", ""), height=80)

    return {
        "alimentazione": {
            "allatt": allatt, "durata_allatt": durata_allatt,
            "suzione": suzione, "svez": svez, "eta_svez": eta_svez,
            "difficolta": difficolta, "selettivita": selettivita, "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 5 — SVILUPPO MOTORIO (TEITELBAUM)
# ══════════════════════════════════════════════════════════════════════

def _s5_motorio(paz_id: int, stored: dict) -> dict:
    st.markdown("### 5. Sviluppo Motorio — Modello Teitelbaum")
    st.caption(
        "Riferimento: Teitelbaum O. & P. (2004). "
        "Analisi del movimento come marker precoce di rischio neurologico."
    )
    d = stored.get("motorio", {})
    s = lambda c: _sk("s5", c, paz_id)

    st.markdown("#### Tappe motorie (eta' in mesi)")
    tappe = {}
    milestone = [
        ("controllo_capo", "Controllo del capo"),
        ("rotolamento",    "Rotolamento"),
        ("seduta",         "Postura seduta"),
        ("eretta",         "Postura eretta con supporto"),
        ("primi_passi",    "Primi passi autonomi"),
        ("scale",          "Salire scale (alternato)"),
    ]
    cols = st.columns(2)
    for i, (k, label) in enumerate(milestone):
        with cols[i % 2]:
            tappe[k] = _campo(label, s(k), d.get("tappe", {}).get(k, ""))

    st.markdown("#### Raddrizzamento e simmetria (0-4 mesi)")
    simmetria = _radio("Simmetria posturale",
        ["Simmetrica", "Asimmetrica DX", "Asimmetrica SX"],
        s("simmetria"), d.get("simmetria"))
    tilt = _radio("Tilt test (riflesso raddrizzamento)",
        ["Presente normale", "Ritardato", "Assente", "Non osservato"],
        s("tilt"), d.get("tilt"))
    atnr = _radio("ATNR (posizione schermitore)",
        ["Fisiologico", "Persistente >6 mesi", "Non osservato"],
        s("atnr"), d.get("atnr"))

    st.markdown("#### Gattonamento")
    gatt_pres = _radio("Gattonamento presente",
        ["Si", "No (saltato)", "Parziale"],
        s("gatt_pres"), d.get("gatt_pres"))
    gatt_schema = _radio("Schema gattonamento",
        ["Crociato (normale)", "Omolaterale", "Strisciamento", "Rotolamento"],
        s("gatt_schema"), d.get("gatt_schema"))
    gatt_simm = _radio("Simmetria gattonamento",
        ["Simmetrica", "Asimmetrica", "Non valutabile"],
        s("gatt_simm"), d.get("gatt_simm"))
    crossing = _campo("Crossing midline (osservazioni)",
        s("crossing"), d.get("crossing", ""))

    st.markdown("#### Cammino")
    appoggio = _radio("Appoggio plantare",
        ["Tallone-punta (normale)", "Punta-punta", "Piatto"],
        s("appoggio"), d.get("appoggio"))
    base = _radio("Base d'appoggio",
        ["Normale", "Allargata", "Stretta"],
        s("base"), d.get("base"))
    cadute = _radio("Cadute frequenti",
        ["No", "Si - rare", "Si - frequenti"],
        s("cadute"), d.get("cadute"))
    rifl_prot = _radio("Riflessi protettivi",
        ["Presenti", "Ridotti", "Assenti"],
        s("rifl_prot"), d.get("rifl_prot"))

    note = _campo("Note sviluppo motorio", s("note"),
                  d.get("note", ""), height=80)

    return {
        "motorio": {
            "tappe": tappe, "simmetria": simmetria, "tilt": tilt,
            "atnr": atnr, "gatt_pres": gatt_pres, "gatt_schema": gatt_schema,
            "gatt_simm": gatt_simm, "crossing": crossing, "appoggio": appoggio,
            "base": base, "cadute": cadute, "rifl_prot": rifl_prot, "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 6 — SVILUPPO SENSORIALE E COMUNICATIVO
# ══════════════════════════════════════════════════════════════════════

def _s6_sensoriale(paz_id: int, stored: dict) -> dict:
    st.markdown("### 6. Sviluppo Sensoriale e Comunicativo")
    d = stored.get("sensoriale", {})
    s = lambda c: _sk("s6", c, paz_id)

    prime_parole = _campo("Prime parole (eta' mesi)", s("prime_parole"),
                          d.get("prime_parole", ""))
    prime_frasi  = _campo("Prime frasi 2 parole (eta' mesi)", s("prime_frasi"),
                          d.get("prime_frasi", ""))
    nome = _radio("Risposta al nome",
        ["Buona", "Ridotta", "Assente", "Tardiva"],
        s("nome"), d.get("nome"))
    occhi = _radio("Contatto oculare",
        ["Buono", "Ridotto", "Assente", "Intermittente"],
        s("occhi"), d.get("occhi"))
    suoni = _radio("Risposta ai suoni",
        ["Normale", "Ridotta", "Esagerata", "Variabile"],
        s("suoni"), d.get("suoni"))

    st.markdown("**Preferenze/reattivita' sensoriale:**")
    sens_opts = [
        "Ipersensibilita' tattile", "Iposensibilita' tattile",
        "Ipersensibilita' uditiva", "Iposensibilita' uditiva",
        "Ipersensibilita' visiva", "Ricerca stimoli sensoriali",
        "Difficolta' texture", "Dondolamento/movimenti ritmici",
        "Fascinazione oggetti rotanti", "Preferenze olfattive intense",
    ]
    sensoriale = []
    cols = st.columns(2)
    for i, so in enumerate(sens_opts):
        with cols[i % 2]:
            if st.checkbox(so, value=so in d.get("sensoriale", []),
                           key=s(f"sens_{i}")):
                sensoriale.append(so)

    note = _campo("Note sensoriale", s("note"), d.get("note", ""), height=80)

    return {
        "sensoriale": {
            "prime_parole": prime_parole, "prime_frasi": prime_frasi,
            "nome": nome, "occhi": occhi, "suoni": suoni,
            "sensoriale": sensoriale, "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 7 — SEGNALI DI ALLERTA
# ══════════════════════════════════════════════════════════════════════

def _s7_allerta(paz_id: int, stored: dict) -> dict:
    st.markdown("### 7. Segnali di Allerta")
    st.caption("Spuntare i segnali presenti o riferiti dai genitori.")
    d = stored.get("allerta", {})
    s = lambda c: _sk("s7", c, paz_id)

    allerta_opts = [
        "Perdita di abilita' gia' acquisite",
        "Assenza linguaggio a 24 mesi",
        "Nessun sorriso sociale a 6 mesi",
        "Nessuna risposta al nome a 12 mesi",
        "Movimenti ripetitivi stereotipati",
        "Assenza lallazione a 12 mesi",
        "Nessun gesto (pointing) a 12 mesi",
        "Iperreattivita' sensoriale grave",
        "Iporeattivita' sensoriale grave",
        "Difficolta' alimentari gravi",
        "Sonno molto disturbato oltre 18 mesi",
        "Asimmetria motoria persistente",
        "Riflessi primitivi persistenti oltre i limiti",
        "Assenza gattonamento crociato",
        "Cammino in punta di piedi persistente",
        "Scarso interesse per le persone",
    ]
    presenti = []
    cols = st.columns(2)
    for i, ao in enumerate(allerta_opts):
        with cols[i % 2]:
            if st.checkbox(ao, value=ao in d.get("presenti", []),
                           key=s(f"all_{i}")):
                presenti.append(ao)

    n = len(presenti)
    if n == 0:
        st.success("Nessun segnale di allerta segnalato.")
    elif n <= 2:
        st.warning(f"{n} segnale/i di allerta — monitorare.")
    else:
        st.error(f"{n} segnali di allerta — approfondire urgentemente.")

    note = _campo("Note segnali di allerta", s("note"),
                  d.get("note", ""), height=80)

    return {"allerta": {"presenti": presenti, "n_allerta": n, "note": note}}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 8 — CONTESTO FAMILIARE
# ══════════════════════════════════════════════════════════════════════

def _s8_famiglia(paz_id: int, stored: dict) -> dict:
    st.markdown("### 8. Contesto Familiare e Anamnesi Familiare")
    d = stored.get("famiglia", {})
    s = lambda c: _sk("s8", c, paz_id)

    n_fratelli = _campo("N. fratelli/sorelle", s("n_fratelli"),
                        d.get("n_fratelli", ""))
    fratelli_simili = _radio("Fratelli/sorelle con difficolta' simili",
        ["No", "Si"], s("fratelli_simili"), d.get("fratelli_simili"))

    st.markdown("**Familiarita' per:**")
    fam_opts = [
        "DSA (dislessia, disgrafia, discalculia)",
        "ADHD / deficit attenzione",
        "Disturbo spettro autistico",
        "Disturbi del linguaggio",
        "Problemi visivi significativi",
        "Problemi uditivi / sordita'",
        "Disturbi movimento / coordinazione",
        "Epilessia / disturbi neurologici",
        "Ansia / depressione",
        "Altro",
    ]
    familiarita = []
    cols = st.columns(2)
    for i, fo in enumerate(fam_opts):
        with cols[i % 2]:
            if st.checkbox(fo, value=fo in d.get("familiarita", []),
                           key=s(f"fam_{i}")):
                familiarita.append(fo)

    lingua = _radio("Lingua parlata in casa",
        ["Italiano", "Bilingue", "Altra lingua"], s("lingua"), d.get("lingua"))
    note = _campo("Note contesto familiare", s("note"),
                  d.get("note", ""), height=80)

    return {
        "famiglia": {
            "n_fratelli": n_fratelli, "fratelli_simili": fratelli_simili,
            "familiarita": familiarita, "lingua": lingua, "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE 9 — MOTIVO DELL'INVIO
# ══════════════════════════════════════════════════════════════════════

def _s9_invio(paz_id: int, stored: dict) -> dict:
    st.markdown("### 9. Motivo dell'Invio / Domanda Clinica")
    d = stored.get("invio", {})
    s = lambda c: _sk("s9", c, paz_id)

    chi_invia = _radio("Chi invia",
        ["Genitori", "Pediatra", "Neurologo", "Logopedista",
         "Insegnante", "Neuropsichiatra", "Altro"],
        s("chi_invia"), d.get("chi_invia"))
    da_quanto = _campo("Da quanto tempo (mesi)", s("da_quanto"),
                       d.get("da_quanto", ""))
    preoccupazione = _campo(
        "Preoccupazione principale dei genitori",
        s("preoccupazione"), d.get("preoccupazione", ""), height=100
    )

    st.markdown("**Trattamenti precedenti:**")
    tratt_opts = [
        "Logopedia", "Psicomotricita'", "Fisioterapia",
        "Neuropsicomotricita'", "Terapia occupazionale",
        "Sostegno scolastico", "Psicoterapia", "Altro",
    ]
    trattamenti = []
    cols = st.columns(2)
    for i, to in enumerate(tratt_opts):
        with cols[i % 2]:
            if st.checkbox(to, value=to in d.get("trattamenti", []),
                           key=s(f"tratt_{i}")):
                trattamenti.append(to)

    note = _campo("Note motivo invio", s("note"), d.get("note", ""), height=80)

    return {
        "invio": {
            "chi_invia": chi_invia, "da_quanto": da_quanto,
            "preoccupazione": preoccupazione, "trattamenti": trattamenti,
            "note": note,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  PROFILO DI RISCHIO AUTOMATICO
# ══════════════════════════════════════════════════════════════════════

def _profilo_rischio(dati: dict) -> None:
    st.markdown("---")
    st.markdown("### Profilo di rischio automatico")

    score = 0
    flags = []

    # Gravidanza
    g = dati.get("gravidanza", {})
    if g.get("stato_em", 3) <= 2:
        score += 2; flags.append("Stress emotivo materno in gravidanza")
    if g.get("qualita_coppia", 3) <= 2:
        score += 1; flags.append("Conflittualita' di coppia in gravidanza")
    if len(g.get("eventi", [])) >= 2:
        score += 1; flags.append("Piu' eventi stressanti in gravidanza")
    if g.get("termine") and "Pre-termine" in g.get("termine", ""):
        score += 2; flags.append("Pre-termine")

    # Parto
    p = dati.get("parto", {})
    try:
        a1 = int(p.get("apgar1", 10) or 10)
        if a1 < 7:
            score += 2; flags.append(f"Apgar basso a 1' ({a1})")
    except Exception:
        pass
    if p.get("pianto") in ["No", "Tardivo"]:
        score += 1; flags.append("Pianto non immediato")
    if len(p.get("complicanze", [])) >= 2:
        score += 1; flags.append("Complicanze al parto")

    # Motorio
    m = dati.get("motorio", {})
    if m.get("gatt_pres") in ["No (saltato)"]:
        score += 2; flags.append("Gattonamento saltato")
    if m.get("gatt_schema") in ["Omolaterale", "Strisciamento"]:
        score += 1; flags.append("Schema gattonamento atipico")
    if m.get("atnr") == "Persistente >6 mesi":
        score += 2; flags.append("ATNR persistente")
    if m.get("simmetria") in ["Asimmetrica DX", "Asimmetrica SX"]:
        score += 1; flags.append("Asimmetria posturale")

    # Alimentazione
    al = dati.get("alimentazione", {})
    if al.get("selettivita", 1) >= 4:
        score += 1; flags.append("Selettivita' alimentare grave")

    # Segnali allerta
    n_all = dati.get("allerta", {}).get("n_allerta", 0)
    score += n_all
    if n_all > 0:
        flags.append(f"{n_all} segnali di allerta")

    # Risultato
    col1, col2 = st.columns(2)
    with col1:
        if score == 0:
            st.success(f"Score di rischio: {score} — Profilo nella norma")
        elif score <= 4:
            st.warning(f"Score di rischio: {score} — Monitorare")
        else:
            st.error(f"Score di rischio: {score} — Approfondire urgentemente")

    with col2:
        st.metric("Fattori di rischio rilevati", len(flags))

    if flags:
        st.markdown("**Fattori rilevati:**")
        for f in flags:
            st.markdown(f"- {f}")

    return score


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

def render_anamnesi_the_organism(conn, paz_id: int) -> None:
    """Scheda anamnesi completa The Organism — 9 sezioni."""

    st.subheader("Scheda Anamnesi Neuropsicologica — The Organism")
    st.caption(
        "Piramide degli apprendimenti | Modello Teitelbaum | "
        "Scale visive + Checklist"
    )

    # Carica dati esistenti
    stored_full = _carica(conn, paz_id)
    stored = stored_full.get("anamnesi_the_organism", {})

    # Tab per sezione
    tabs = st.tabs([
        "1. Gravidanza", "2. Parto", "3. Neonatale",
        "4. Alimentazione", "5. Motorio (Teitelbaum)",
        "6. Sensoriale", "7. Segnali allerta",
        "8. Famiglia", "9. Invio", "Profilo rischio",
    ])

    dati_correnti = {}

    with tabs[0]:
        dati_correnti.update(_s1_gravidanza(paz_id, stored))
        if st.button("Salva gravidanza", key=f"save_s1_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[1]:
        dati_correnti.update(_s2_parto(paz_id, stored))
        if st.button("Salva parto", key=f"save_s2_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[2]:
        dati_correnti.update(_s3_neonatale(paz_id, stored))
        if st.button("Salva neonatale", key=f"save_s3_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[3]:
        dati_correnti.update(_s4_alimentazione(paz_id, stored))
        if st.button("Salva alimentazione", key=f"save_s4_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[4]:
        dati_correnti.update(_s5_motorio(paz_id, stored))
        if st.button("Salva motorio", key=f"save_s5_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[5]:
        dati_correnti.update(_s6_sensoriale(paz_id, stored))
        if st.button("Salva sensoriale", key=f"save_s6_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[6]:
        dati_correnti.update(_s7_allerta(paz_id, stored))
        if st.button("Salva segnali allerta", key=f"save_s7_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[7]:
        dati_correnti.update(_s8_famiglia(paz_id, stored))
        if st.button("Salva famiglia", key=f"save_s8_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[8]:
        dati_correnti.update(_s9_invio(paz_id, stored))
        if st.button("Salva motivo invio", key=f"save_s9_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})

    with tabs[9]:
        _profilo_rischio(stored)
        if st.button("Ricalcola profilo", key=f"risc_{paz_id}"):
            st.rerun()
        if st.button("Salva tutto e aggiorna profilo",
                     type="primary", key=f"save_all_{paz_id}"):
            _salva(conn, paz_id, {"anamnesi_the_organism": dati_correnti})
            st.rerun()
