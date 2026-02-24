# -*- coding: utf-8 -*-
import streamlit as st

import pnev_module as pnev
try:
    import pnev_ai
    PNEV_AI_AVAILABLE = True
except Exception:
    pnev_ai = None
    PNEV_AI_AVAILABLE = False
# --- FIX: verifica disponibilità psycopg2 (deve esistere prima di usare _connect_cached) ---
PSYCOPG2_AVAILABLE = False
try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
    PSYCOPG2_AVAILABLE = True
except Exception:
    PSYCOPG2_AVAILABLE = False

USE_S3 = False  # Disabilitato: archiviamo su Neon (BYTEA) e/o altri canali



# --- PRIVACY PDF TEMPLATES (DIFFERENZIATI) ---
# STAMPABILE COMPLETO (UI stampa / download)
PDF_PRIVACY_ADULTO_TEMPLATE = "assets/privacy/Consenso_Informato_Privacy_Adulto_The_Organism_STAMPABILE_COMPLETO_v5.pdf"
PDF_PRIVACY_MINORE_TEMPLATE = "assets/privacy/Consenso_Informato_Privacy_Minore_The_Organism_STAMPABILE_COMPLETO_v5.pdf"

# FIRMA ONLINE (pagina pubblica)
PDF_PRIVACY_ADULTO_SIGN_TEMPLATE = "assets/privacy/Consenso_Informato_Privacy_Adulto_The_Organism_v4_FINAL.pdf"
PDF_PRIVACY_MINORE_SIGN_TEMPLATE = "assets/privacy/Consenso_Informato_Privacy_Minore_The_Organism_v4_FINAL.pdf"



def _privacy_abs_path(p: str) -> str:
    """Resolve relative paths against app directory (works on Streamlit Cloud)."""
    try:
        base = os.path.dirname(__file__)
    except Exception:
        base = os.getcwd()
    return p if os.path.isabs(p) else os.path.join(base, p)

def _check_privacy_templates_ui():
    """Mostra in UI lo stato dei file template privacy (senza crashare)."""
    st.markdown("### ✅ Diagnostica template Privacy (file presenti?)")
    files = [
        ("STAMPABILE Adulto", PDF_PRIVACY_ADULTO_TEMPLATE),
        ("STAMPABILE Minore", PDF_PRIVACY_MINORE_TEMPLATE),
        ("FIRMA ONLINE Adulto", PDF_PRIVACY_ADULTO_SIGN_TEMPLATE),
        ("FIRMA ONLINE Minore", PDF_PRIVACY_MINORE_SIGN_TEMPLATE),
    ]
    rows = []
    for label, p in files:
        ap = _privacy_abs_path(p)
        ok = False
        try:
            ok = os.path.exists(ap)
        except Exception:
            ok = False
        rows.append({"Template": label, "Path": p, "Path risolto": ap, "Presente": "✅" if ok else "❌"})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    missing = [r for r in rows if r["Presente"] == "❌"]
    if missing:
        st.warning("Mancano uno o più file template. Caricali nel repo nella cartella indicata (assets/privacy).")

def _valid_endpoint_url(url):
    if not url:
        return None
    u = str(url).strip()
    if not u:
        return None
    if not (u.startswith("http://") or u.startswith("https://")):
        return None
    return u

# ---------- AUTO-DETECT TABella PAZIENTI (SQLite/PostgreSQL) ----------
def _qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def _get_columns(conn, table_name: str):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
        """, (table_name,))
        cols = [r[0] for r in cur.fetchall()]
        if cols:
            return cols
    except Exception:
        pass
    try:
        cur.execute(f"PRAGMA table_info({_qident(table_name)})")
        rows = cur.fetchall()
        return [r[1] for r in rows]
    except Exception:
        return []

def _detect_patient_table_and_cols(conn):
    table_candidates = [
        'pazienti','Pazienti','patients','Patients','patienti','Patienti',
        'anagrafica_pazienti','Anagrafica_Pazienti','tbl_pazienti','Tbl_Pazienti'
    ]
    id_cols = ['id','ID','paziente_id','Paziente_ID','id_paziente','ID_Paziente','idPaziente']
    cogn_cols = ['cognome','Cognome','last_name','LastName','lastname','cognome_paziente','Cognome_Paziente']
    nome_cols = ['nome','Nome','first_name','FirstName','firstname','nome_paziente','Nome_Paziente']
    dn_cols = ['data_nascita','Data_Nascita','birth_date','BirthDate','dataNascita','DataNascita','data_n']
    scuola_cols = ['scuola','Scuola','istituto','Istituto','classe_scuola','Classe_Scuola']
    eta_cols = ['eta','Eta','age','Age']

    cur = conn.cursor()
    discovered = []
    try:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public'
        """)
        discovered = [r[0] for r in cur.fetchall()]
    except Exception:
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            discovered = [r[0] for r in cur.fetchall()]
        except Exception:
            discovered = []

    for t in discovered:
        tl = str(t).lower()
        if ('paz' in tl or 'patient' in tl) and t not in table_candidates:
            table_candidates.insert(0, t)

    def pick(cols, candidates):
        cols_set = set(cols)
        for c in candidates:
            if c in cols_set:
                return c
        lower_map = {x.lower(): x for x in cols}
        for c in candidates:
            if c.lower() in lower_map:
                return lower_map[c.lower()]
        return None

    for table in table_candidates:
        cols = _get_columns(conn, table)
        if not cols:
            continue
        idc = pick(cols, id_cols)
        cc  = pick(cols, cogn_cols)
        nc  = pick(cols, nome_cols)
        if not (idc and cc and nc):
            continue
        dnc = pick(cols, dn_cols)
        sc  = pick(cols, scuola_cols)
        ec  = pick(cols, eta_cols)
        return table, {'id': idc, 'cognome': cc, 'nome': nc, 'data_nascita': dnc, 'scuola': sc, 'eta': ec}
    return None, {}

def fetch_pazienti_for_select(conn, limit=5000):
    table, colmap = _detect_patient_table_and_cols(conn)
    if not table:
        return [], None, None

    idc = colmap['id']; cc = colmap['cognome']; nc = colmap['nome']
    dnc = colmap.get('data_nascita'); sc = colmap.get('scuola'); ec = colmap.get('eta')

    select_cols = [idc, cc, nc]
    if dnc: select_cols.append(dnc)
    if sc:  select_cols.append(sc)
    if ec:  select_cols.append(ec)

    cur = conn.cursor()
    cols_sql = ', '.join(_qident(c) for c in select_cols)
    order_sql = f"{_qident(cc)}, {_qident(nc)}"
    sql = f"SELECT {cols_sql} FROM {_qident(table)} ORDER BY {order_sql} LIMIT {int(limit)}"
    try:
        cur.execute(sql)
        rows = cur.fetchall()
    except Exception:
        try:
            cur.execute(f"SELECT {cols_sql} FROM {_qident(table)} ORDER BY {order_sql}")
            rows = cur.fetchall()[:limit]
        except Exception:
            return [], table, colmap

    out = []
    for r in rows:
        r = list(r)
        while len(r) < 6:
            r.append('')
        out.append(tuple(r[:6]))
    return out, table, colmap


# ---------- DEBUG DB (non mostra credenziali) ----------
def _debug_list_tables(conn, limit=200):
    """Ritorna lista di tuple (schema, table). Gestisce cursor che ritorna dict/RealDictRow."""
    cur = conn.cursor()
    # PostgreSQL: schema + table
    try:
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            ORDER BY table_schema, table_name
        """)
        rows = cur.fetchall()
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append((r.get("table_schema"), r.get("table_name")))
            else:
                try:
                    out.append((r[0], r[1]))
                except Exception:
                    out.append((None, str(r)))
        return out[:limit]
    except Exception:
        pass

    # SQLite fallback
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = cur.fetchall()
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append(("main", r.get("name")))
            else:
                out.append(("main", r[0]))
        return out[:limit]
    except Exception:
        return []

def _debug_table_columns(conn, schema, table):
    """Ritorna lista di tuple (colonna, tipo) gestendo righe dict/tuple."""
    cur = conn.cursor()
    # PostgreSQL
    try:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table))
        rows = cur.fetchall()
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append((r.get("column_name"), r.get("data_type")))
            else:
                try:
                    out.append((r[0], r[1]))
                except Exception:
                    out.append((str(r), ""))
        if out:
            return out
    except Exception:
        pass

    # SQLite
    try:
        cur.execute(f"PRAGMA table_info({table})")
        rows = cur.fetchall()
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append((r.get("name"), r.get("type")))
            else:
                out.append((r[1], r[2]))
        return out
    except Exception:
        return []

def _debug_count_rows(conn, schema, table):
    cur = conn.cursor()
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
        return int(cur.fetchone()[0])
    except Exception:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            return int(cur.fetchone()[0])
        except Exception:
            return None




def debug_secrets_auth():
    has_auth = "auth" in st.secrets
    st.write("SECRETS: has [auth] =", has_auth)

    if has_auth:
        u_ok = "username" in st.secrets["auth"]
        p_ok = "password" in st.secrets["auth"]
        st.write("SECRETS auth.username presente =", u_ok)
        st.write("SECRETS auth.password presente =", p_ok)

        if p_ok:
            pw = st.secrets["auth"]["password"]
            st.write("Lunghezza password letta =", len(pw))
            st.write("Password vuota? =", (len(pw) == 0))

# chiama la funzione solo in test o solo per admin

import sqlite3

def _ai_enabled() -> bool:
    """Enable AI helper ONLY in TEST unless explicitly allowed.

    Controlled via Streamlit Secrets:
    [ai]
    ENABLED = true
    """
    try:
        if str(APP_MODE).lower().strip() != "test":
            return False
        a = st.secrets.get("ai", {})
        return bool(a.get("ENABLED", False))
    except Exception:
        return False

APP_MODE = st.secrets.get("APP_MODE", "prod")


def _inpps_cutoff() -> int:
    """Cut-off operativo (screening) per INPPS. Configurabile via Secrets: [pnev] INPPS_CUTOFF=7"""
    try:
        return int(st.secrets.get("pnev", {}).get("INPPS_CUTOFF", 7))
    except Exception:
        return 7



def _is_empty_pnev(raw) -> bool:
    """True if pnev_json is missing/empty (works for sqlite TEXT or postgres JSONB)."""
    if raw is None:
        return True
    try:
        if isinstance(raw, dict):
            return len(raw) == 0
    except Exception:
        pass
    s = str(raw).strip()
    if s == "" or s.lower() == "null":
        return True
    return s in ("{}", "'{}'", '"{}"', "[]")

def migrate_anamnesi_legacy_to_pnev(cur, paziente_id: int | None = None, limit: int = 5000) -> dict:
    """Populate pnev_json/pnev_summary for legacy Anamnesi rows that have only Storia/Note.
    Does NOT overwrite existing pnev_json (non-empty) or pnev_summary (non-empty).
    Returns stats dict.
    """
    stats = {"scanned": 0, "updated": 0, "skipped_has_pnev": 0, "skipped_no_content": 0}

    if paziente_id is None:
        cur.execute("SELECT ID, Paziente_ID, Data_Anamnesi, Motivo, Storia, Note, pnev_json, pnev_summary FROM Anamnesi ORDER BY ID DESC LIMIT ?", (int(limit),))
    else:
        cur.execute("SELECT ID, Paziente_ID, Data_Anamnesi, Motivo, Storia, Note, pnev_json, pnev_summary FROM Anamnesi WHERE Paziente_ID = ? ORDER BY ID DESC LIMIT ?", (int(paziente_id), int(limit)))

    rows = cur.fetchall() or []
    for r in rows:
        stats["scanned"] += 1
        rid = int(r["ID"]) if hasattr(r, "__getitem__") else int(r[0])

        motivo = (r.get("Motivo") if hasattr(r, "get") else r[3]) or ""
        storia = (r.get("Storia") if hasattr(r, "get") else r[4]) or ""
        note = (r.get("Note") if hasattr(r, "get") else r[5]) or ""
        pnev_raw = (r.get("pnev_json") if hasattr(r, "get") else r[6])
        pnev_sum = (r.get("pnev_summary") if hasattr(r, "get") else r[7]) or ""

        if (not _is_empty_pnev(pnev_raw)) or (str(pnev_sum).strip() != ""):
            stats["skipped_has_pnev"] += 1
            continue

        content = "\n\n".join([x.strip() for x in [motivo, storia, note] if str(x).strip()])
        if not content.strip():
            stats["skipped_no_content"] += 1
            continue

        payload = {
            "meta": {
                "source": "legacy_anamnesi_migration",
                "migrated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            },
            "legacy": {
                "motivo": motivo.strip(),
                "storia": storia.strip(),
                "note": note.strip(),
            },
        }

        summary = (storia or "").strip() or content.strip()

        try:
            dump = pnev.pnev_dump(payload)
        except Exception:
            dump = json.dumps(payload, ensure_ascii=False)

        cur.execute(
            "UPDATE Anamnesi SET pnev_json = ?, pnev_summary = ? WHERE ID = ?",
            (dump, summary, rid),
        )
        stats["updated"] += 1

    return stats


def inpps_collect_ui(prefix: str, existing: dict | None = None) -> tuple[dict, str]:
    """
    INPPS Screening bambini (genitori) -> dict scalabile + summary.
    existing: dict precedente (pnev_json["questionari"]["inpps_screening_genitori"]) o None.
    """
    existing = existing or {}
    st.markdown("### INPPS – Screening (Genitori)")

    # --- Prima parte: Neurologica (1-29) ---
    neuro_items = [
        ("N01", "C'è qualche caso di difficoltà di apprendimento fra i genitori o le loro famiglie?"),
        ("N02", "Durante la gravidanza c'è stato qualche problema medico? (es. pressione alta, nausea eccessiva, infezioni, stress emotivo)"),
        ("N03", "È stata una gravidanza a termine, pre-termine o post-termine?"),
        ("N04", "È stata la nascita particolarmente difficoltosa o anomala in qualche senso?"),
        ("N05", "Il bimbo era particolarmente piccolo per la età gestazionale?"),
        ("N06", "L'allattamento ha presentato particolari difficoltà?"),
        ("N07", "Il bimbo soffriva di coliche?"),
        ("N08", "Il bimbo ha avuto difficoltà a dormire (frequenti risvegli, addormentamento difficile)?"),
        ("N09", "Il bimbo ha avuto difficoltà nell'alimentazione (suzione, deglutizione, masticazione, selettività)?"),
        ("N10", "Ha gattonato? (se no, ha strisciato o ha saltato la fase?)"),
        ("N11", "Ha camminato tardi rispetto ai coetanei?"),
        ("N12", "È stato lento a diventare autonomo (vestirsi, allacciarsi, usare posate)?"),
        ("N13", "È goffo / inciampa spesso?"),
        ("N14", "Ha difficoltà con equilibrio (bicicletta, saltare, stare su un piede)?"),
        ("N15", "Ha difficoltà a prendere / lanciare / colpire una palla?"),
        ("N16", "Ha difficoltà con coordinazione fine (scrittura, forbici, puzzle)?"),
        ("N17", "Ha difficoltà a stare seduto fermo a lungo?"),
        ("N18", "È facilmente distraibile?"),
        ("N19", "È impulsivo / agisce senza riflettere?"),
        ("N20", "Ha difficoltà a seguire istruzioni (specialmente in sequenza)?"),
        ("N21", "Ha difficoltà a organizzare i compiti / pianificare?"),
        ("N22", "Ha difficoltà di lettura / comprensione del testo?"),
        ("N23", "Ha difficoltà di scrittura / ortografia?"),
        ("N24", "Ha difficoltà a copiare dalla lavagna?"),
        ("N25", "Ha difficoltà con matematica / calcolo?"),
        ("N26", "Ha difficoltà a ricordare ciò che ha letto/ascoltato?"),
        ("N27", "Ha difficoltà nelle relazioni con i pari (amicizie, integrazione)?"),
        ("N28", "Si frustra facilmente / scatti emotivi?"),
        ("N29", "Se c'è un rumore o movimento inaspettato, si spaventa facilmente?"),
    ]

    # NOTE: le domande aperte del modulo cartaceo vengono raccolte qui:
    diag_pregresse = st.text_area(
        "Diagnosi pregresse (se presenti: dislessia, disprassia, ADHD, ecc.)",
        value=str(existing.get("free_text", {}).get("diagnosi_pregresse", "")),
        key=f"{prefix}_diag"
    )

    st.caption("Spunta le voci che descrivono tuo figlio/a.")
    neuro_checked = {}
    with st.expander("Prima parte – Neurologica / sviluppo / scuola (spunte)", expanded=True):
        for code, label in neuro_items:
            neuro_checked[code] = st.checkbox(
                label,
                value=bool(existing.get("items", {}).get(code, False)),
                key=f"{prefix}_{code}",
            )

    # --- Seconda parte: Nutrizione ---
    gi_opts = ["Colica", "Dolori addominali o aerofagia", "Frequenza anomala movimenti intestinali", "Stitichezza ricorrente", "Diarrea"]
    skin_opts = ["Eczema", "Zone secche in viso o braccia", "“Pelle di gallina” su braccia/cosce", "Dermatite", "Altro"]
    ent_opts = ["Ulcere sulla bocca", "Respirazione difficoltosa", "Tonsillite", "Dolori di orecchie", "Sinusite", "Muco persistente", "Russa", "Respirazione con la bocca", "Febbre da fieno (rinite allergica)"]
    asthma_triggers = ["Esercizio", "Infezioni", "Polvere", "Muffa", "Animali", "Alimenti", "Altro"]
    with st.expander("Seconda parte – Nutrizione / salute (spunte)", expanded=False):
        nutr = existing.get("nutrizione", {}) or {}
        st.markdown("**Problemi gastro-intestinali**")
        gi_sel = {opt: st.checkbox(opt, value=bool(nutr.get("gastro", {}).get(opt, False)), key=f"{prefix}_GI_{opt}") for opt in gi_opts}

        st.markdown("**Problemi di pelle**")
        skin_sel = {opt: st.checkbox(opt, value=bool(nutr.get("pelle", {}).get(opt, False)), key=f"{prefix}_SK_{opt}") for opt in skin_opts}
        skin_altro = st.text_input("Altro (pelle) – specificare", value=str(nutr.get("pelle_altro", "")), key=f"{prefix}_SK_altro_txt")

        st.markdown("**Orecchio, Naso e Gola**")
        ent_sel = {opt: st.checkbox(opt, value=bool(nutr.get("orlg", {}).get(opt, False)), key=f"{prefix}_ENT_{opt}") for opt in ent_opts}

        st.markdown("**Asma – indotto da**")
        asthma_sel = {opt: st.checkbox(opt, value=bool(nutr.get("asma", {}).get(opt, False)), key=f"{prefix}_AS_{opt}") for opt in asthma_triggers}
        asma_altro = st.text_input("Altro (asma) – specificare", value=str(nutr.get("asma_altro", "")), key=f"{prefix}_AS_altro_txt")

        sete = st.checkbox("Sete particolarmente esagerata?", value=bool(nutr.get("sete_esagerata", False)), key=f"{prefix}_sete")

    # --- Terza parte: Udito (Madaule) ---
    dev_hist = [
        ("U_H01", "C'è stato un ritardo nello sviluppo motorio?"),
        ("U_H02", "C'è stato un ritardo nello sviluppo del linguaggio?"),
        ("U_H03", "Otite di ripetizione?"),
        ("U_H04", "Sospetti di difficoltà uditive con accertamenti?"),
    ]
    ascolto_ric = [
        ("U_R01", "Brevi tempi di attenzione"),
        ("U_R02", "Distraibilità"),
        ("U_R03", "Ipersensibile ai suoni"),
        ("U_R04", "Mal intende le domande"),
        ("U_R05", "Confonde parole simili / necessita spesso ripetizioni"),
        ("U_R06", "Incapace di seguire ordini in sequenza"),
    ]
    energia = [
        ("U_E01", "Stanchezza alla fine della giornata"),
        ("U_E02", "Iperattività"),
        ("U_E03", "Tendenze depressive"),
    ]
    espressivo = [
        ("U_X01", "Voce piatta e monotona"),
        ("U_X02", "Discorso dubitativo"),
        ("U_X03", "Scarso vocabolario"),
        ("U_X04", "Povera costruzione delle frasi"),
        ("U_X05", "Incapacità a cantare intonato"),
        ("U_X06", "Confusione o inversione di lettere"),
        ("U_X07", "Scarsa comprensione della lettura"),
        ("U_X08", "Povera lettura ad alta voce"),
        ("U_X09", "Povera ortografia"),
    ]
    sociale = [
        ("U_S01", "Scarsa tollerabilità per la frustrazione"),
        ("U_S02", "Povera immagine di sé"),
        ("U_S03", "Difficoltà a fare amici"),
        ("U_S04", "Tendenza a rinchiudersi / evitare gli altri"),
        ("U_S05", "Scarsa motivazione / disinteresse nei compiti scolastici"),
        ("U_S06", "Immaturità"),
        ("U_S07", "Irritabilità"),
        ("U_S08", "Timidezza"),
    ]
    with st.expander("Terza parte – Udito (Madaule) (spunte)", expanded=False):
        ud = existing.get("udito", {}) or {}
        st.markdown("**Storia dello sviluppo**")
        for code, label in dev_hist:
            neuro_checked[code] = st.checkbox(label, value=bool(existing.get("items", {}).get(code, False)), key=f"{prefix}_{code}")

        st.markdown("**Ascolto ricettivo (esterno)**")
        for code, label in ascolto_ric:
            neuro_checked[code] = st.checkbox(label, value=bool(existing.get("items", {}).get(code, False)), key=f"{prefix}_{code}")

        st.markdown("**Livello di energia**")
        for code, label in energia:
            neuro_checked[code] = st.checkbox(label, value=bool(existing.get("items", {}).get(code, False)), key=f"{prefix}_{code}")

        st.markdown("**Ascolto espressivo (interno)**")
        for code, label in espressivo:
            neuro_checked[code] = st.checkbox(label, value=bool(existing.get("items", {}).get(code, False)), key=f"{prefix}_{code}")

        st.markdown("**Comportamento e integrazione sociale**")
        for code, label in sociale:
            neuro_checked[code] = st.checkbox(label, value=bool(existing.get("items", {}).get(code, False)), key=f"{prefix}_{code}")

    # Build structured result
    n_neuro = sum(1 for k,v in neuro_checked.items() if k.startswith("N") and v)
    n_udito = sum(1 for k,v in neuro_checked.items() if k.startswith("U_") and v)

    nutr_res = {
        "gastro": {k: bool(v) for k,v in locals().get("gi_sel", {}).items()},
        "pelle": {k: bool(v) for k,v in locals().get("skin_sel", {}).items()},
        "pelle_altro": (locals().get("skin_altro") or "").strip(),
        "orlg": {k: bool(v) for k,v in locals().get("ent_sel", {}).items()},
        "asma": {k: bool(v) for k,v in locals().get("asthma_sel", {}).items()},
        "asma_altro": (locals().get("asma_altro") or "").strip(),
        "sete_esagerata": bool(locals().get("sete", False)),
    }

    # counts
    nutr_count = 0
    for group in ("gastro","pelle","orlg","asma"):
        nutr_count += sum(1 for _,v in nutr_res.get(group, {}).items() if v)
    nutr_count += 1 if nutr_res.get("sete_esagerata") else 0

    result = {
        "version": "inpps01it",
        "mode": "genitori",
        "date": date.today().isoformat(),
        "positivi": {"neurologica_scuola": int(n_neuro), "nutrizione": int(nutr_count), "udito_madaule": int(n_udito)},
        "items": {k: bool(v) for k,v in neuro_checked.items()},
        "nutrizione": nutr_res,
        "free_text": {"diagnosi_pregresse": (diag_pregresse or "").strip()},
    }

    cutoff = _inpps_cutoff()
    totale = int(n_neuro) + int(nutr_count) + int(n_udito)
    flag = totale >= cutoff

    # Salva interpretazione (screening, non diagnosi)
    result["screening"] = {
        "cutoff": int(cutoff),
        "totale_positivi": int(totale),
        "flag_possibile_immaturita_neuromotoria": bool(flag),
        "nota": "Criterio operativo di screening (protocollo PNEV/INPPS). Richiede conferma clinica diretta.",
    }

    # Semaforo in UI
    if flag:
        st.warning(
            f"⚠️ Screening INPPS: {totale} positivi (cut-off ≥ {cutoff}) → possibile immaturità neuromotoria. "
            "Richiede conferma con valutazione clinica diretta."
        )
    else:
        st.success(f"✅ Screening INPPS: {totale} positivi (cut-off ≥ {cutoff}) → nessun alert da screening.")

    summary = (
        f"INPPS genitori: Neurologica/Scuola {n_neuro} • Nutrizione {nutr_count} • Udito {n_udito} "
        f"(Totale {totale}, cut-off ≥ {cutoff})"
    )
    if flag:
        summary += " → possibile immaturità neuromotoria (screening)."
    else:
        summary += "."
    return result, summary


if APP_MODE == "test":
    debug_secrets_auth()
if APP_MODE == "test":
    st.warning("⚠️ MODALITÀ TEST — database separato (Neon TEST).")
from datetime import date, datetime
from typing import Optional, Dict
from letterhead_pdf import build_pdf_with_letterhead
from pdf_templates import build_pdf
# A5

# A4 2×A5

import os
import io
import urllib.parse
import csv
from functools import lru_cache
import math  # <-- aggiungi questa riga se non c'è
import textwrap  # per andare a capo nel referto

# PDF (referti e prescrizioni A4/A5)

# ---- PRINT HELPERS (image background + clean prescription table) ----
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

def _safe_str(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    return s

def _blob_to_bytes(v):
    """Converte BLOB/bytea da SQLite/Postgres in bytes."""
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    # psycopg2 può restituire memoryview
    try:
        if isinstance(v, memoryview):
            return v.tobytes()
    except Exception:
        pass
    return None


def _fmt_num(x) -> str:
    if x is None:
        return ""
    try:
        # keep sign and 2 decimals for floats
        if isinstance(x, (int,)):
            return f"{x:d}"
        xf = float(x)
        return f"{xf:+.2f}"
    except Exception:
        return _safe_str(x)

def _find_bg_image(page_kind: str, variant: str) -> str | None:
    """
    Finds a background image inside common asset folders.
    page_kind: 'a4' or 'a5'
    variant: 'with_cirillo' or 'no_cirillo'
    """
    candidates = []

    # preferred canonical names
    base_names = [
        f"{page_kind}_{variant}",
        f"letterhead_{page_kind}_{variant}",
        f"prescrizione_{page_kind}_{variant}",
    ]
    exts = [".png", ".jpg", ".jpeg", ".webp"]

    # common folders
    folders = [
        "assets/print_bg",
        "assets/print",
        "assets",
        "assets/templates",   # just in case you put them here
    ]

    for folder in folders:
        for bn in base_names:
            for ext in exts:
                candidates.append(os.path.join(folder, bn + ext))

    # also accept your specific filenames (legacy)
    legacy = []
    if page_kind == "a4":
        legacy += [
            "assets/print_bg/CARATA INTESTAT THE ORGANISMA4.jpeg",
            "assets/CARATA INTESTAT THE ORGANISMA4.jpeg",
        ]
    if page_kind == "a5" and variant == "no_cirillo":
        legacy += [
            "assets/print_bg/PRESCRIZIONI THE ORGANISMAA5_no cirillo.png",
            "assets/PRESCRIZIONI THE ORGANISMAA5_no cirillo.png",
        ]
    candidates += legacy

    for p in candidates:
        if os.path.exists(p):
            return p

    # fallback: if with_cirillo missing, try no_cirillo; and vice versa
    if variant == "with_cirillo":
        return _find_bg_image(page_kind, "no_cirillo")
    return _find_bg_image(page_kind, "with_cirillo") if variant == "no_cirillo" else None

def _draw_bg_image_fullpage(c: canvas.Canvas, page_w: float, page_h: float, img_path: str | None):
    if not img_path:
        return
    try:
        img = ImageReader(img_path)
        iw, ih = img.getSize()
        scale = min(page_w / iw, page_h / ih)
        dw, dh = iw * scale, ih * scale
        x = (page_w - dw) / 2
        y = (page_h - dh) / 2
        c.drawImage(img, x, y, width=dw, height=dh, mask="auto")
    except Exception:
        # fail silently: no background
        return


def _draw_tabo_semicircle(c: canvas.Canvas, cx: float, cy: float, r: float, label: str):
    """Disegna semicerchio TABO 180→0 con tick principali e label."""
    c.saveState()
    c.setLineWidth(1)
    # arco superiore (0→180)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # tick ogni 30° (più lunghi ogni 60°)
    for deg in range(0, 181, 10):
        rad = math.radians(deg)
        x1 = cx + r * math.cos(rad)
        y1 = cy + r * math.sin(rad)
        tick = 3*mm if deg % 30 == 0 else 1.8*mm
        if deg % 60 == 0:
            tick = 4*mm
        x2 = cx + (r - tick) * math.cos(rad)
        y2 = cy + (r - tick) * math.sin(rad)
        c.line(x2, y2, x1, y1)

    # labels principali
    c.setFont("Helvetica", 8)
    c.drawString(cx - r - 12*mm, cy + 1*mm, "180")
    c.drawCentredString(cx, cy + r + 3*mm, "90")
    c.drawString(cx + r + 4*mm, cy + 1*mm, "0")

    # label occhio sotto
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - r - 6*mm, label)
    c.restoreState()


def _draw_axis_arrow(c: canvas.Canvas, cx: float, cy: float, r: float, axis_deg, enabled: bool):
    """Disegna freccia direzione asse cilindro su TABO. axis_deg 0..180."""
    if not enabled:
        return
    try:
        ax = int(axis_deg)
    except Exception:
        return
    if ax < 0 or ax > 180:
        return

    c.saveState()
    c.setLineWidth(1.2)
    rad = math.radians(ax)
    x2 = cx + (r - 2*mm) * math.cos(rad)
    y2 = cy + (r - 2*mm) * math.sin(rad)
    c.line(cx, cy, x2, y2)

    # arrow head
    head = 4*mm
    ang1 = rad + math.radians(155)
    ang2 = rad - math.radians(155)
    c.line(x2, y2, x2 + head*math.cos(ang1), y2 + head*math.sin(ang1))
    c.line(x2, y2, x2 + head*math.cos(ang2), y2 + head*math.sin(ang2))
    c.restoreState()

def _draw_prescrizione_clean_table(c: canvas.Canvas, page_w: float, page_h: float, dati: dict, top_offset_mm: float = 60):
    """
    Clean layout (no boxes): writes a readable table with SF/CIL/AX for OD/OS:
    Lontano / Intermedio / Vicino.
    """
    left = 18 * mm
    right = page_w - 18 * mm
    y = page_h - top_offset_mm * mm  # below header line

    # marker di debug: posizione inizio stampa
    c.saveState(); c.setFont('Helvetica', 7); c.drawString(left-8*mm, y+2, '1'); c.restoreState()

    c.setFont("Helvetica", 11)
    c.drawString(left, y, f"Sig.: {_safe_str(dati.get('paziente',''))}")
    c.drawRightString(right, y, f"Data: {_safe_str(dati.get('data',''))}")
    y -= 18*mm

    # headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "PRESCRIZIONE OCCHIALI")
    y -= 7 * mm

    # --- TABO semicircles + axis arrow (asse cilindro) ---
    # Usare asse del LONTANO; freccia solo se CIL != 0
    r_tabo = 24 * mm
    # Spazio extra: evita che Nome/Data coprano i semicerchi
    y -= 20 * mm
    cy_tabo = y - 4 * mm
    cx_od = left + 55 * mm
    cx_os = left + 135 * mm

    _draw_tabo_semicircle(c, cx_od, cy_tabo, r_tabo, "Occhio Destro")
    _draw_tabo_semicircle(c, cx_os, cy_tabo, r_tabo, "Occhio Sinistro")

    # Scegli l'asse da disegnare sui TABO.
    # Regola: usa prima il rigo che ha CIL diverso da 0; se nessuno, usa il primo asse diverso da 0 (se presente).
    def _pick_axis_and_cyl(prefix: str):
        cand = [
            ("lon", dati.get(f"{prefix}_lon_cil"), dati.get(f"{prefix}_lon_ax")),
            ("int", dati.get(f"{prefix}_int_cil"), dati.get(f"{prefix}_int_ax")),
            ("vic", dati.get(f"{prefix}_vic_cil"), dati.get(f"{prefix}_vic_ax")),
        ]
        # 1) priorità: CIL != 0
        for _, cil, ax in cand:
            try:
                if float(cil or 0) != 0.0 and ax is not None and str(ax).strip() != "":
                    return ax, cil
            except Exception:
                pass
        # 2) fallback: asse != 0 (anche se CIL=0) — utile se vuoi indicare comunque la direzione di montaggio
        for _, cil, ax in cand:
            try:
                if ax is not None and str(ax).strip() != "":
                    return ax, cil
            except Exception:
                if ax is not None and str(ax).strip() != "":
                    return ax, cil
        return None, None

    od_ax_pick, od_cil_pick = _pick_axis_and_cyl("od")
    os_ax_pick, os_cil_pick = _pick_axis_and_cyl("os")

    _draw_axis_arrow(c, cx_od, cy_tabo, r_tabo, od_ax_pick, enabled=(od_ax_pick is not None))
    _draw_axis_arrow(c, cx_os, cy_tabo, r_tabo, os_ax_pick, enabled=(os_ax_pick is not None))

    # spazio dopo TABO
    y -= 2 * r_tabo + 10 * mm

    # columns
    col_label = left
    col_od_sf  = left + 28*mm
    col_od_cil = left + 46*mm
    col_od_ax  = left + 64*mm

    col_os_sf  = left + 112*mm
    col_os_cil = left + 130*mm
    col_os_ax  = left + 148*mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_od_sf - 10*mm, y, "OD")
    c.drawString(col_os_sf - 10*mm, y, "OS")
    y -= 5 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_label, y, "")
    c.drawString(col_od_sf,  y, "SF")
    c.drawString(col_od_cil, y, "CIL")
    c.drawString(col_od_ax,  y, "AX")
    c.drawString(col_os_sf,  y, "SF")
    c.drawString(col_os_cil, y, "CIL")
    c.drawString(col_os_ax,  y, "AX")
    y -= 6 * mm

    def row(label, od_sf, od_cil, od_ax, os_sf, os_cil, os_ax):
        nonlocal y
        c.setFont("Helvetica", 9)
        c.drawString(col_label, y, label)
        c.drawRightString(col_od_sf + 10*mm, y, _fmt_num(od_sf))
        c.drawRightString(col_od_cil + 10*mm, y, _fmt_num(od_cil))
        c.drawRightString(col_od_ax + 10*mm, y, _safe_str(od_ax))

        c.drawRightString(col_os_sf + 10*mm, y, _fmt_num(os_sf))
        c.drawRightString(col_os_cil + 10*mm, y, _fmt_num(os_cil))
        c.drawRightString(col_os_ax + 10*mm, y, _safe_str(os_ax))
        y -= 6 * mm

    row("Lontano",
        dati.get("od_lon_sf"), dati.get("od_lon_cil"), dati.get("od_lon_ax"),
        dati.get("os_lon_sf"), dati.get("os_lon_cil"), dati.get("os_lon_ax"))
    row("Intermedio",
        dati.get("od_int_sf"), dati.get("od_int_cil"), dati.get("od_int_ax"),
        dati.get("os_int_sf"), dati.get("os_int_cil"), dati.get("os_int_ax"))
    row("Vicino",
        dati.get("od_vic_sf"), dati.get("od_vic_cil"), dati.get("od_vic_ax"),
        dati.get("os_vic_sf"), dati.get("os_vic_cil"), dati.get("os_vic_ax"))

    y -= 8 * mm

    # Lenti / trattamenti
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Lenti consigliate / Trattamenti")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    lenti = ", ".join(dati.get("lenti", []) or [])
    if lenti:
        c.drawString(left, y, f"Lenti: {lenti}")
        y -= 5 * mm
    altri = _safe_str(dati.get("altri_trattamenti", ""))
    if altri:
        c.drawString(left, y, f"Altri trattamenti: {altri}")
        y -= 5 * mm

    note = _safe_str(dati.get("note", ""))
    if note:
        y -= 2 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "Note:")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        max_chars = 110 if page_w >= A4[0] else 70
        for i in range(0, len(note), max_chars):
            c.drawString(left, y, note[i:i+max_chars])
            y -= 5 * mm

def _prescrizione_pdf_imagebg(page_size, page_kind: str, con_cirillo: bool, dati: dict) -> bytes:
    variant = "with_cirillo" if con_cirillo else "no_cirillo"
    bg = _find_bg_image(page_kind, variant)
    page_w, page_h = page_size
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page_size)
    _draw_bg_image_fullpage(c, page_w, page_h, bg)
    # top offset: A5 has less vertical space
    top_offset = 72 if page_kind == "a4" else 62
    _draw_prescrizione_clean_table(c, page_w, page_h, dati, top_offset_mm=top_offset)
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()

try:
    from reportlab.lib.pagesizes import A4, A5, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# PDF merge (template letterhead)
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf._page import PageObject
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def _make_overlay_pdf_pagesize(pagesize, draw_fn):
    """Crea un PDF overlay (una pagina) con ReportLab per un pagesize arbitrario."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)
    w, h = pagesize
    draw_fn(c, w, h)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

@lru_cache(maxsize=4)
def _build_a4_landscape_2up_template_bytes(variant: str) -> bytes:
    """Crea un template A4 landscape con 2 template A5 affiancati (sinistra+destra)."""
    if not PYPDF_AVAILABLE:
        raise RuntimeError("pypdf non disponibile")

    a4_w, a4_h = landscape(A4)
    a5_w, a5_h = A5

    a5_path = "assets/letterhead/a5_with_cirillo.pdf" if variant == "with_cirillo" else "assets/letterhead/a5_no_cirillo.pdf"
    reader = PdfReader(a5_path)
    a5_page = reader.pages[0]

    out_page = PageObject.create_blank_page(width=a4_w, height=a4_h)

    # due pannelli A5 affiancati
    out_page.merge_translated_page(a5_page, tx=0, ty=0)
    out_page.merge_translated_page(a5_page, tx=a5_w, ty=0)

    writer = PdfWriter()
    writer.add_page(out_page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


# -----------------------------
# -----------------------------
# Configurazione accesso (login semplice)
# - In locale: fallback admin/admin123
# - In Cloud: usa Secrets [auth] oppure [users]
# -----------------------------

APP_VERSION = "UNIFIED-SQLITE-NEON-2026-01-31"

def _safe_secrets():
    try:
        return getattr(st, "secrets", {}) or {}
    except Exception:
        return {}

def load_users_dynamic() -> dict:
    """Carica credenziali da secrets (Streamlit Cloud o locale), con fallback."""
    sec = _safe_secrets()

    # Multi-utente: [users]
    try:
        users = sec.get("users", {})
        if isinstance(users, dict) and users:
            return {str(k).strip(): str(v).strip() for k, v in users.items()}
    except Exception:
        pass

    # Singolo utente: [auth]
    try:
        auth = sec.get("auth", {})
        if isinstance(auth, dict):
            u = str(auth.get("username", "")).strip()
            p = str(auth.get("password", "")).strip()
            if u and p:
                return {u: p}
    except Exception:
        pass

    # Fallback locale
    return {"admin": "admin123"}

# =========================
# AUTH (DB-based) + RBAC
# =========================
import secrets as _secrets_mod

PBKDF2_ITERS = 260_000

def _pwd_hash(pw: str, salt_b64: str | None = None, iters: int = PBKDF2_ITERS) -> str:
    """Hash password with PBKDF2-HMAC-SHA256.
    Format: pbkdf2_sha256$<iters>$<salt_b64>$<hash_b64>
    NOTE: Imports are inside the function to avoid NameError if global imports change.
    """
    import base64
    import hashlib
    import secrets as _secrets_mod_local

    if salt_b64 is None:
        salt = _secrets_mod_local.token_bytes(16)
        salt_b64 = base64.b64encode(salt).decode("utf-8")
    else:
        salt = base64.b64decode(salt_b64.encode("utf-8"))

    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, int(iters), dklen=32)
    hash_b64 = base64.b64encode(dk).decode("utf-8")
    return f"pbkdf2_sha256${int(iters)}${salt_b64}${hash_b64}"

def _pwd_verify(pw: str, stored: str) -> bool:
    """Verify PBKDF2 password hash."""
    import hmac
    try:
        algo, iters_s, salt_b64, _hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        candidate = _pwd_hash(pw, salt_b64=salt_b64, iters=iters)
        return hmac.compare_digest(candidate, stored)
    except Exception:
        return False
        iters = int(iters_s)
        candidate = _pwd_hash(pw, salt_b64=salt_b64, iters=iters)
        return hmac.compare_digest(candidate, stored)
    except Exception:
        return False

def _breakglass_enabled() -> bool:
    """Emergency login toggle (TEST only)."""
    try:
        if str(st.secrets.get("APP_MODE", "prod")).lower().strip() != "test":
            return False
    except Exception:
        return False
    bg = st.secrets.get("breakglass", {})
    return bool(bg.get("ENABLED", False))

def _breakglass_check(username: str, password: str) -> bool:
    bg = st.secrets.get("breakglass", {})
    return username == bg.get("USERNAME") and password == bg.get("PASSWORD")


def ensure_auth_schema(conn):
    """Create auth tables if missing (safe to call multiple times)."""
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_users (
          id BIGSERIAL PRIMARY KEY,
          username TEXT UNIQUE NOT NULL,
          email TEXT,
          password_hash TEXT NOT NULL,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          last_login_at TIMESTAMPTZ
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_roles (
          id BIGSERIAL PRIMARY KEY,
          name TEXT UNIQUE NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_user_roles (
          user_id BIGINT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
          role_id BIGINT NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,
          PRIMARY KEY (user_id, role_id)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_audit_log (
          id BIGSERIAL PRIMARY KEY,
          ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          user_id BIGINT REFERENCES auth_users(id) ON DELETE SET NULL,
          action TEXT NOT NULL,
          entity TEXT,
          entity_id TEXT,
          meta JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """)
        cur.execute("""
        INSERT INTO auth_roles(name) VALUES
        ('admin'),('vision'),('osteo'),('segreteria'),('clinico')
        ON CONFLICT (name) DO NOTHING;
        """)
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass

def _audit(conn, user_id: int | None, action: str, entity: str | None = None, entity_id: str | None = None, meta: dict | None = None):
    """Write an audit log entry.
    Safe for break-glass sessions (user_id < 1) by storing NULL user_id (allowed by FK).
    Imports json locally to avoid NameError.
    """
    import json

    meta = meta or {}

    # break-glass / invalid user id -> NULL
    try:
        if user_id is not None and int(user_id) < 1:
            user_id = None
    except Exception:
        user_id = None

    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO auth_audit_log(user_id, action, entity, entity_id, meta) VALUES (%s,%s,%s,%s,%s::jsonb)",
            (user_id, action, entity, entity_id, json.dumps(meta)),
        )
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

def _get_user_by_username(conn, username: str):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, username, email, password_hash, is_active, must_change_password
            FROM auth_users
            WHERE username = %s
        """, (username,))
        return cur.fetchone()
    finally:
        try: cur.close()
        except Exception: pass

def _get_roles_for_user(conn, user_id: int) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT r.name
            FROM auth_user_roles ur
            JOIN auth_roles r ON r.id = ur.role_id
            WHERE ur.user_id = %s
            ORDER BY r.name
        """, (user_id,))
        rows = cur.fetchall() or []
        return [r[0] for r in rows]
    finally:
        try: cur.close()
        except Exception: pass

def current_user():
    return st.session_state.get("user")

def is_admin() -> bool:
    u = current_user() or {}
    return "admin" in (u.get("roles") or [])

def can(role: str) -> bool:
    u = current_user() or {}
    roles = set(u.get("roles") or [])
    return ("admin" in roles) or (role in roles)

def _ensure_first_admin(conn) -> bool:
    """If no users exist yet, allow creating the first admin from UI."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM auth_users;")
        n = cur.fetchone()[0]
    finally:
        try: cur.close()
        except Exception: pass

    if n and int(n) > 0:
        return True  # already bootstrapped

    st.warning("⚠️ Nessun utente presente. Crea il primo amministratore.")
    username = st.text_input("Username admin iniziale", value="admin")
    pw1 = st.text_input("Password admin", type="password")
    pw2 = st.text_input("Conferma password", type="password")
    if st.button("Crea admin"):
        if not username.strip() or not pw1:
            st.error("Username e password sono obbligatori.")
            return False
        if pw1 != pw2:
            st.error("Le password non coincidono.")
            return False

        ph = _pwd_hash(pw1)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO auth_users(username, email, password_hash, must_change_password) VALUES (%s,%s,%s,%s) RETURNING id",
                (username.strip(), None, ph, False),
            )
            uid = cur.fetchone()[0]

            # assegna ruolo admin
            cur.execute("SELECT id FROM auth_roles WHERE name = 'admin'")
            rid = cur.fetchone()[0]
            cur.execute("INSERT INTO auth_user_roles(user_id, role_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, rid))

            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            st.error(f"Errore creazione admin: {e}")
            return False
        finally:
            try: cur.close()
            except Exception: pass

        _audit(conn, uid, "BOOTSTRAP_ADMIN", meta={"username": username.strip()})
        st.success("Admin creato. Ora effettua il login.")
        st.rerun()
    return False

def login(get_conn) -> bool:
    """Login su DB con ruoli."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None

    if st.session_state["logged_in"] and st.session_state["user"]:
        u = st.session_state["user"]
        st.sidebar.markdown(f"👤 Utente: **{u['username']}**")
        st.sidebar.caption("Ruoli: " + (", ".join(u.get("roles", [])) or "(nessuno)"))
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state["user"] = None
            st.rerun()
        return True

    st.title("The Organism – Login")
    st.caption(f"Versione: {APP_VERSION}")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    conn = get_conn()
    # Clear any aborted transaction state from previous operations
    try:
        conn.rollback()
    except Exception:
        pass
    ensure_auth_schema(conn)

    # bootstrap primo admin se non ci sono utenti
    if not _ensure_first_admin(conn):
        return False

    if st.button("Accedi"):

        u_in = (username or "").strip()
        p_in = password or ""
        if _breakglass_enabled() and _breakglass_check(u_in, p_in):
            st.session_state["logged_in"] = True
            st.session_state["user"] = {
                "id": None,
                "username": u_in,
                "email": None,
                "roles": ["admin"],
                "must_change_password": False,
                "breakglass": True,
            }
            try:
                _audit(conn, None, "LOGIN_BREAKGLASS", meta={"username": u_in})
            except Exception:
                pass
            st.warning("✅ Accesso di emergenza attivo (break-glass). Disattivalo nei Secrets dopo aver sistemato gli utenti.")
            st.rerun()
        row = _get_user_by_username(conn, username.strip())
        if not row:
            st.error("Credenziali errate.")
            _audit(conn, None, "LOGIN_FAIL", meta={"username": username.strip()})
            return False

        user_id, uname, email, pwd_hash, is_active, must_change = row
        if not is_active:
            st.error("Utente disattivato.")
            _audit(conn, user_id, "LOGIN_FAIL_DISABLED", meta={})
            return False

        if not _pwd_verify(password, pwd_hash):
            st.error("Credenziali errate.")
            _audit(conn, user_id, "LOGIN_FAIL", meta={})
            return False

        roles = _get_roles_for_user(conn, user_id)

        # update last login
        cur = conn.cursor()
        try:
            cur.execute("UPDATE auth_users SET last_login_at = NOW() WHERE id = %s", (user_id,))
            conn.commit()
        finally:
            try: cur.close()
            except Exception: pass

        _audit(conn, user_id, "LOGIN_SUCCESS", meta={"roles": roles})

        st.session_state["logged_in"] = True
        st.session_state["user"] = {
            "id": int(user_id),
            "username": str(uname),
            "email": email,
            "roles": roles,
            "must_change_password": bool(must_change),
        }
        st.success("Accesso effettuato.")
        st.rerun()

    return False

def ui_gestione_utenti(get_conn):
    """UI admin: crea utenti/ruoli, reset password e attiva/disattiva."""
    if not is_admin():
        st.error("Accesso negato: solo admin.")
        return

    conn = get_conn()
    ensure_auth_schema(conn)

    st.header("Utenti / Ruoli")

    # Crea utente
    with st.expander("➕ Crea nuovo utente", expanded=True):
        new_u = st.text_input("Nuovo username")
        new_email = st.text_input("Email (opzionale)")
        new_pw = st.text_input("Password iniziale", type="password")
        roles = st.multiselect("Ruoli", ["admin","vision","osteo","segreteria","clinico"], default=["clinico"])
        must_change = st.checkbox("Obbliga cambio password al primo accesso", value=True)

        if st.button("Crea utente"):
            if not new_u.strip() or not new_pw:
                st.warning("Username e password obbligatori.")
            else:
                ph = _pwd_hash(new_pw)
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO auth_users(username, email, password_hash, must_change_password) VALUES (%s,%s,%s,%s) RETURNING id",
                        (new_u.strip(), (new_email.strip() or None), ph, must_change),
                    )
                    uid = cur.fetchone()[0]

                    for r in roles:
                        cur.execute("SELECT id FROM auth_roles WHERE name=%s", (r,))
                        rid = cur.fetchone()[0]
                        cur.execute("INSERT INTO auth_user_roles(user_id, role_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, rid))

                    conn.commit()
                    try: cur.close()
                    except Exception: pass
                    _audit(conn, st.session_state["user"]["id"], "USER_CREATED", entity="auth_users", entity_id=str(uid), meta={"username": new_u.strip(), "roles": roles})
                    st.success("Utente creato.")
                    st.rerun()
                except Exception as e:
                    try: conn.rollback()
                    except Exception: pass
                    st.error(f"Errore creazione utente: {e}")

    # Lista utenti
    st.subheader("Elenco utenti")
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, email, is_active, must_change_password, last_login_at FROM auth_users ORDER BY username;")
        rows = cur.fetchall() or []
    finally:
        try: cur.close()
        except Exception: pass

    if not rows:
        st.info("Nessun utente.")
        return

    for r in rows:
        uid = int(r[0])
        uname = str(r[1])
        email = r[2]
        is_active = bool(r[3])
        must_change = bool(r[4])
        last_login = r[5]
        with st.expander(f"👤 {uname} (id {uid})", expanded=False):
            st.write({"email": email, "is_active": is_active, "must_change_password": must_change, "last_login_at": str(last_login) if last_login else None})
            # ruoli
            current_roles = _get_roles_for_user(conn, uid)
            new_roles = st.multiselect(f"Ruoli per {uname}", ["admin","vision","osteo","segreteria","clinico"], default=current_roles, key=f"roles_{uid}")

            col1, col2, col3 = st.columns(3)
            with col1:
                new_pw = st.text_input(f"Reset password ({uname})", type="password", key=f"pw_{uid}")
                if st.button(f"Imposta password", key=f"setpw_{uid}"):
                    if not new_pw:
                        st.warning("Inserisci una password.")
                    else:
                        ph = _pwd_hash(new_pw)
                        c2 = conn.cursor()
                        try:
                            c2.execute("UPDATE auth_users SET password_hash=%s, must_change_password=TRUE WHERE id=%s", (ph, uid))
                            conn.commit()
                        finally:
                            try: c2.close()
                            except Exception: pass
                        _audit(conn, st.session_state["user"]["id"], "PASSWORD_RESET", entity="auth_users", entity_id=str(uid), meta={})
                        st.success("Password aggiornata (utente obbligato a cambiarla al prossimo accesso).")
            with col2:
                if st.button("Salva ruoli", key=f"saveroles_{uid}"):
                    c3 = conn.cursor()
                    try:
                        # rimuovi e reinserisci
                        c3.execute("DELETE FROM auth_user_roles WHERE user_id=%s", (uid,))
                        for rr in new_roles:
                            c3.execute("SELECT id FROM auth_roles WHERE name=%s", (rr,))
                            rid = c3.fetchone()[0]
                            c3.execute("INSERT INTO auth_user_roles(user_id, role_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, rid))
                        conn.commit()
                    finally:
                        try: c3.close()
                        except Exception: pass
                    _audit(conn, st.session_state["user"]["id"], "ROLES_UPDATED", entity="auth_users", entity_id=str(uid), meta={"roles": new_roles})
                    st.success("Ruoli salvati.")
                    st.rerun()
            with col3:
                toggle_label = "Disattiva" if is_active else "Riattiva"
                if st.button(toggle_label, key=f"toggle_{uid}"):
                    c4 = conn.cursor()
                    try:
                        c4.execute("UPDATE auth_users SET is_active=%s WHERE id=%s", (not is_active, uid))
                        conn.commit()
                    finally:
                        try: c4.close()
                        except Exception: pass
                    _audit(conn, st.session_state["user"]["id"], "USER_TOGGLED", entity="auth_users", entity_id=str(uid), meta={"is_active": (not is_active)})
                    st.success("Stato aggiornato.")
                    st.rerun()



def _is_streamlit_cloud() -> bool:
    """Heuristic check: True when running on Streamlit Cloud."""
    try:
        # Streamlit Cloud mounts the repo under /mount/src
        if os.getcwd().startswith("/mount/src") or os.path.exists("/mount/src"):
            return True
    except Exception:
        pass
    # Fallback heuristics
    for k in ("STREAMLIT_CLOUD", "STREAMLIT_SHARING", "STREAMLIT_RUNTIME_ENV"):
        v = os.getenv(k, "")
        if str(v).lower() in ("1", "true", "yes", "cloud", "sharing"):
            return True
    return False



class _RowCI(dict):
    """Case-insensitive dict for row access, but also behaves like a sequence.

    We need BOTH:
    - row['ID'] style access (case-insensitive) for legacy SQLite-style code
    - row[0] / list(row) sequence-style access for code paths that expect tuples

    psycopg2 DictRow supports both, but we wrap it to make key access case-insensitive.
    """
    def __init__(self, mapping, seq=None):
        super().__init__(mapping or {})
        # Preserve column order so row[0] works and list(row) returns values (not keys)
        if seq is None:
            seq = list((mapping or {}).values())
        self._seq = list(seq)

    def __iter__(self):
        # Iterate VALUES (not keys) so list(row) behaves like a tuple row
        return iter(self._seq)

    def __len__(self):
        return len(self._seq)

    def __getitem__(self, key):
        # Numeric / slice access -> sequence behaviour
        if isinstance(key, (int, slice)):
            return self._seq[key]

        # Case-insensitive string key access
        if isinstance(key, str):
            if dict.__contains__(self, key):
                return dict.__getitem__(self, key)
            lk = key.lower()
            if dict.__contains__(self, lk):
                return dict.__getitem__(self, lk)
            uk = key.upper()
            if dict.__contains__(self, uk):
                return dict.__getitem__(self, uk)

        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except Exception:
            return default

class _PgCursor:

    """Cursor wrapper to:
    - translate SQLite '?' placeholders -> psycopg2 '%s'
    - return psycopg2 DictRow (supports both dict and index access)
    """
    def __init__(self, cur):
        self._cur = cur

    @staticmethod
    def _adapt_sql(sql: str) -> str:
        # naive but effective for this app: replace all '?' placeholders
        return sql.replace("?", "%s")

    def execute(self, sql, params=None):
        sql2 = self._adapt_sql(str(sql))
        try:
            if params is None:
                return self._cur.execute(sql2)
            return self._cur.execute(sql2, params)
        except Exception:
            # If a statement fails, PostgreSQL marks the transaction as aborted.
            # Roll back so subsequent statements don't hit InFailedSqlTransaction.
            try:
                self._cur.connection.rollback()
            except Exception:
                pass
            raise

    def executemany(self, sql, seq_of_params):
        sql2 = self._adapt_sql(str(sql))
        try:
            return self._cur.executemany(sql2, seq_of_params)
        except Exception:
            try:
                self._cur.connection.rollback()
            except Exception:
                pass
            raise

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        try:
            return _RowCI(dict(row), list(row))
        except Exception:
            return row

    def fetchall(self):
        rows = self._cur.fetchall()
        out = []
        for r in rows:
            try:
                out.append(_RowCI(dict(r), list(r)))
            except Exception:
                out.append(r)
        return out

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        try:
            return self._cur.close()
        except Exception:
            return None


class _PgConn:
    """Connection wrapper to emulate the minimal sqlite3 API used by the app."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        # DictCursor yields DictRow which supports both mapping and sequence access
        return _PgCursor(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

def _secrets_diagnostics():
    """Return non-sensitive diagnostics about Streamlit secrets/env.

    Non stampa mai valori sensibili (solo presenza/chiavi/lunghezze).
    """
    diag = {
        "secrets_available": False,
        "secrets_keys": [],
        "has_db_section": False,
        "db_keys": [],
        # True se esiste una delle chiavi attese e il valore non è vuoto dopo strip()
        "has_db_database_url": False,
        "db_database_url_key": None,
        "db_database_url_len": 0,
        "has_root_database_url": False,
        "root_database_url_key": None,
        "root_database_url_len": 0,
        "env_database_url": False,
        "env_database_url_len": 0,
    }

    sec = None
    try:
        sec = getattr(st, "secrets", None)
        if sec is not None:
            diag["secrets_available"] = True
            try:
                diag["secrets_keys"] = sorted(list(sec.keys()))
            except Exception:
                diag["secrets_keys"] = ["<unreadable>"]
    except Exception:
        sec = None

    # --- [db] section ---
    try:
        diag["has_db_section"] = bool(sec is not None and ("db" in sec))
    except Exception:
        diag["has_db_section"] = False

    if diag["has_db_section"]:
        try:
            db = sec.get("db", {})
            if isinstance(db, dict):
                diag["db_keys"] = sorted(list(db.keys()))
                for k in ("DATABASE_URL", "database_url", "url", "URL"):
                    v = db.get(k)
                    if v is not None:
                        s = str(v)
                        l = len(s.strip())
                        if l > 0:
                            diag["has_db_database_url"] = True
                            diag["db_database_url_key"] = k
                            diag["db_database_url_len"] = l
                            break
                        else:
                            # chiave presente ma vuota: salva info (se non già trovato nulla)
                            if diag["db_database_url_key"] is None:
                                diag["db_database_url_key"] = k
                                diag["db_database_url_len"] = 0
        except Exception:
            pass

    # --- root keys ---
    if sec is not None:
        try:
            for k in ("DATABASE_URL", "database_url"):
                v = sec.get(k)
                if v is not None:
                    s = str(v)
                    l = len(s.strip())
                    if l > 0:
                        diag["has_root_database_url"] = True
                        diag["root_database_url_key"] = k
                        diag["root_database_url_len"] = l
                        break
                    else:
                        if diag["root_database_url_key"] is None:
                            diag["root_database_url_key"] = k
                            diag["root_database_url_len"] = 0
        except Exception:
            pass

    # --- env ---
    try:
        envv = (os.getenv("DATABASE_URL", "") or os.getenv("database_url", "") or "")
        diag["env_database_url_len"] = len(envv.strip())
        diag["env_database_url"] = diag["env_database_url_len"] > 0
    except Exception:
        diag["env_database_url"] = False
        diag["env_database_url_len"] = 0

    return diag
def _get_database_url() -> str:
    """Return DATABASE_URL from Streamlit secrets or environment.
    Supports either:
      - [db] DATABASE_URL = "..."
      - DATABASE_URL = "..."  (root)
    """
    sec = _safe_secrets()

    # 1) [db].DATABASE_URL (preferred)
    try:
        dbsec = sec.get("db", {})
        if isinstance(dbsec, dict):
            for k in ("DATABASE_URL", "database_url", "url", "URL"):
                v = dbsec.get(k)
                if v:
                    return str(v).strip()
    except Exception:
        pass

    # 2) root DATABASE_URL
    try:
        for k in ("DATABASE_URL", "database_url"):
            v = sec.get(k)
            if v:
                return str(v).strip()
    except Exception:
        pass

    # 3) environment
    return (os.getenv("DATABASE_URL", "") or os.getenv("database_url", "") or "").strip()


def _normalize_db_url(u: str) -> str:
    u = (u or "").strip()
    # strip accidental surrounding quotes
    if (u.startswith('"') and u.endswith('"')) or (u.startswith("'") and u.endswith("'")):
        u = u[1:-1].strip()
    # normalize scheme
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return u

_DB_URL = _normalize_db_url(_get_database_url())
_DB_BACKEND = "postgres" if _DB_URL else "sqlite"


def _sidebar_db_indicator():
    """Mostra in sidebar quale database sta usando l'app."""
    try:
        if _is_streamlit_cloud():
            if _DB_BACKEND == "postgres" and _DB_URL:
                st.sidebar.success("🟢 DB: PostgreSQL (Neon)")
            else:
                st.sidebar.error("🔴 DB: PostgreSQL (Neon) NON configurato")
        else:
            if _DB_BACKEND == "postgres" and _DB_URL:
                st.sidebar.success("🟢 DB: PostgreSQL (Neon)")
            else:
                # locale / test
                db_path = os.getenv("SQLITE_DB_PATH", "the_organism_gestionale_TEST.db")
                st.sidebar.warning(f"🟡 DB: SQLite ({db_path})")
    except Exception:
        pass

def _require_postgres_on_cloud():
    # Mostra sempre l'indicatore, anche in caso di errore
    _sidebar_db_indicator()
    if _is_streamlit_cloud() and _DB_BACKEND != "postgres":
        st.error("❌ DATABASE_URL mancante nei Secrets: in Streamlit Cloud il gestionale richiede PostgreSQL (Neon).")
        diag = _secrets_diagnostics()
        st.write("Diagnostica Secrets (senza valori):")
        st.write({
            "secrets_available": diag.get("secrets_available"),
            "secrets_keys": diag.get("secrets_keys"),
            "has_db_section": diag.get("has_db_section"),
            "db_keys": diag.get("db_keys"),
            "has_db_database_url": diag.get("has_db_database_url"),
            "db_database_url_key": diag.get("db_database_url_key"),
            "db_database_url_len": diag.get("db_database_url_len"),
            "has_root_database_url": diag.get("has_root_database_url"),
            "root_database_url_key": diag.get("root_database_url_key"),
            "root_database_url_len": diag.get("root_database_url_len"),
            "env_database_url": diag.get("env_database_url"),
            "env_database_url_len": diag.get("env_database_url_len"),
        })
        st.write("Chiavi in [db]:", diag.get("db_keys"))
        st.write("Lunghezza DATABASE_URL (strip):", diag.get("db_database_url_len"))
        st.write("DATABASE_URL sembra postgresql:// ?", str(_safe_secrets().get("db",{}).get("DATABASE_URL","")).strip().lower().startswith("postgresql://"))
        st.info("""Apri la tua app su Streamlit Cloud → Settings → Secrets e aggiungi:

[db]
DATABASE_URL = "postgresql://...sslmode=require"

Poi premi Save e riavvia l'app (Reboot).""")
        st.stop()
def _connect_cached():
    _require_postgres_on_cloud()
    if _DB_BACKEND == "postgres":
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 non disponibile. Aggiungi psycopg2-binary a requirements.txt")

        try:
            conn = psycopg2.connect(_DB_URL)
        except Exception:
            # Non-leak diagnostics (does not print the URL)
            u = _DB_URL or ""
            st.error("❌ Errore connessione PostgreSQL (Neon). La DATABASE_URL non sembra in un formato valido per psycopg2.")
            st.write({
                "db_url_len": len(u),
                "db_url_has_whitespace": any(ch.isspace() for ch in u),
                "db_url_scheme": (u.split("://", 1)[0] if "://" in u else "<missing>"),
                "hint_1": "Verifica che sia su UNA sola riga nei Secrets (nessun a capo).",
                "hint_2": "Usa lo schema 'postgresql://'.",
                "hint_3": "Se la password contiene caratteri speciali (@ : / ? # & %), deve essere URL-encoded (es. @ -> %40).",
            })
            st.stop()

        return _PgConn(conn)

    # SQLite (locale / fallback)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection():

    return _connect_cached()

def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    if _DB_BACKEND == "sqlite":

        # Pazienti
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Pazienti (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                Cognome         TEXT NOT NULL,
                Nome            TEXT NOT NULL,
                Data_Nascita    TEXT,
                Sesso           TEXT,
                Telefono        TEXT,
                Email           TEXT,
                Indirizzo       TEXT,
                CAP             TEXT,
                Citta           TEXT,
                Provincia       TEXT,
                Codice_Fiscale  TEXT,
                Stato_Paziente  TEXT
            )
            """
        )
        # Anamnesi
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Anamnesi (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID     INTEGER NOT NULL,
                Data_Anamnesi   TEXT,
                Motivo          TEXT,
                Storia          TEXT,
                Note            TEXT,
                -- campi strutturati legacy
                Perinatale      TEXT,
                Sviluppo        TEXT,
                Scuola          TEXT,
                Emotivo         TEXT,
                Sensoriale      TEXT,
                Stile_Vita      TEXT,
                -- PNEV scalabile (JSON)
                pnev_json        TEXT,
                pnev_summary     TEXT
            )
            """
        )

        # Migrazione PNEV (SQLite) – aggiunge colonne se mancanti
        try:
            cur.execute("PRAGMA table_info(Anamnesi)")
            existing_cols = {r[1] for r in cur.fetchall()}
            mig_cols = [
                ("pnev_json", "TEXT"),
                ("pnev_summary", "TEXT"),
            ]
            for col, typ in mig_cols:
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE Anamnesi ADD COLUMN {col} {typ}")
        except Exception:
            pass

        # Valutazioni visive / oculistiche
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Valutazioni_Visive (
                ID                  INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID         INTEGER NOT NULL,
                Data_Valutazione    TEXT,
                Tipo_Visita         TEXT,
                Professionista      TEXT,

                Anamnesi            TEXT,

                Acuita_Nat_OD       TEXT, Acuita_Nat_OS       TEXT, Acuita_Nat_OO       TEXT,
                Acuita_Corr_OD      TEXT, Acuita_Corr_OS      TEXT, Acuita_Corr_OO      TEXT,

                OD_SF_OBJ           REAL, OD_CIL_OBJ          REAL, OD_AX_OBJ           INTEGER,
                OS_SF_OBJ           REAL, OS_CIL_OBJ          REAL, OS_AX_OBJ           INTEGER,

                OD_SF_SOGG          REAL, OD_CIL_SOGG         REAL, OD_AX_SOGG          INTEGER,
                OS_SF_SOGG          REAL, OS_CIL_SOGG         REAL, OS_AX_SOGG          INTEGER,

                OD_K1_MM            REAL, OD_K1_D             REAL,
                OD_K2_MM            REAL, OD_K2_D             REAL,
                OS_K1_MM            REAL, OS_K1_D             REAL,
                OS_K2_MM            REAL, OS_K2_D             REAL,

                Tonometria_OD       REAL,
                Tonometria_OS       REAL,

                Motilita            TEXT,
                Cover_Test          TEXT,
                Stereopsi           TEXT,
                PPC                 REAL,

                Ishihara            TEXT,
                Pachimetria_OD      REAL,
                Pachimetria_OS      REAL,
                Fondo               TEXT,
                Campo_Visivo        TEXT,
                OCT                 TEXT,
                Topografia          TEXT,

                Costo               REAL DEFAULT 0,
                Pagato              INTEGER DEFAULT 0,
                Stato               TEXT DEFAULT 'BOZZA',

                Esame               TEXT,
                Conclusioni         TEXT,
                Note                TEXT
            )
            """
        )

        
        # Migrazione campi Esame Obiettivo (SQLite) – aggiunge colonne se mancanti
        try:
            cur.execute("PRAGMA table_info(Valutazioni_Visive)")
            existing_cols = {r[1] for r in cur.fetchall()}
            eo_cols = [
                ("Cornea", "TEXT"),
                ("Camera_Anteriore", "TEXT"),
                ("Cristallino", "TEXT"),
                ("Congiuntiva_Sclera", "TEXT"),
                ("Iride_Pupilla", "TEXT"),
                ("Vitreo", "TEXT"),
            ]
            for col, typ in eo_cols:
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE Valutazioni_Visive ADD COLUMN {col} {typ}")
        except Exception:
            # Non bloccare l'avvio se la migrazione fallisce
            pass
    # Sedute / terapie
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Sedute (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID     INTEGER NOT NULL,
                Data_Seduta     TEXT,
                Terapia         TEXT,
                Professionista  TEXT,
                Costo           REAL DEFAULT 0,
                Pagato          INTEGER DEFAULT 0,
                Note            TEXT
            )
            """
        )

        # Coupons
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Coupons (
                ID                  INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID         INTEGER NOT NULL,
                Tipo_Coupon         TEXT,
                Codice_Coupon       TEXT,
                Data_Assegnazione   TEXT,
                Note                TEXT,
                Utilizzato          INTEGER DEFAULT 0
            )
            """
        )

        
        # Consensi privacy (adulto / minore) + marketing (Klaviyo)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Consensi_Privacy (
                ID                  INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID         INTEGER NOT NULL,
                Data_Ora            TEXT,
                Tipo                TEXT,   -- ADULTO / MINORE
                Tutore_Nome         TEXT,
                Tutore_CF           TEXT,
                Tutore_Telefono     TEXT,
                Tutore_Email        TEXT,
                Consenso_Trattamento    INTEGER DEFAULT 0,
                Consenso_Comunicazioni  INTEGER DEFAULT 0,
                Consenso_Marketing       INTEGER DEFAULT 0,
                Canale_Email            INTEGER DEFAULT 0,
                Canale_SMS              INTEGER DEFAULT 0,
                Canale_WhatsApp          INTEGER DEFAULT 0,
                Usa_Klaviyo              INTEGER DEFAULT 0,
                Firma_Blob               BLOB,
                Firma_Filename           TEXT,
                Firma_URL                TEXT,
                Firma_Source             TEXT,
                Pdf_Blob               BLOB,
                Pdf_Filename           TEXT,
                Note                    TEXT
            )
    """
    )


        
        # Migrazione Consensi_Privacy (SQLite) – aggiunge colonne firma se mancanti
        try:
            cur.execute("PRAGMA table_info(Consensi_Privacy)")
            existing_cols = {r[1] for r in cur.fetchall()}
            mig_cols = [
                ("Firma_Blob", "BLOB"),
                ("Firma_Filename", "TEXT"),
                ("Firma_URL", "TEXT"),
                ("Firma_Source", "TEXT"),
                ("Pdf_Blob", "BLOB"),
                ("Pdf_Filename", "TEXT"),
            ]
            for col, typ in mig_cols:
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE Consensi_Privacy ADD COLUMN {col} {typ}")
        except Exception:
            pass

        
        # Relazioni Cliniche (SQLite)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relazioni_cliniche (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        paziente_id  INTEGER NOT NULL,
        tipo         TEXT NOT NULL,
        titolo       TEXT NOT NULL,
        data_relazione TEXT NOT NULL,
        docx_path    TEXT NOT NULL,
        pdf_path     TEXT,
        note         TEXT,
        created_at   TEXT NOT NULL
            )
            """
        )
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
        except Exception:
            pass
        
        conn.commit()
        return

    # -------------------------
    # PostgreSQL (Neon) init
    # -------------------------
    # Nota: usiamo tipi compatibili e vincoli FK corretti.
        # Anamnesi (Valutazione PNEV) – tabella centrale (PostgreSQL)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Anamnesi (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID     BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Anamnesi   TEXT,
            Motivo          TEXT,
            Storia          TEXT,
            Note            TEXT,
            Perinatale      TEXT,
            Sviluppo        TEXT,
            Scuola          TEXT,
            Emotivo         TEXT,
            Sensoriale      TEXT,
            Stile_Vita      TEXT,
            pnev_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
            pnev_summary     TEXT
        )
        """
    )

    # Migrazione PNEV (PostgreSQL) – Anamnesi: JSON strutturato + summary
    try:
        cur.execute("ALTER TABLE IF EXISTS Anamnesi ADD COLUMN IF NOT EXISTS pnev_json JSONB NOT NULL DEFAULT '{}'::jsonb;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE IF EXISTS Anamnesi ADD COLUMN IF NOT EXISTS pnev_summary TEXT;")
    except Exception:
        pass



    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Valutazioni_Visive (
            ID                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID         BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Valutazione    TEXT,
            Tipo_Visita         TEXT,
            Professionista      TEXT,
            Anamnesi            TEXT,
            Acuita_Nat_OD       TEXT, Acuita_Nat_OS       TEXT, Acuita_Nat_OO       TEXT,
            Acuita_Corr_OD      TEXT, Acuita_Corr_OS      TEXT, Acuita_Corr_OO      TEXT,
            SF_Ogg_OD           REAL, CIL_Ogg_OD          REAL, AX_Ogg_OD           INTEGER,
            SF_Ogg_OS           REAL, CIL_Ogg_OS          REAL, AX_Ogg_OS           INTEGER,
            SF_Sogg_OD          REAL, CIL_Sogg_OD         REAL, AX_Sogg_OD          INTEGER,
            SF_Sogg_OS          REAL, CIL_Sogg_OS         REAL, AX_Sogg_OS          INTEGER,
            ADD_Vicino          REAL,
            K1_OD_mm            REAL, K1_OD_D            REAL, K2_OD_mm            REAL, K2_OD_D            REAL,
            K1_OS_mm            REAL, K1_OS_D            REAL, K2_OS_mm            REAL, K2_OS_D            REAL,
            Tono_OD             REAL, Tono_OS             REAL,
            Motilita            TEXT,
            Cover_Test          TEXT,
            Stereopsi           TEXT,
            PPC_cm              REAL,
            Ishihara            TEXT,
            Pachim_OD_um        REAL, Pachim_OS_um        REAL,
            Fondo               TEXT,
            Campo_Visivo        TEXT,
            OCT                 TEXT,
            Topografia          TEXT,
            Costo               REAL,
            Pagato              INTEGER NOT NULL DEFAULT 0,
            Note                TEXT
        )
        """
    )

    
    # Migrazione campi Esame Obiettivo (PostgreSQL) – aggiunge colonne se mancanti
    try:
        cur.execute("""
            ALTER TABLE IF EXISTS Valutazioni_Visive
                ADD COLUMN IF NOT EXISTS Cornea              TEXT,
                ADD COLUMN IF NOT EXISTS Camera_Anteriore    TEXT,
                ADD COLUMN IF NOT EXISTS Cristallino         TEXT,
                ADD COLUMN IF NOT EXISTS Congiuntiva_Sclera  TEXT,
                ADD COLUMN IF NOT EXISTS Iride_Pupilla       TEXT,
                ADD COLUMN IF NOT EXISTS Vitreo              TEXT;
        """)
    except Exception:
        pass


    # Migrazione PNEV (PostgreSQL) – JSON strutturato + summary
    try:
        cur.execute("ALTER TABLE IF EXISTS Valutazioni_Visive ADD COLUMN IF NOT EXISTS pnev_json JSONB NOT NULL DEFAULT '{}'::jsonb;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE IF EXISTS Valutazioni_Visive ADD COLUMN IF NOT EXISTS pnev_summary TEXT;")
    except Exception:
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Sedute (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID     BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Seduta     TEXT,
            Terapia         TEXT,
            Professionista  TEXT,
            Costo           REAL,
            Pagato          INTEGER NOT NULL DEFAULT 0,
            Note            TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Coupons (
            ID                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID       BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Tipo_Coupon       TEXT NOT NULL,     -- OF o SDS
            Codice_Coupon     TEXT,              -- numero / codice coupon
            Data_Assegnazione TEXT,
            Note              TEXT,
            Utilizzato        INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    



    # Consensi privacy (adulto / minore) + marketing (Klaviyo)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Consensi_Privacy (
            ID                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID         BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Ora            TEXT,
            Tipo                TEXT,   -- ADULTO / MINORE
            Tutore_Nome         TEXT,
            Tutore_CF           TEXT,
            Tutore_Telefono     TEXT,
            Tutore_Email        TEXT,
            Consenso_Trattamento    INTEGER NOT NULL DEFAULT 0,
            Consenso_Comunicazioni  INTEGER NOT NULL DEFAULT 0,
            Consenso_Marketing       INTEGER NOT NULL DEFAULT 0,
            Canale_Email            INTEGER NOT NULL DEFAULT 0,
            Canale_SMS              INTEGER NOT NULL DEFAULT 0,
            Canale_WhatsApp          INTEGER NOT NULL DEFAULT 0,
            Usa_Klaviyo              INTEGER NOT NULL DEFAULT 0,
            Note                    TEXT
        )
        """
    )

    
    # Migrazione Consensi_Privacy (PostgreSQL) – aggiunge colonne firma se mancanti
    try:
        cur.execute(
            """
            ALTER TABLE IF EXISTS Consensi_Privacy
                ADD COLUMN IF NOT EXISTS Firma_Blob BYTEA,
                ADD COLUMN IF NOT EXISTS Firma_Filename TEXT,
                ADD COLUMN IF NOT EXISTS Firma_URL TEXT,
                ADD COLUMN IF NOT EXISTS Firma_Source TEXT,
                ADD COLUMN IF NOT EXISTS Pdf_Blob BYTEA,
                ADD COLUMN IF NOT EXISTS Pdf_Filename TEXT;
            """
        )
    except Exception:
        pass

    # Relazioni Cliniche (PostgreSQL)
    # (Inizializzazione spostata dentro init_db / funzioni helper per evitare NameError in import)

def _solo_lettere(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalpha())

def _codice_cognome(cognome: str) -> str:
    s = _solo_lettere(cognome)
    consonanti = [c for c in s if c not in "AEIOU"]
    vocali = [c for c in s if c in "AEIOU"]
    codice = "".join(consonanti + vocali)[:3]
    return (codice + "XXX")[:3]

def _codice_nome(nome: str) -> str:
    s = _solo_lettere(nome)
    consonanti = [c for c in s if c not in "AEIOU"]
    vocali = [c for c in s if c in "AEIOU"]
    if len(consonanti) >= 4:
        # regola CF: 1a, 3a e 4a consonante
        codice = consonanti[0] + consonanti[2] + consonanti[3]
    else:
        codice = "".join(consonanti + vocali)[:3]
    return (codice + "XXX")[:3]

# ------------------------------
# Codice Fiscale - tabelle
# ------------------------------
# Mese (01-12) -> lettera
MESE_CF = {
    1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "H",
    7: "L", 8: "M", 9: "P", 10: "R", 11: "S", 12: "T",
}

# Tabelle ufficiali per il carattere di controllo (16° carattere)
CONTROL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

EVEN_MAP = {
    **{str(i): i for i in range(10)},
    **{chr(ord("A") + i): i for i in range(26)},
}

ODD_MAP = {
    # cifre
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9,
    "5": 13, "6": 15, "7": 17, "8": 19, "9": 21,
    # lettere
    "A": 1, "B": 0, "C": 5, "D": 7, "E": 9,
    "F": 13, "G": 15, "H": 17, "I": 19, "J": 21,
    "K": 2, "L": 4, "M": 18, "N": 20, "O": 11,
    "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14,
    "U": 16, "V": 10, "W": 22, "X": 25, "Y": 24, "Z": 23,
}


def _codice_data_sesso(d: date, sesso: str) -> str:
    yy = f"{d.year % 100:02d}"
    mm = MESE_CF[d.month]
    giorno = d.day + (40 if sesso.upper().startswith("F") else 0)
    gg = f"{giorno:02d}"
    return yy + mm + gg

def parse_data_it(data_str: str, campo: str = "Data"):
    """
    Prova a interpretare una data scritta in vari modi:
    - gg/mm/aaaa
    - gg-mm-aaaa
    - gg.mm.aaaa
    - gg mm aaaa

    Ritorna:
      - oggetto date se va bene
      - None se non riesce a interpretarla
    """
    if not data_str:
        return None

    s = data_str.strip()

    # unifichiamo i separatori a "/"
    for sep in ["-", ".", " "]:
        s = s.replace(sep, "/")

    # ora ci aspettiamo sempre gg/mm/aaaa
    try:
        d = datetime.strptime(s, "%d/%m/%Y").date()
        return d
    except ValueError:
        return None

CODICI_CATASTALI_CSV = "codici_catastali_comuni.csv"

@lru_cache(maxsize=1)
def load_codici_catastali() -> Dict[tuple, str]:
    """
    Carica i codici catastali da codici_catastali_comuni.csv.

    Formato richiesto (con header):
    paese;prov;codice_catastale
    ABANO TERME;PD;A001
    ...
    """
    mapping: Dict[tuple, str] = {}
    if not os.path.exists(CODICI_CATASTALI_CSV):
        return mapping

    try:
        with open(CODICI_CATASTALI_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                comune = (row.get("paese") or "").strip().upper()
                prov = (row.get("prov") or "").strip().upper()
                codice = (row.get("codice_catastale") or "").strip().upper()
                if comune and prov and codice:
                    mapping[(comune, prov)] = codice
    except Exception:
        # in caso di errore restituisce mappa vuota
        return {}

    return mapping


def _codice_catastale(comune: str, provincia: str) -> Optional[str]:
    """
    Ritorna il codice catastale leggendo dal CSV.

    comune: es. 'ABANO TERME'
    provincia: es. 'PD'
    """
    mapping = load_codici_catastali()
    key = (comune.strip().upper(), provincia.strip().upper())
    return mapping.get(key)



def _calcola_carattere_controllo(primi15: str) -> str:
    total = 0
    for i, ch in enumerate(primi15):
        if (i + 1) % 2 == 1:  # posizioni dispari (1-based)
            total += ODD_MAP.get(ch, 0)
        else:
            total += EVEN_MAP.get(ch, 0)
    resto = total % 26
    return CONTROL_CHARS[resto]

def genera_codice_fiscale(
    cognome: str,
    nome: str,
    data_nascita_str: str,
    sesso: str,
    comune_nascita: str,
    provincia_nascita: str,
) -> Optional[str]:
    """
    Genera un codice fiscale di supporto.
    Ritorna None se i dati non sono sufficienti/validi o se il comune non è noto.
    """

    cognome = (cognome or "").strip()
    nome = (nome or "").strip()
    data_nascita_str = (data_nascita_str or "").strip()
    sesso = (sesso or "").strip()
    comune_nascita = (comune_nascita or "").strip()
    provincia_nascita = (provincia_nascita or "").strip()

    if not (cognome and nome and data_nascita_str and sesso and comune_nascita and provincia_nascita):
        return None

    try:
        d = datetime.strptime(data_nascita_str, "%d/%m/%Y").date()
    except ValueError:
        return None

    cod_cat = _codice_catastale(comune_nascita, provincia_nascita)
    if not cod_cat:
        return None

    parte1 = _codice_cognome(cognome)
    parte2 = _codice_nome(nome)
    parte3 = _codice_data_sesso(d, sesso)
    primi15 = (parte1 + parte2 + parte3 + cod_cat).upper()
    if len(primi15) != 15:
        return None

    controllo = _calcola_carattere_controllo(primi15)
    return primi15 + controllo

def valida_codice_fiscale(cf: str) -> bool:
    cf = (cf or "").strip().upper()
    if len(cf) != 16:
        return False
    if not cf.isalnum():
        return False
    primi15 = cf[:15]
    expected = _calcola_carattere_controllo(primi15)
    return cf[-1] == expected

# -----------------------------
# Helpers: Cheratometria & CL tools
# -----------------------------

def cherato_mm_to_D(raggio_mm: float) -> float:
    """
    Conversione approssimata raggio (mm) -> diottrie.
    Formula: D ≈ 337.5 / r (mm)
    """
    if raggio_mm <= 0:
        return 0.0
    return 337.5 / raggio_mm

def cherato_D_to_mm(D: float) -> float:
    """
    Conversione approssimata diottrie -> raggio (mm).
    Formula: r (mm) ≈ 337.5 / D
    """
    if D <= 0:
        return 0.0
    return 337.5 / D

def convert_occhiali_to_cl(sphere_glasses: float, cyl_glasses: float, axis: float, vertex_mm: float = 12.0):
    """
    Conversione approssimata occhiali -> lenti a contatto (sfera + cilindro).
    Usa la formula del potere efficace: F_cl = F_g / (1 - d * F_g), con d in metri.
    Calcola il potere in due meridiani e ricostruisce sfera e cilindro CL.
    """
    d = vertex_mm / 1000.0  # mm -> m
    F1 = sphere_glasses
    F2 = sphere_glasses + cyl_glasses

    def eff(F):
        return F / (1 - d * F) if (1 - d * F) != 0 else F

    F1c = eff(F1)
    F2c = eff(F2)

    sphere_cl = F1c
    cyl_cl = F2c - F1c

    # arrotonda a step 0.25
    sphere_cl = round(sphere_cl * 4) / 4.0
    cyl_cl = round(cyl_cl * 4) / 4.0
    axis_cl = axis  # asse invariato (approssimazione)

    return sphere_cl, cyl_cl, axis_cl

# -----------------------------
# Helpers: Acuità visiva (lista valori)
# -----------------------------

AV_OPTIONS = [
    "NV - non vedente",
    "PL - percezione luce",
    "ML/HM - moto mano",
    "CF 30 cm",
    "CF 50 cm",
    "CF 1 m",
    "1/50",
    "1/20",
    "1/10",
    "2/10",
    "3/10",
    "4/10",
    "5/10",
    "6/10",
    "7/10",
    "8/10",
    "9/10",
    "10/10",
    "12/10",
    "14/10",
    "16/10",
]

def av_select(label: str, current_value: Optional[str], key: str) -> str:
    """
    Selectbox per acuità visiva.
    Mantiene il valore salvato anche se non è in AV_OPTIONS (lo mette in cima).
    """
    base = AV_OPTIONS.copy()
    if current_value and current_value not in base:
        options = [current_value] + base
    else:
        options = [""] + base
    index = 0
    if current_value and current_value in options:
        index = options.index(current_value)
    return st.selectbox(label, options, index=index, key=key)

# -----------------------------
# UI: Pazienti
# -----------------------------

def _format_data_it_from_iso(iso_str: Optional[str]) -> str:
    """
    Converte una data ISO (aaaa-mm-gg) in formato italiano gg/mm/aaaa.
    Se non valida, restituisce la stringa originale.
    """
    if not iso_str:
        return ""
    try:
        d = datetime.strptime(iso_str, "%Y-%m-%d").date()
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso_str



def genera_referto_oculistico_pdf(paziente, valutazione, include_header: bool) -> bytes:
    """
    Genera un referto oculistico/optometrico in PDF A4.
    - Usa background letterhead (con/ senza Cirillo) se disponibile
    - Contenuto spostato più in alto di ~2.5 cm rispetto alla versione precedente
    - Stampa SOLO i campi compilati (nessuna riga vuota o con soli separatori)
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Sfondo intestazione (immagine A4)
    try:
        variant = "with_cirillo" if include_header else "no_cirillo"
        bg = _find_bg_image("a4", variant)
        _draw_bg_image_fullpage(c, width, height, bg)
    except Exception:
        pass

    left = 30 * mm
    right = width - 30 * mm

    # ✅ Alza la stampa di 2.5 cm (25mm)
    top_with_header = height - 30 * mm   # prima: 55mm
    top_no_header   = height - 55 * mm   # prima: 80mm
    top = top_with_header if include_header else top_no_header

    bottom = 30 * mm
    y = top

    def _newline(n=12):
        nonlocal y
        y -= n

    def _reset_y_for_new_page():
        nonlocal y
        y = top_with_header if include_header else top_no_header

    def _ensure_space(min_y=bottom + 40):
        nonlocal y
        if y < min_y:
            c.showPage()
            # riapplica background anche sulle pagine successive
            try:
                variant = "with_cirillo" if include_header else "no_cirillo"
                bg = _find_bg_image("a4", variant)
                _draw_bg_image_fullpage(c, width, height, bg)
            except Exception:
                pass
            _reset_y_for_new_page()

    def _draw_header():
        # Header testuale (fallback); normalmente l'intestazione è già nel background.
        yy = height - 18 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left, yy, "Studio The Organism")
        yy -= 12
        c.setFont("Helvetica", 10)
        c.drawString(left, yy, "Via De Rosa 46 – Pagani (SA)")
        yy -= 11
        c.drawString(left, yy, "www.ferraioligiuseppe.it  |  Tel. 393 581 7157")
        c.line(left, yy - 6, right, yy - 6)

    # Se vuoi un header testuale extra (di solito no), abilitalo qui:
    # if include_header:
    #     _draw_header()
    #     y = top_with_header

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Referto oculistico / optometrico")
    _newline(18)

    # Dati paziente (solo se presenti)
    c.setFont("Helvetica", 11)
    nome_paz = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    if nome_paz:
        c.drawString(left, y, f"Paziente: {nome_paz}")
        _newline(14)

    dn = _format_data_it_from_iso(paziente.get("Data_Nascita"))
    if dn:
        c.drawString(left, y, f"Data di nascita: {dn}")
        _newline(14)

    data_vis = _format_data_it_from_iso(valutazione.get("Data_Valutazione"))
    if data_vis:
        c.drawString(left, y, f"Data visita: {data_vis}")
        _newline(14)

    tipo_visita = (valutazione.get("Tipo_Visita") or "").strip()
    if tipo_visita:
        c.drawString(left, y, f"Tipo visita: {tipo_visita}")
        _newline(14)

    prof = (valutazione.get("Professionista") or "").strip()
    if prof:
        c.drawString(left, y, f"Professionista: {prof}")
        _newline(16)

    # -------------------
    # Acuità visiva (solo campi compilati)
    # -------------------
    def _fmt_av_triplet(prefix: str, od, os_, oo):
        parts = []
        if (od or "").strip():
            parts.append(f"OD {str(od).strip()}")
        if (os_ or "").strip():
            parts.append(f"OS {str(os_).strip()}")
        if (oo or "").strip():
            parts.append(f"OO {str(oo).strip()}")
        if not parts:
            return ""
        return f"{prefix}: " + "   ".join(parts)

    av_nat = _fmt_av_triplet(
        "Acuità visiva naturale",
        valutazione.get("Acuita_Nat_OD"),
        valutazione.get("Acuita_Nat_OS"),
        valutazione.get("Acuita_Nat_OO"),
    )
    av_corr = _fmt_av_triplet(
        "Acuità visiva corretta",
        valutazione.get("Acuita_Corr_OD"),
        valutazione.get("Acuita_Corr_OS"),
        valutazione.get("Acuita_Corr_OO"),
    )

    for line in (av_nat, av_corr):
        if line:
            _ensure_space()
            c.drawString(left, y, line)
            _newline(14)
    if av_nat or av_corr:
        _newline(6)

    # -------------------
    # Esame obiettivo (solo campi compilati)
    # -------------------
    eo = [
        ("Cornea", valutazione.get("Cornea")),
        ("Camera anteriore", valutazione.get("Camera_Anteriore")),
        ("Cristallino", valutazione.get("Cristallino")),
        ("Congiuntiva / Sclera", valutazione.get("Congiuntiva_Sclera")),
        ("Iride / Pupilla", valutazione.get("Iride_Pupilla")),
        ("Vitreo", valutazione.get("Vitreo")),
    ]
    eo_items = [(lab, ("" if v is None else str(v).strip())) for lab, v in eo]
    eo_items = [(lab, v) for lab, v in eo_items if v]

    if eo_items:
        c.setFont("Helvetica-Bold", 11)
        _ensure_space()
        c.drawString(left, y, "Esame obiettivo (strutture oculari)")
        _newline(14)
        c.setFont("Helvetica", 11)
        for lab, vv in eo_items:
            _ensure_space()
            c.drawString(left, y, f"- {lab}: {vv}")
            _newline(13)
        _newline(6)

    # -------------------
    # Dettaglio clinico (valutazione['Note']) filtrato: SOLO righe compilate
    # -------------------
    testo_raw = (valutazione.get("Note") or "").strip()

    def _is_filled_line(line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        # Non stampare righe di firma già gestite a parte
        if s.lower().startswith("firma"):
            return False
        # Righe tipo "- Campo:" senza contenuto
        if s.startswith("-"):
            body = s.lstrip("-").strip()
            # "- X:" oppure "- X :" oppure "- X:" + solo spazi
            if ":" in body:
                left_part, right_part = body.split(":", 1)
                if right_part.strip() == "":
                    return False
            else:
                # "- " senza niente
                if body == "":
                    return False
        else:
            # Righe tipo "NOTE LIBERE:" senza contenuto
            if ":" in s:
                left_part, right_part = s.split(":", 1)
                if right_part.strip() == "" and len(left_part.strip()) <= 40:
                    return False
        return True

    def _is_section_header(line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        # Header tipici in maiuscolo (es: "ACUITÀ VISIVA", "TONOMETRIA", ecc.)
        if s == s.upper() and any(ch.isalpha() for ch in s) and ":" not in s and not s.startswith("-"):
            return True
        return False

    def _filter_note_block(raw: str) -> list[str]:
        lines = [ln.rstrip() for ln in raw.splitlines()]
        sections = []
        current_header = None
        current_items = []

        def flush():
            nonlocal current_header, current_items
            if current_items:
                if current_header:
                    sections.append(current_header)
                sections.extend(current_items)
            current_header = None
            current_items = []

        for ln in lines:
            if _is_section_header(ln):
                flush()
                current_header = ln.strip()
                continue
            if _is_filled_line(ln):
                current_items.append(ln.strip())
        flush()
        return sections

    filtered_lines = _filter_note_block(testo_raw)

    if filtered_lines:
        c.setFont("Helvetica-Bold", 11)
        _ensure_space()
        c.drawString(left, y, "Dettaglio clinico")
        _newline(14)

        c.setFont("Helvetica", 11)
        wrapper = textwrap.TextWrapper(width=90)
        for ln in filtered_lines:
            # lascia una piccola distanza prima dei titoli sezione
            if _is_section_header(ln):
                _newline(4)
                c.setFont("Helvetica-Bold", 11)
                _ensure_space()
                c.drawString(left, y, ln)
                _newline(14)
                c.setFont("Helvetica", 11)
                continue

            # wrap normale
            for wline in wrapper.wrap(ln):
                _ensure_space()
                c.drawString(left, y, wline)
                _newline(13)

            _newline(2)

    # Firma (sempre)
    if y < bottom + 60:
        c.showPage()
        try:
            variant = "with_cirillo" if include_header else "no_cirillo"
            bg = _find_bg_image("a4", variant)
            _draw_bg_image_fullpage(c, width, height, bg)
        except Exception:
            pass
        _reset_y_for_new_page()

    y_sig = bottom + 40
    c.line(right - 120, y_sig, right, y_sig)
    c.setFont("Helvetica", 10)
    c.drawString(right - 115, y_sig + 5, "Firma / Timbro")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# -----------------------------
# Privacy PDF + Storico Consensi
# -----------------------------

def _now_iso_dt() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _bool_i(v) -> int:
    try:
        return 1 if bool(v) else 0
    except Exception:
        return 0

def insert_privacy_consent(cur, paziente_id: int, payload: dict):
    """Inserisce un record in Consensi_Privacy. Payload usa chiavi python-friendly."""
    cur.execute(
        """
        INSERT INTO Consensi_Privacy
        (Paziente_ID, Data_Ora, Tipo, Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
         Consenso_Trattamento, Consenso_Comunicazioni, Consenso_Marketing,
         Canale_Email, Canale_SMS, Canale_WhatsApp, Usa_Klaviyo,
         Firma_Blob, Firma_Filename, Firma_URL, Firma_Source,
         Pdf_Blob, Pdf_Filename, Note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paziente_id,
            payload.get("Data_Ora") or _now_iso_dt(),
            payload.get("Tipo") or "",
            payload.get("Tutore_Nome") or "",
            payload.get("Tutore_CF") or "",
            payload.get("Tutore_Telefono") or "",
            payload.get("Tutore_Email") or "",
            _bool_i(payload.get("Consenso_Trattamento")),
            _bool_i(payload.get("Consenso_Comunicazioni")),
            _bool_i(payload.get("Consenso_Marketing")),
            _bool_i(payload.get("Canale_Email")),
            _bool_i(payload.get("Canale_SMS")),
            _bool_i(payload.get("Canale_WhatsApp")),
            _bool_i(payload.get("Usa_Klaviyo")),
            payload.get("Firma_Blob"),
            payload.get("Firma_Filename") or "",
            payload.get("Firma_URL") or "",
            payload.get("Firma_Source") or "",
            payload.get("Pdf_Blob"),
            payload.get("Pdf_Filename") or "",
            payload.get("Note") or "",
        ),
    )

def fetch_privacy_consents(cur, paziente_id: int):
    cur.execute(
        """SELECT * FROM Consensi_Privacy WHERE Paziente_ID = ? ORDER BY Data_Ora DESC, ID DESC""",
        (paziente_id,),
    )
    return cur.fetchall()


# -----------------------------
# Google Forms (firma remota) + Google Sheets import
# -----------------------------
# I link sotto sono stati ricavati dai tuoi form precompilati (entry.xxx).
# Per usare l'import dallo Sheet ESISTENTE, pubblica il foglio delle risposte come CSV e metti l'URL in Secrets:
#   PRIVACY_SHEET_ADULTO_CSV_URL = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
#   PRIVACY_SHEET_MINORE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
#
# Nota sulla firma in Google Forms:
# - Google Forms NON supporta firma grafometrica "disegna qui" in modo nativo.
# - La soluzione pratica è una domanda "Caricamento file" (immagine della firma) oppure usare la firma su canvas nel gestionale.

FORM_MINORE_BASE = "https://docs.google.com/forms/d/e/1FAIpQLSezx9Xk05ok_EYhSJ1OnMAatSJHxLxST2e8-G_SI4Ad_X1_kg/viewform?usp=pp_url"
FORM_ADULTO_BASE = "https://docs.google.com/forms/d/e/1FAIpQLSe_GV962CPAw2osILAbQNqkivCHGSWES1VAdcJw3-f-LeCxbQ/viewform?usp=pp_url"

# Mappatura campi -> entry id (dal link che mi hai fornito)
FORM_MINORE_ENTRY = {
    "nome_cognome": "entry.324079259",
    "comune": "entry.1522430793",
    "data_nascita_iso": "entry.91400366",
    "tutore_nome": "entry.1194585802",
    "codice_fiscale": "entry.947551290",
    "email": "entry.295917843",
    "motivo": "entry.1792109233",
}

FORM_ADULTO_ENTRY = {
    "nome": "entry.1752970381",
    "codice_fiscale": "entry.648905519",
    "email": "entry.2080611620",
    "motivo": "entry.1529138592",
}

def _urlencode_params(params: dict) -> str:
    # Mantiene spazi come + (compatibile Forms)
    return urllib.parse.urlencode({k: (v or "") for k, v in params.items()}, doseq=True)

def build_google_form_url_adulto(paziente: dict, motivo: str = "") -> str:
    nome = f"{(paziente.get('Nome','') or '').strip()} {(paziente.get('Cognome','') or '').strip()}".strip()
    cf = (paziente.get("Codice_Fiscale") or "").strip().upper()
    email = (paziente.get("Email") or "").strip()
    params = {
        FORM_ADULTO_ENTRY["nome"]: nome,
        FORM_ADULTO_ENTRY["codice_fiscale"]: cf,
        FORM_ADULTO_ENTRY["email"]: email,
        FORM_ADULTO_ENTRY["motivo"]: motivo,
    }
    return FORM_ADULTO_BASE + "&" + _urlencode_params(params)

def build_google_form_url_minore(paziente: dict, motivo: str = "", tutore_fallback: dict | None = None) -> str:
    nome = f"{(paziente.get('Nome','') or '').strip()} {(paziente.get('Cognome','') or '').strip()}".strip()
    comune = (paziente.get("Citta") or paziente.get("Città") or "").strip()
    # data nascita attesa in ISO yyyy-mm-dd nel form (dal tuo esempio)
    dn_iso = (paziente.get("Data_Nascita") or "").strip()
    cf = (paziente.get("Codice_Fiscale") or "").strip().upper()
    email = (paziente.get("Email") or "").strip()

    # Se hai già un consenso MINORE salvato, puoi usare i dati tutore da lì.
    tutore_nome = (tutore_fallback or {}).get("Tutore_Nome","") if tutore_fallback else ""
    if not tutore_nome:
        tutore_nome = (tutore_fallback or {}).get("tutore_nome","") if tutore_fallback else ""

    params = {
        FORM_MINORE_ENTRY["nome_cognome"]: nome,
        FORM_MINORE_ENTRY["comune"]: comune,
        FORM_MINORE_ENTRY["data_nascita_iso"]: dn_iso,
        FORM_MINORE_ENTRY["tutore_nome"]: tutore_nome,
        FORM_MINORE_ENTRY["codice_fiscale"]: cf,
        FORM_MINORE_ENTRY["email"]: email,
        FORM_MINORE_ENTRY["motivo"]: motivo,
    }
    return FORM_MINORE_BASE + "&" + _urlencode_params(params)

def _read_csv_url(url: str):
    try:
        import pandas as pd
        return pd.read_csv(url)
    except Exception:
        return None

def import_privacy_from_sheet_csv(cur, paziente: dict, tipo: str) -> int | None:
    """Importa l'ultima risposta dallo Sheet (pubblicato CSV) e la registra in Consensi_Privacy.
    Ritorna l'ID inserito (se disponibile) o None se non trova match.

    Match per Codice Fiscale (preferito) oppure Email.
    """
    sec = _safe_secrets()
    url_key = "PRIVACY_SHEET_MINORE_CSV_URL" if tipo.upper().startswith("M") else "PRIVACY_SHEET_ADULTO_CSV_URL"
    csv_url = (sec.get(url_key) or "").strip()
    if not csv_url:
        return None

    df = _read_csv_url(csv_url)
    if df is None or df.empty:
        return None

    cf = (paziente.get("Codice_Fiscale") or "").strip().upper()
    email = (paziente.get("Email") or "").strip().lower()

    # Normalizza nomi colonne
    cols = {c.lower(): c for c in df.columns}
    # prova colonne comuni
    def col(*names):
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None

    col_cf = col("codice fiscale", "cf", "codice_fiscale")
    col_mail = col("email", "e-mail")
    col_ts = col("timestamp", "data/ora", "data ora", "submitted at", "submission time")

    # filtro match
    dff = df
    if col_cf and cf:
        dff = dff[dff[col_cf].astype(str).str.upper().str.strip() == cf]
    elif col_mail and email:
        dff = dff[dff[col_mail].astype(str).str.lower().str.strip() == email]
    else:
        return None

    if dff.empty:
        return None

    # ordina per timestamp se presente
    if col_ts:
        try:
            dff = dff.sort_values(col_ts, ascending=False)
        except Exception:
            pass

    row = dff.iloc[0].to_dict()

    # prova ad estrarre consensi (se presenti nel form); fallback: solo trattamento=1
    def _yn(v):
        s = str(v).strip().lower()
        return 1 if s in ("si","sì","yes","true","1","x","checked") else 0

    # prova colonne possibili
    c_tratt = None
    for n in ("consenso trattamento", "consenso al trattamento", "trattamento dati"):
        c_tratt = col(n)
        if c_tratt: break
    c_mark = None
    for n in ("marketing", "consenso marketing", "offerte", "promozioni"):
        c_mark = col(n)
        if c_mark: break
    c_serv = None
    for n in ("comunicazioni", "comunicazioni di servizio", "promemoria"):
        c_serv = col(n)
        if c_serv: break

    consenso_tratt = _yn(row.get(c_tratt)) if c_tratt else 1
    consenso_mark = _yn(row.get(c_mark)) if c_mark else 0
    consenso_serv = _yn(row.get(c_serv)) if c_serv else 1

    # firma: se nel form c'è "Caricamento file", nel foglio appare spesso come link o nome file.
    firma_url = ""
    for c in df.columns:
        cl = str(c).strip().lower()
        if any(k in cl for k in ("firma", "caric", "upload")):
            v = str(row.get(c) or "").strip()
            if v:
                firma_url = v
                break

    # Klaviyo: lo abilitiamo solo se marketing=1 e firma/consenso presente
    usa_klaviyo = 1 if (consenso_mark == 1) else 0

    paz_id = int(paziente.get("ID") or 0)
    now_iso = datetime.now().isoformat(timespec="seconds")
    tipo_db = "MINORE" if tipo.upper().startswith("M") else "ADULTO"

    # campi tutore: se presenti nel form, prova a leggerli; altrimenti lascia vuoti
    t_nome = ""
    t_cf = ""
    t_tel = ""
    t_mail = ""
    if tipo_db == "MINORE":
        c_tn = col("nome e cognome tutore", "tutore", "genitore/tutore")
        c_tcf = col("codice fiscale tutore", "cf tutore")
        c_ttel = col("telefono tutore", "tel tutore")
        c_tmail = col("email tutore", "mail tutore")
        t_nome = str(row.get(c_tn) or "").strip() if c_tn else ""
        t_cf = str(row.get(c_tcf) or "").strip().upper() if c_tcf else ""
        t_tel = str(row.get(c_ttel) or "").strip() if c_ttel else ""
        t_mail = str(row.get(c_tmail) or "").strip() if c_tmail else ""

    note = "Fonte: Google Form/Sheet; Firma URL: " + (firma_url or "")

    cur.execute(
        """
        INSERT INTO Consensi_Privacy
        (Paziente_ID, Data_Ora, Tipo, Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
         Consenso_Trattamento, Consenso_Comunicazioni, Consenso_Marketing,
         Canale_Email, Canale_SMS, Canale_WhatsApp, Usa_Klaviyo,
         Firma_Blob, Firma_Filename, Firma_URL, Firma_Source, Note)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            paz_id,
            row.get(col_ts) or now_iso,
            tipo_db,
            t_nome, t_cf, t_tel, t_mail,
            consenso_tratt,
            consenso_serv,
            consenso_mark,
            1, 0, 0,
            usa_klaviyo,
            None,
            "",
            firma_url,
            "google_form",
            note,
        ),
    )
    try:
        return int(getattr(cur, "lastrowid", None) or 0) or None
    except Exception:
        return None



def _extract_firma_url(consenso: dict) -> str:
    """Estrae l'eventuale URL/valore firma salvato in Note.
    Formato atteso: '... Firma URL: <valore>' (salvato dall'import Google Sheet)."""
    try:
        note = str(consenso.get("Note") or "")
    except Exception:
        return ""
    if "Firma URL:" not in note:
        return ""
    try:
        return note.split("Firma URL:", 1)[1].strip()
    except Exception:
        return ""

def _is_firmato(consenso: dict) -> bool:
    return bool(_extract_firma_url(consenso))

def _draw_checkbox(c, x, y, checked: bool, label: str):
    box = 4 * mm
    c.rect(x, y - box + 1, box, box, stroke=1, fill=0)
    if checked:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 0.8*mm, y - box + 1.2*mm, "X")
    c.setFont("Helvetica", 10)
    c.drawString(x + box + 2*mm, y - box + 1.2*mm, label)

def genera_privacy_pdf(paziente: dict, consenso: dict, include_header: bool = True) -> bytes:
    """PDF privacy adulti/minori firmabile con spazi Firma + Timbro.
    NOTE: testo base (da personalizzare se vuoi una versione legale 'chiusa')."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # background letterhead (A4)
    try:
        variant = "with_cirillo" if include_header else "no_cirillo"
        bg = _find_bg_image('a4', variant)
        _draw_bg_image_fullpage(c, width, height, bg)
    except Exception:
        pass

    left = 22 * mm
    right = width - 22 * mm
    top = height - (55 * mm if include_header else 35 * mm)
    bottom = 20 * mm
    y = top

    def nl(h=12):
        nonlocal y
        y -= h

    def ensure(min_y=bottom + 55):
        nonlocal y
        if y < min_y:
            c.showPage()
            # su pagine successive NON ripetiamo il background per non 'sporcare' la firma
            y = height - 25*mm

    tipo = (consenso.get("Tipo") or "").upper()  # ADULTO / MINORE
    data_ora = _safe_str(consenso.get("Data_Ora"))
    data_str = data_ora.split(" ")[0] if data_ora else datetime.now().strftime("%Y-%m-%d")
    data_it = _format_data_it_from_iso(data_str) if data_str else datetime.now().strftime("%d/%m/%Y")

    nome_paz = f"{_safe_str(paziente.get('Cognome'))} {_safe_str(paziente.get('Nome'))}".strip()
    dn = _format_data_it_from_iso(paziente.get("Data_Nascita"))

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "INFORMATIVA PRIVACY E CONSENSO AL TRATTAMENTO DEI DATI (GDPR)")
    nl(16)

    c.setFont("Helvetica", 10.5)
    c.drawString(left, y, f"Paziente: {nome_paz}")
    nl(12)
    if dn:
        c.drawString(left, y, f"Data di nascita: {dn}")
        nl(12)
    c.drawString(left, y, f"Data: {data_it}   |   Luogo: Pagani (SA)")
    nl(16)
    # Se presente, riporta riferimento a firma digitale (Google Form / upload firma)
    firma_val = _extract_firma_url(consenso)
    if firma_val:
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(left, y, "Firma digitale acquisita (Google Form):")
        nl(12)
        c.setFont("Helvetica", 9.5)
        # spezza su più righe se lungo
        maxw = 95
        s = str(firma_val)
        for i in range(0, len(s), maxw):
            ensure()
            c.drawString(left, y, s[i:i+maxw])
            nl(11)
        nl(6)


    if tipo == "MINORE":
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Dati del genitore/tutore legale")
        nl(14)
        c.setFont("Helvetica", 10.5)
        c.drawString(left, y, f"Nome e Cognome: {_safe_str(consenso.get('Tutore_Nome'))}")
        nl(12)
        cf_t = _safe_str(consenso.get("Tutore_CF"))
        if cf_t:
            c.drawString(left, y, f"Codice Fiscale: {cf_t}")
            nl(12)
        tel_t = _safe_str(consenso.get("Tutore_Telefono"))
        em_t = _safe_str(consenso.get("Tutore_Email"))
        if tel_t:
            c.drawString(left, y, f"Telefono: {tel_t}")
            nl(12)
        if em_t:
            c.drawString(left, y, f"Email: {em_t}")
            nl(14)

    # Testo informativa (breve ma completa per uso studio; se vuoi la 'versione lunga' la mettiamo)
    c.setFont("Helvetica", 10)
    testo = (
        "Titolare del trattamento: Studio The Organism. Finalità: gestione clinica/assistenziale, " 
        "amministrativa e organizzativa delle prestazioni; adempimenti di legge. Base giuridica: " 
        "consenso (ove richiesto) e/o esecuzione del rapporto di cura/servizio. Conservazione: " 
        "per il tempo necessario alle finalità e secondo obblighi di legge. Diritti: accesso, " 
        "rettifica, cancellazione nei limiti di legge, limitazione, opposizione, portabilità; " 
        "reclamo al Garante Privacy. I dati possono essere comunicati a fornitori/Responsabili esterni " 
        "per servizi tecnici/gestionali (es. hosting, email, backup).\n\n"
        "Marketing (facoltativo): se autorizzato, i contatti possono essere gestiti tramite Klaviyo " 
        "(piattaforma email/SMS marketing) per invio di comunicazioni promozionali e contenuti informativi. " 
        "Il consenso marketing è revocabile in qualsiasi momento."
    )
    wrapper = textwrap.TextWrapper(width=105)
    for line in wrapper.wrap(testo):
        ensure()
        c.drawString(left, y, line)
        nl(12)
    nl(8)

    # Consensi (checkbox)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Consensi")
    nl(12)

    def g(k):
        v = consenso.get(k)
        try:
            return bool(int(v))
        except Exception:
            return bool(v)

    _draw_checkbox(c, left, y, g("Consenso_Trattamento"), "Consenso al trattamento dati per finalità cliniche/gestionali (obbligatorio)")
    nl(12)
    _draw_checkbox(c, left, y, g("Consenso_Comunicazioni"), "Consenso a comunicazioni di servizio (appuntamenti, referti, promemoria)")
    nl(12)
    _draw_checkbox(c, left, y, g("Consenso_Marketing"), "Consenso a comunicazioni promozionali/offerte (facoltativo)")
    nl(14)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Canali autorizzati")
    nl(12)
    _draw_checkbox(c, left, y, g("Canale_Email"), "Email")
    nl(12)
    _draw_checkbox(c, left, y, g("Canale_SMS"), "SMS")
    nl(12)
    _draw_checkbox(c, left, y, g("Canale_WhatsApp"), "WhatsApp")
    nl(14)

    _draw_checkbox(c, left, y, g("Usa_Klaviyo"), "Autorizzo l'uso di Klaviyo per newsletter/SMS marketing (solo se marketing attivo)")
    nl(16)

    note = _safe_str(consenso.get("Note"))
    if note:
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(left, y, "Note:")
        nl(12)
        c.setFont("Helvetica", 10)
        for line in textwrap.TextWrapper(width=105).wrap(note.replace("\n", " ")):
            ensure()
            c.drawString(left, y, line)
            nl(12)
        nl(8)

    # Firme
    ensure(bottom + 80)
    y_sig = bottom + 55
    c.setFont("Helvetica", 10)

    # Linea firma paziente/tutore
    label_firma = "Firma Paziente" if tipo != "MINORE" else "Firma Genitore/Tutore"
    c.drawString(left, y_sig + 22, label_firma)
    c.line(left, y_sig + 18, left + 80*mm, y_sig + 18)

    # Linea firma professionista + timbro
    c.drawString(right - 95*mm, y_sig + 22, "Firma Professionista")
    c.line(right - 95*mm, y_sig + 18, right - 15*mm, y_sig + 18)

    c.setFont("Helvetica", 9)
    c.drawString(right - 40*mm, y_sig - 2, "Timbro")
    c.rect(right - 45*mm, y_sig - 22, 40*mm, 18*mm, stroke=1, fill=0)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def draw_axis_arrow(c, center_x, center_y, radius, axis_deg: int):
    """
    Disegna una freccia sulla semicirconferenza per indicare l'asse (0–180°).
    0° = lato destro, 90° = alto, 180° = sinistra.
    """
    axis_deg = max(0, min(180, int(axis_deg)))  # clamp di sicurezza
    angle_rad = math.radians(axis_deg)

    # Punto interno e punto sulla circonferenza
    r1 = radius * 0.7
    r2 = radius * 0.95
    x1 = center_x + r1 * math.cos(angle_rad)
    y1 = center_y + r1 * math.sin(angle_rad)
    x2 = center_x + r2 * math.cos(angle_rad)
    y2 = center_y + r2 * math.sin(angle_rad)

    c.setLineWidth(1)
    # stelo della freccia
    c.line(x1, y1, x2, y2)

    # testa della freccia (due segmentini inclinati)
    head_len = radius * 0.15
    for delta in (-20, 20):
        ang = angle_rad + math.radians(delta)
        hx = x2 - head_len * math.cos(ang)
        hy = y2 - head_len * math.sin(ang)
        c.line(x2, y2, hx, hy)

def draw_axis_arrow(c, center_x, center_y, radius, axis_deg: int):
    """
    Disegna una freccia sulla semicirconferenza per indicare l'asse (0–180°).
    0° = lato destro, 90° = alto, 180° = sinistra.
    """
    axis_deg = max(0, min(180, int(axis_deg)))  # clamp di sicurezza
    angle_rad = math.radians(axis_deg)

    # Punto interno e punto sulla circonferenza
    r1 = radius * 0.7
    r2 = radius * 0.95
    x1 = center_x + r1 * math.cos(angle_rad)
    y1 = center_y + r1 * math.sin(angle_rad)
    x2 = center_x + r2 * math.cos(angle_rad)
    y2 = center_y + r2 * math.sin(angle_rad)

    c.setLineWidth(1)
    # stelo della freccia
    c.line(x1, y1, x2, y2)

    # testa della freccia (due segmentini inclinati)
    head_len = radius * 0.15
    for delta in (-20, 20):
        ang = angle_rad + math.radians(delta)
        hx = x2 - head_len * math.cos(ang)
        hy = y2 - head_len * math.sin(ang)
        c.line(x2, y2, hx, hy)



def _draw_prescrizione_values_only_on_canvas(
    c,
    width: float,
    height: float,
    paziente,
    data_prescrizione_iso: Optional[str],
    # lontano/intermedio/vicino OD/OS
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
):
    """Overlay SOLO VALORI: non disegna linee/archi/riquadri (quelli sono nel template)."""

    # Helper formatting
    def fmt_sphere_cyl(v):
        if v is None or v == "": 
            return ""
        try:
            v = float(v)
        except Exception:
            return str(v)
        # +0.00 / -0.50
        if abs(v) < 1e-9:
            v = 0.0
        return f"{v:+.2f}"

    def fmt_axis(v):
        if v is None or v == "": 
            return ""
        try:
            iv = int(float(v))
            return str(iv)
        except Exception:
            return str(v)

    # Font
    c.setFont("Helvetica", 10)

    # Data (linea 'Data')
    data_it = _format_data_it_from_iso(data_prescrizione_iso) if data_prescrizione_iso else ""
    if data_it:
        c.drawString(105 * mm, height - 30 * mm, data_it)

    # Paziente (linea 'Sig.')
    try:
        nome_paz = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    except Exception:
        nome_paz = str(paziente)
    if nome_paz:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, height - 45 * mm, nome_paz)
        c.setFont("Helvetica", 10)

    # Coordinate centri box (mm -> punti) calibrate sul tuo template A5
    # OD (sinistra)
    od_x_sf  = 45 * mm
    od_x_cil = 68 * mm
    od_x_ax  = 91 * mm

    # OS (destra)
    os_x_sf  = 96 * mm
    os_x_cil = 119 * mm
    os_x_ax  = 142 * mm

    # Y dei tre righi (Lontano / Intermedio / Vicino)
    y_lon = 104 * mm
    y_int = 85 * mm
    y_vic = 66 * mm

    def put_triplet(xsf, xcil, xax, y, sf, cil, ax):
        s = fmt_sphere_cyl(sf)
        c1 = fmt_sphere_cyl(cil)
        a1 = fmt_axis(ax)
        if s:
            c.drawCentredString(xsf, y, s)
        if c1:
            c.drawCentredString(xcil, y, c1)
        if a1:
            c.drawCentredString(xax, y, a1)

    # OD
    put_triplet(od_x_sf, od_x_cil, od_x_ax, y_lon, sf_lon_od, cil_lon_od, ax_lon_od)
    put_triplet(od_x_sf, od_x_cil, od_x_ax, y_int, sf_int_od, cil_int_od, ax_int_od)
    put_triplet(od_x_sf, od_x_cil, od_x_ax, y_vic, sf_vic_od, cil_vic_od, ax_vic_od)

    # OS
    put_triplet(os_x_sf, os_x_cil, os_x_ax, y_lon, sf_lon_os, cil_lon_os, ax_lon_os)
    put_triplet(os_x_sf, os_x_cil, os_x_ax, y_int, sf_int_os, cil_int_os, ax_int_os)
    put_triplet(os_x_sf, os_x_cil, os_x_ax, y_vic, sf_vic_os, cil_vic_os, ax_vic_os)

    # Checkboxes lenti consigliate (metti "X" a sinistra delle voci)
    checks = set([str(x).strip().lower() for x in (lenti_scelte or [])])

    # Colonna sinistra (progressive, vicino/intermedio, fotocromatiche, polarizzate)
    base_x = 23 * mm
    base_y = 48 * mm
    dy = 6 * mm
    left_labels = [
        ("progressive", 0),
        ("per vicino/intermedio", 1),
        ("fotocromatiche", 2),
        ("polarizzate", 3),
    ]
    c.setFont("Helvetica-Bold", 10)
    for lab, i in left_labels:
        if any(lab in s for s in checks):
            c.drawString(base_x, base_y - i * dy, "X")

    # Colonna destra (trattamento antiriflesso, altri trattamenti)
    right_x = 112 * mm
    right_y = 48 * mm
    if any("trattamento antiriflesso" in s for s in checks):
        c.drawString(right_x, right_y, "X")
    # altri trattamenti: c'è una checkbox e riga testo
    if (altri_trattamenti or "").strip():
        c.drawString(right_x, right_y - 6 * mm, "X")
        c.setFont("Helvetica", 9)
        c.drawString(112 * mm, 35 * mm, str(altri_trattamenti)[:60])

    # NOTE
    if (note or "").strip():
        c.setFont("Helvetica", 9)
        # area note in basso a sinistra
        c.drawString(15 * mm, 20 * mm, (str(note).replace("\n", " "))[:120])


def _draw_prescrizione_occhiali_a5_on_canvas(
    c,
    width: float,
    height: float,
    paziente,
    data_prescrizione_iso: Optional[str],
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
):
    """Disegna la prescrizione (layout A5) sul canvas corrente, senza fare showPage/save."""
    left = 20 * mm
    right = width - 20 * mm
    top = height - 30 * mm
    bottom = 30 * mm

    # Data prescrizione
    c.setFont("Helvetica", 10)
    data_it = _format_data_it_from_iso(data_prescrizione_iso) if data_prescrizione_iso else ""
    if data_it:
        c.drawRightString(right, top, f"Data: {data_it}")

    # Nome paziente
    y = top - 15
    c.setFont("Helvetica-Bold", 11)
    nome_paz = f"{paziente['Cognome']} {paziente['Nome']}"
    c.drawString(left, y, f"Paziente: {nome_paz}")
    y -= 20

    # Semicerchi TABO semplificati per OD e OS
    c.setFont("Helvetica", 8)
    radius = 22 * mm
    center_y = y - radius - 5 * mm
    center_x_os = left + radius
    center_x_od = right - radius

    # OS – semicirconferenza + etichette
    c.arc(
        center_x_os - radius,
        center_y - radius,
        center_x_os + radius,
        center_y + radius,
        0,
        180,
    )
    c.drawString(center_x_os - radius - 4 * mm, center_y, "180° / 0°")
    c.drawString(center_x_os - 5, center_y + radius + 3 * mm, "90°")

    # OD – semicirconferenza + etichette
    c.arc(
        center_x_od - radius,
        center_y - radius,
        center_x_od + radius,
        center_y + radius,
        0,
        180,
    )
    c.drawString(center_x_od - radius - 4 * mm, center_y, "180° / 0°")
    c.drawString(center_x_od - 5, center_y + radius + 3 * mm, "90°")

    # Frecce sull'asse (uso gli assi di LONTANO: ax_lon_os / ax_lon_od)
    try:
        draw_axis_arrow(c, center_x_os, center_y, radius, ax_lon_os)
        draw_axis_arrow(c, center_x_od, center_y, radius, ax_lon_od)
    except Exception:
        # se per qualunque motivo qualcosa va storto, non blocchiamo la prescrizione
        pass

    y = center_y - radius - 10

    # Funzione di utilità per disegnare una riga LONTANO/INTERMEDIO/VICINO
    def draw_riga_prescr(y_start, label, sf_od, cil_od, ax_od, sf_os, cil_os, ax_os):
        # se tutti zero, saltiamo la riga
        if (
            abs(sf_od) < 0.001 and abs(cil_od) < 0.001 and int(ax_od) == 0 and
            abs(sf_os) < 0.001 and abs(cil_os) < 0.001 and int(ax_os) == 0
        ):
            return y_start

        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y_start, label)
        y = y_start - 11
        c.setFont("Helvetica", 9)
        c.drawString(
            left + 5 * mm,
            y,
            f"OD: SF {sf_od:+.2f}  CIL {cil_od:+.2f}  AX {int(ax_od)}°",
        )
        y -= 10
        c.drawString(
            left + 5 * mm,
            y,
            f"OS: SF {sf_os:+.2f}  CIL {cil_os:+.2f}  AX {int(ax_os)}°",
        )
        return y - 8

    y = draw_riga_prescr(y, "LONTANO", sf_lon_od, cil_lon_od, ax_lon_od, sf_lon_os, cil_lon_os, ax_lon_os)
    y = draw_riga_prescr(y, "INTERMEDIO", sf_int_od, cil_int_od, ax_int_od, sf_int_os, cil_int_os, ax_int_os)
    y = draw_riga_prescr(y, "VICINO", sf_vic_od, cil_vic_od, ax_vic_od, sf_vic_os, cil_vic_os, ax_vic_os)

    y -= 5

    # Lenti consigliate
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Lenti consigliate:")
    y -= 12
    c.setFont("Helvetica", 9)

    tutte_lenti = [
        "Progressive",
        "Per vicino/intermedio",
        "Fotocromatiche",
        "Polarizzate",
        "Controllo miopia",
        "Trattamento antiriflesso",
    ]

    for voce in tutte_lenti:
        mark = "[x]" if voce in lenti_scelte else "[ ]"
        c.drawString(left + 5 * mm, y, f"{mark} {voce}")
        y -= 10

    if altri_trattamenti:
        c.drawString(left + 5 * mm, y, f"Altri trattamenti: {altri_trattamenti}")
        y -= 12

    # Note
    if note.strip():
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "Note:")
        y -= 10
        c.setFont("Helvetica", 9)
        wrapper = textwrap.TextWrapper(width=70)
        for line in wrapper.wrap(note.strip()):
            if y < bottom + 40:
                break
            c.drawString(left + 5 * mm, y, line)
            y -= 11

    # Firma
    if y < bottom + 50:
        pass

        # Firma: se presente un'immagine (upload in gestionale) la inseriamo; altrimenti lasciamo la riga.
    c.line(right - 100, bottom + 30, right, bottom + 30)
    c.drawString(right - 95, bottom + 35, "Firma / Timbro")

    firma_bytes = _blob_to_bytes(consenso.get("Firma_Blob"))
    firma_url = _safe_str(consenso.get("Firma_URL"))
    if firma_bytes:
        try:
            img = ImageReader(io.BytesIO(firma_bytes))
            # riquadro firma: 100mm x 25mm circa
            c.drawImage(img, right - 100, bottom + 32, width=100, height=22, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    elif firma_url:
        # se la firma arriva da Google Form (file upload), lasciamo il riferimento nel PDF
        c.setFont("Helvetica", 7)
        c.drawString(left, bottom + 15, "Firma digitale (Google Form): " + firma_url[:110])






def genera_prescrizione_occhiali_a4_pdf(
    paziente,
    data_prescrizione_iso: Optional[str],
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
    con_cirillo: bool = True,
) -> bytes:
    """A4: sfondo intestazione (immagine) + prescrizione pulita + TABO con freccia asse cilindro."""
    dati = {
        "paziente": f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip() if isinstance(paziente, dict) else _safe_str(paziente),
        "data": _safe_str(data_prescrizione_iso),
        "od_lon_sf": sf_lon_od, "od_lon_cil": cil_lon_od, "od_lon_ax": ax_lon_od,
        "os_lon_sf": sf_lon_os, "os_lon_cil": cil_lon_os, "os_lon_ax": ax_lon_os,
        "od_int_sf": sf_int_od, "od_int_cil": cil_int_od, "od_int_ax": ax_int_od,
        "os_int_sf": sf_int_os, "os_int_cil": cil_int_os, "os_int_ax": ax_int_os,
        "od_vic_sf": sf_vic_od, "od_vic_cil": cil_vic_od, "od_vic_ax": ax_vic_od,
        "os_vic_sf": sf_vic_os, "os_vic_cil": cil_vic_os, "os_vic_ax": ax_vic_os,
        "lenti": lenti_scelte,
        "altri_trattamenti": altri_trattamenti,
        "note": note,
    }
    return _prescrizione_pdf_imagebg(A4, "a4", con_cirillo, dati)

def genera_prescrizione_occhiali_a4_pdf(
    paziente,
    data_prescrizione_iso: Optional[str],
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
    con_cirillo: bool = True,
) -> bytes:
    """
    A5: SFONDO = immagine letterhead (The Organism) + overlay SOLO valori (tabella pulita).
    Niente riquadri: zero accavallamenti.
    """
    dati = {
        "paziente": f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip() if isinstance(paziente, dict) else _safe_str(paziente),
        "data": _safe_str(data_prescrizione_iso),
        "od_lon_sf": sf_lon_od, "od_lon_cil": cil_lon_od, "od_lon_ax": ax_lon_od,
        "os_lon_sf": sf_lon_os, "os_lon_cil": cil_lon_os, "os_lon_ax": ax_lon_os,
        "od_int_sf": sf_int_od, "od_int_cil": cil_int_od, "od_int_ax": ax_int_od,
        "os_int_sf": sf_int_os, "os_int_cil": cil_int_os, "os_int_ax": ax_int_os,
        "od_vic_sf": sf_vic_od, "od_vic_cil": cil_vic_od, "od_vic_ax": ax_vic_od,
        "os_vic_sf": sf_vic_os, "os_vic_cil": cil_vic_os, "os_vic_ax": ax_vic_os,
        "lenti": lenti_scelte,
        "altri_trattamenti": altri_trattamenti,
        "note": note,
    }
    return _prescrizione_pdf_imagebg(A5, "a5", con_cirillo, dati)

def _draw_crop_marks_for_rect(c, x0, y0, w, h, mark_len_mm: float = 4, inset_mm: float = 2):
    """Crop marks (segni di taglio) ai 4 angoli di un rettangolo."""
    L = mark_len_mm * mm
    inset = inset_mm * mm

    # Bottom-left
    c.line(x0 - L, y0 + inset, x0, y0 + inset)
    c.line(x0 + inset, y0 - L, x0 + inset, y0)

    # Bottom-right
    c.line(x0 + w, y0 + inset, x0 + w + L, y0 + inset)
    c.line(x0 + w - inset, y0 - L, x0 + w - inset, y0)

    # Top-left
    c.line(x0 - L, y0 + h - inset, x0, y0 + h - inset)
    c.line(x0 + inset, y0 + h, x0 + inset, y0 + h + L)

    # Top-right
    c.line(x0 + w, y0 + h - inset, x0 + w + L, y0 + h - inset)
    c.line(x0 + w - inset, y0 + h, x0 + w - inset, y0 + h + L)


def _draw_mid_cut_marks(c, page_w, page_h, mark_len_mm: float = 8):
    """Tacche centrali sui bordi sinistro e destro per taglio a metà pagina."""
    y = page_h / 2.0
    L = mark_len_mm * mm
    c.line(0, y, L, y)
    c.line(page_w - L, y, page_w, y)



def genera_prescrizione_occhiali_a4_pdf(
    paziente,
    data_prescrizione_iso: Optional[str],
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
    divider_line: bool = False,
    con_cirillo: bool = True,
) -> bytes:
    """
    A4: SFONDO = immagine letterhead A4 (The Organism) + overlay SOLO valori (tabella pulita).
    Nota: il nome della funzione resta per compatibilità con la UI.
    """
    dati = {
        "paziente": f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip() if isinstance(paziente, dict) else _safe_str(paziente),
        "data": _safe_str(data_prescrizione_iso),
        "od_lon_sf": sf_lon_od, "od_lon_cil": cil_lon_od, "od_lon_ax": ax_lon_od,
        "os_lon_sf": sf_lon_os, "os_lon_cil": cil_lon_os, "os_lon_ax": ax_lon_os,
        "od_int_sf": sf_int_od, "od_int_cil": cil_int_od, "od_int_ax": ax_int_od,
        "os_int_sf": sf_int_os, "os_int_cil": cil_int_os, "os_int_ax": ax_int_os,
        "od_vic_sf": sf_vic_od, "od_vic_cil": cil_vic_od, "od_vic_ax": ax_vic_od,
        "os_vic_sf": sf_vic_os, "os_vic_cil": cil_vic_os, "os_vic_ax": ax_vic_os,
        "lenti": lenti_scelte,
        "altri_trattamenti": altri_trattamenti,
        "note": note,
    }
    return _prescrizione_pdf_imagebg(A4, "a4", con_cirillo, dati)

def genera_referto_oculistico_a4_pdf(paziente, valutazione, with_header: bool) -> bytes:
    """
    Genera un referto oculistico/optometrico in formato A4.
    - with_header = True  → stampa anche l'intestazione dello studio
    - with_header = False → niente intestazione (usa carta intestata)
    Stampa solo i campi realmente compilati (non vuoti).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    # Sfondo intestazione (immagine A4)
    try:
        variant = "with_cirillo" if with_header else "no_cirillo"
        bg = _find_bg_image('a4', variant)
        _draw_bg_image_fullpage(c, width, height, bg)
    except Exception:
        pass


    left = 25 * mm
    right = width - 25 * mm
    top = height - 40 * mm
    bottom = 25 * mm

    y = top
    # marker di debug: posizione inizio stampa
    c.saveState(); c.setFont('Helvetica', 7); c.drawString(left-8*mm, y+2, '1'); c.restoreState()

    # Intestazione opzionale
    if False and with_header:
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2.0, y, "The Organism – Centro di Neuropsicologia e Sviluppo")
        y -= 14
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2.0, y, "Via De Rosa, 46 – 84016 Pagani (SA)")
        y -= 18

    # Data referto = data valutazione
    data_iso = valutazione["Data_Valutazione"]
    data_it = _format_data_it_from_iso(data_iso) if data_iso else ""
    c.setFont("Helvetica", 10)
    if data_it:
        c.drawRightString(right, y, f"Data referto: {data_it}")
    y -= 20

    # Titolo
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, "Referto oculistico / optometrico")
    y -= 20

    # Dati paziente
    c.setFont("Helvetica", 11)
    nome_paz = f"{paziente['Cognome']} {paziente['Nome']}"
    c.drawString(left, y, f"Paziente: {nome_paz}")
    y -= 14

    # Data nascita + CF se presenti
    dn = paziente["Data_Nascita"]
    cf = (paziente["Codice_Fiscale"] or "").upper() if paziente["Codice_Fiscale"] else ""
    extra_parts = []
    if dn:
        try:
            dn_it = _format_data_it_from_iso(dn)
        except Exception:
            dn_it = dn
        extra_parts.append(f"Nato il: {dn_it}")
    if cf:
        extra_parts.append(f"CF: {cf}")
    if extra_parts:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, " – ".join(extra_parts))
        y -= 14

    # Tipo visita e professionista
    tipo = valutazione["Tipo_Visita"] or ""
    prof = valutazione["Professionista"] or ""
    if tipo:
        c.drawString(left, y, f"Tipo visita: {tipo}")
        y -= 14
    if prof:
        c.drawString(left, y, f"Professionista: {prof}")
        y -= 18

    # Acuità visiva (stampata solo se è stato scritto qualcosa)
    ac_nat_od = valutazione["Acuita_Nat_OD"] or ""
    ac_nat_os = valutazione["Acuita_Nat_OS"] or ""
    ac_nat_oo = valutazione["Acuita_Nat_OO"] or ""
    ac_cor_od = valutazione["Acuita_Corr_OD"] or ""
    ac_cor_os = valutazione["Acuita_Corr_OS"] or ""
    ac_cor_oo = valutazione["Acuita_Corr_OO"] or ""

    if any([ac_nat_od, ac_nat_os, ac_nat_oo, ac_cor_od, ac_cor_os, ac_cor_oo]):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Acuità visiva")
        y -= 14
        c.setFont("Helvetica", 10)

        if any([ac_nat_od, ac_nat_os, ac_nat_oo]):
            parts = []
            if ac_nat_od:
                parts.append(f"OD {ac_nat_od}")
            if ac_nat_os:
                parts.append(f"OS {ac_nat_os}")
            if ac_nat_oo:
                parts.append(f"OO {ac_nat_oo}")
            c.drawString(left + 10, y, "Naturale: " + " – ".join(parts))
            y -= 12

        if any([ac_cor_od, ac_cor_os, ac_cor_oo]):
            parts = []
            if ac_cor_od:
                parts.append(f"OD {ac_cor_od}")
            if ac_cor_os:
                parts.append(f"OS {ac_cor_os}")
            if ac_cor_oo:
                parts.append(f"OO {ac_cor_oo}")
            c.drawString(left + 10, y, "Corretta: " + " – ".join(parts))
            y -= 16

    # Blocco NOTE / refertazione
    note = valutazione["Note"] or ""
    if note.strip():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Esame e refertazione")
        y -= 14
        c.setFont("Helvetica", 10)

        wrapper = textwrap.TextWrapper(width=90)
        for paragraph in note.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                y -= 6
                continue
            for line in wrapper.wrap(paragraph):
                if y < bottom + 50:
                    c.showPage()
                    y = top
                    if with_header:
                        c.setFont("Helvetica-Bold", 12)
                        c.drawCentredString(width / 2.0, y, "The Organism – Centro di Neuropsicologia e Sviluppo")
                        y -= 14
                        c.setFont("Helvetica", 9)
                        c.drawCentredString(width / 2.0, y, "Via De Rosa, 46 – 84016 Pagani (SA)")
                        y -= 18
                        c.setFont("Helvetica", 10)
                c.drawString(left, y, line)
                y -= 12

    # Spazio firma
    if y < bottom + 60:
        c.showPage()
        y = top

    c.setFont("Helvetica", 10)
    c.drawRightString(right, bottom + 40, "_____________________________")
    c.drawRightString(right, bottom + 26, "Firma / Timbro")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()



# -----------------------------
# 🧹 Tool: Pulizia duplicati (solo TEST)
# -----------------------------

def _patient_child_tables():
    # tabelle che referenziano Pazienti(ID) via Paziente_ID
    return [
        ("Valutazione PNEV", "Paziente_ID"),
        ("Valutazioni_Visive", "Paziente_ID"),
        ("Sedute", "Paziente_ID"),
        ("Coupons", "Paziente_ID"),
        ("Consensi_Privacy", "Paziente_ID"),
    ]


def _fetchall_dicts(cur, sql: str, params=()):
    cur.execute(sql, params)
    rows = cur.fetchall()
    out = []
    for r in rows:
        try:
            out.append(dict(r))
        except Exception:
            out.append({str(i): v for i, v in enumerate(r)})
    return out


def db_find_duplicate_cf(cur):
    # duplicati solo per CF non vuoto
    rows = _fetchall_dicts(
        cur,
        '''
        SELECT UPPER(TRIM(Codice_Fiscale)) AS CF, COUNT(*) AS N
        FROM Pazienti
        WHERE Codice_Fiscale IS NOT NULL AND TRIM(Codice_Fiscale) <> ''
        GROUP BY UPPER(TRIM(Codice_Fiscale))
        HAVING COUNT(*) > 1
        ORDER BY N DESC, CF
        ''',
        (),
    )
    groups = []
    for r in rows:
        cf = r.get("CF") or r.get("cf")
        det = _fetchall_dicts(
            cur,
            '''
            SELECT ID, Cognome, Nome, Data_Nascita, Email, Telefono, Stato_Paziente, Codice_Fiscale
            FROM Pazienti
            WHERE UPPER(TRIM(Codice_Fiscale)) = ?
            ORDER BY ID
            ''',
            (cf,),
        )
        groups.append({"key": cf, "kind": "CF", "rows": det})
    return groups


def db_find_duplicate_identity(cur):
    # duplicati per (Cognome, Nome, Data_Nascita) quando presenti
    rows = _fetchall_dicts(
        cur,
        '''
        SELECT
          UPPER(TRIM(Cognome)) AS COG,
          UPPER(TRIM(Nome)) AS NOM,
          COALESCE(TRIM(Data_Nascita),'') AS DN,
          COUNT(*) AS N
        FROM Pazienti
        WHERE TRIM(Cognome) <> '' AND TRIM(Nome) <> ''
        GROUP BY UPPER(TRIM(Cognome)), UPPER(TRIM(Nome)), COALESCE(TRIM(Data_Nascita),'')
        HAVING COUNT(*) > 1
        ORDER BY N DESC, COG, NOM, DN
        ''',
        (),
    )
    groups = []
    for r in rows:
        cog = r.get("COG") or r.get("cog")
        nom = r.get("NOM") or r.get("nom")
        dn = r.get("DN") or r.get("dn") or ""
        det = _fetchall_dicts(
            cur,
            '''
            SELECT ID, Cognome, Nome, Data_Nascita, Email, Telefono, Stato_Paziente, Codice_Fiscale
            FROM Pazienti
            WHERE UPPER(TRIM(Cognome)) = ?
              AND UPPER(TRIM(Nome)) = ?
              AND COALESCE(TRIM(Data_Nascita),'') = ?
            ORDER BY ID
            ''',
            (cog, nom, dn),
        )
        groups.append({"key": f"{cog} | {nom} | {dn or 'SENZA_DATA'}", "kind": "IDENTITA", "rows": det})
    return groups


def _count_refs(cur, paziente_id: int) -> dict:
    counts = {}
    for tbl, col in _patient_child_tables():
        try:
            cur.execute(f"SELECT COUNT(*) AS N FROM {tbl} WHERE {col} = ?", (paziente_id,))
            r = cur.fetchone()
            try:
                n = int(r["N"]) if isinstance(r, dict) else int(r[0])
            except Exception:
                n = int(r[0]) if r else 0
            counts[tbl] = n
        except Exception:
            counts[tbl] = 0
    return counts


def db_merge_patients(cur, master_id: int, dup_ids: list):
    """Sposta tutti i riferimenti (Paziente_ID) dai duplicati verso master_id e cancella i duplicati."""
    report = {"master": int(master_id), "moved": {}, "deleted": [], "errors": []}
    for dup_id in dup_ids:
        dup_id = int(dup_id)
        if dup_id == int(master_id):
            continue
        for tbl, col in _patient_child_tables():
            try:
                cur.execute(f"UPDATE {tbl} SET {col} = ? WHERE {col} = ?", (master_id, dup_id))
                moved = getattr(cur, "rowcount", None)
                report["moved"].setdefault(tbl, 0)
                if moved is not None and moved >= 0:
                    report["moved"][tbl] += int(moved)
            except Exception as e:
                report["errors"].append(f"{tbl}: {e}")
        try:
            cur.execute("DELETE FROM Pazienti WHERE ID = ?", (dup_id,))
            report["deleted"].append(dup_id)
        except Exception as e:
            report["errors"].append(f"DELETE Pazienti({dup_id}): {e}")
    return report


def db_keep_latest_privacy_consent(cur, paziente_id: int):
    """Mantiene SOLO l'ultimo consenso privacy del paziente (per Data_Ora/ID) ed elimina i precedenti."""
    cur.execute(
        "SELECT ID, Data_Ora FROM Consensi_Privacy WHERE Paziente_ID=? ORDER BY COALESCE(Data_Ora,'') DESC, ID DESC",
        (paziente_id,),
    )
    rows = cur.fetchall() or []
    if not rows:
        return {"kept": None, "deleted": 0}

    keep_id = rows[0]["ID"]
    deleted = 0
    if len(rows) > 1:
        cur.execute(
            "DELETE FROM Consensi_Privacy WHERE Paziente_ID=? AND ID<>?",
            (paziente_id, keep_id),
        )
        deleted = len(rows) - 1
    return {"kept": keep_id, "deleted": deleted}


def db_compact_all_privacy_consents(cur):
    """Per ogni paziente, mantiene SOLO l'ultimo consenso privacy."""
    cur.execute("SELECT DISTINCT Paziente_ID FROM Consensi_Privacy")
    pids = [r["Paziente_ID"] for r in (cur.fetchall() or [])]
    total_deleted = 0
    total_patients = 0
    for pid in pids:
        rep = db_keep_latest_privacy_consent(cur, int(pid))
        total_deleted += int(rep.get("deleted", 0))
        total_patients += 1
    return {"patients": total_patients, "deleted": total_deleted}



def ui_db_cleanup():
    st.header("🧹 Pulizia DB (solo TEST)")
    st.warning("Usa questa sezione SOLO in APP_MODE=test (DB TEST).")

    conn = get_connection()
    cur = conn.cursor()

    tab1, tab2 = st.tabs(["Duplicati per Codice Fiscale", "Duplicati per Identità (nome/cognome/data)"])

    with st.expander("🧾 Compatta consensi privacy (tieni solo l'ultimo)", expanded=False):
        st.write("Elimina i consensi privacy precedenti e lascia SOLO l'ultimo per ogni paziente (DB TEST).")
        conf = st.text_input("Per confermare scrivi: COMPACT", key="compact_confirm")
        if st.button("Esegui compattazione consensi (tutti i pazienti)", disabled=(conf.strip().upper() != "COMPACT")):
            try:
                repc = db_compact_all_privacy_consents(cur)
                conn.commit()
                st.success(f"Compattazione completata: pazienti analizzati={repc['patients']}, consensi eliminati={repc['deleted']}.")
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Errore compattazione: {e}")


    def _render(groups, key_prefix: str):
        if not groups:
            st.success("Nessun duplicato trovato 🎉")
            return

        keys = [f"{g['kind']}: {g['key']} ({len(g['rows'])} record)" for g in groups]
        sel = st.selectbox("Seleziona un gruppo da analizzare", keys, key=f"{key_prefix}_grp")
        g = groups[keys.index(sel)]
        rows = g["rows"]

        st.markdown("### Record nel gruppo")
        for r in rows:
            pid = int(r.get("ID") or r.get("id") or 0)
            st.write(
                f"**ID {pid}** — {r.get('Cognome','')} {r.get('Nome','')} | DN: {r.get('Data_Nascita','') or ''} | CF: {r.get('Codice_Fiscale','') or ''} | Email: {r.get('Email','') or ''}"
            )
            counts = _count_refs(cur, pid)
            st.caption("Riferimenti: " + ", ".join([f"{k}={v}" for k, v in counts.items()]))

        ids = [int(r.get("ID") or r.get("id")) for r in rows]
        master_id = st.selectbox("Scegli il record MASTER (quello da tenere)", ids, key=f"{key_prefix}_master")
        dup_ids = [i for i in ids if i != master_id]

        st.info(f"Sposterò i riferimenti da {dup_ids} verso MASTER {master_id}, poi eliminerò i duplicati.")

        confirm = st.text_input("Per confermare scrivi: MERGE", key=f"{key_prefix}_confirm")
        if st.button("Esegui MERGE", type="primary", key=f"{key_prefix}_go", disabled=(confirm.strip().upper() != "MERGE")):
            try:
                rep = db_merge_patients(cur, master_id=master_id, dup_ids=dup_ids)
                conn.commit()
                st.success(f"Merge completato. Master: {master_id}. Eliminati: {rep['deleted']}")
                # Dopo merge: mantieni SOLO l'ultimo consenso privacy (come richiesto)
                try:
                    rep2 = db_keep_latest_privacy_consent(cur, paziente_id=master_id)
                    conn.commit()
                    st.info(f"Consensi_Privacy: tenuto ID {rep2.get('kept')} — eliminati {rep2.get('deleted')} consensi precedenti.")
                except Exception as e:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    st.warning(f"Merge ok, ma non sono riuscito a compattare i consensi privacy: {e}")
                if rep["moved"]:
                    st.write("Spostamenti:", rep["moved"])
                if rep["errors"]:
                    st.error("Alcuni errori:")
                    for e in rep["errors"]:
                        st.write(e)
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Merge fallito: {e}")

    with tab1:
        _render(db_find_duplicate_cf(cur), "cf")

    with tab2:
        _render(db_find_duplicate_identity(cur), "id")

    conn.close()


def ui_pazienti():
    st.header("Pazienti")

    conn = get_connection()
    cur = conn.cursor()

    # --- Tool CF separato (facoltativo) ---
    with st.expander("Tool di supporto per generare il Codice Fiscale"):
        st.write("Usalo come aiuto quando il paziente non ricorda il CF. Copia il risultato nel campo CF dell'anagrafica.")
        with st.form("cf_tool"):
            cogn_t = st.text_input("Cognome", key="cf_cognome")
            nome_t = st.text_input("Nome", key="cf_nome")
            data_t = st.text_input("Data di nascita (gg/mm/aaaa)", key="cf_data")
            sesso_t = st.selectbox("Sesso", ["", "M", "F", "Altro"], key="cf_sesso")
            comune_n_t = st.text_input("Comune di nascita (es. Pagani)", key="cf_comune")
            prov_n_t = st.text_input("Provincia di nascita (sigla, es. SA)", key="cf_prov")
            calcola = st.form_submit_button("Calcola CF")
            if calcola:
                cf_gen = genera_codice_fiscale(
                    cognome=cogn_t,
                    nome=nome_t,
                    data_nascita_str=data_t,
                    sesso=sesso_t,
                    comune_nascita=comune_n_t,
                    provincia_nascita=prov_n_t,
                )
                if cf_gen is None:
                    st.error(
                        "Impossibile generare il codice fiscale: controlla i dati e che il comune sia previsto nel file dei codici catastali."
                    )
                else:
                    st.success(f"Codice fiscale generato: **{cf_gen}**")
                    st.info("Copia questo codice nel campo 'Codice fiscale' del paziente.")

    st.markdown("---")
    st.subheader("Nuovo paziente")

    # --- Nuovo paziente ---
    with st.form("nuovo_paziente"):
        col1, col2 = st.columns(2)
        with col1:
            cognome = st.text_input("Cognome", "")
            data_nascita_str = st.text_input("Data di nascita (gg/mm/aaaa)", "")
        with col2:
            nome = st.text_input("Nome", "")
            sesso = st.selectbox("Sesso", ["", "M", "F", "Altro"])

        col3, col4, col5 = st.columns(3)
        with col3:
            indirizzo = st.text_input("Indirizzo (via, numero civico)", "")
        with col4:
            cap = st.text_input("CAP", "")
        with col5:
            provincia = st.text_input("Provincia (sigla, es. SA)", "")

        col6, col7 = st.columns(2)
        with col6:
            citta = st.text_input("Città / Comune di residenza", "")
        with col7:
            codice_fiscale = st.text_input("Codice fiscale", "").upper()

        col8, col9 = st.columns(2)
        with col8:
            telefono = st.text_input("Telefono", "")
        with col9:
            email = st.text_input("Email", "")


        st.markdown("### Privacy e Consensi (GDPR)")
        st.caption("I consensi vengono registrati nel gestionale. Le opzioni marketing fanno riferimento a Klaviyo (piattaforma e-mail/SMS marketing) per l'invio di comunicazioni e offerte, solo se autorizzato.")

        tipo_privacy = st.radio("Tipo di privacy", ["Adulto", "Minore"], horizontal=True)

        tutore_nome = tutore_cf = tutore_tel = tutore_email = ""
        if tipo_privacy == "Minore":
            st.markdown("**Dati del genitore/tutore**")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tutore_nome = st.text_input("Nome e cognome tutore", "")
                tutore_tel = st.text_input("Telefono tutore", "")
            with col_t2:
                tutore_cf = st.text_input("Codice fiscale tutore", "").upper()
                tutore_email = st.text_input("Email tutore", "")

        st.markdown("**Consensi**")
        consenso_trattamento = st.checkbox("✅ Consenso al trattamento dei dati personali per finalità cliniche/gestionali (obbligatorio)", value=False)
        consenso_comunicazioni = st.checkbox("Consenso a comunicazioni di servizio (appuntamenti, referti, promemoria)", value=True)

        st.markdown("**Canali di comunicazione autorizzati**")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            canale_email = st.checkbox("Email", value=True)
        with col_c2:
            canale_sms = st.checkbox("SMS", value=False)
        with col_c3:
            canale_whatsapp = st.checkbox("WhatsApp", value=True)

        st.markdown("**Marketing / offerte (facoltativo)**")
        consenso_marketing = st.checkbox("Consenso a ricevere comunicazioni promozionali, offerte e contenuti informativi", value=False)
        usa_klaviyo = st.checkbox("Autorizzo l'uso di Klaviyo per la gestione di newsletter/SMS marketing (solo se marketing attivo)", value=False)

        note_privacy = st.text_area("Note privacy (facoltative)", "")

        salva = st.form_submit_button("Salva paziente")

    # --- Salvataggio nuovo paziente ---
    
    # --- Salvataggio nuovo paziente ---
    if salva:
        if not cognome or not nome:
            st.error("Cognome e Nome sono obbligatori.")
            conn.close()
            return

        if not consenso_trattamento:
            st.error("Per salvare il paziente devi acquisire il consenso al trattamento dati (obbligatorio).")
            conn.close()
            return

        # Gestione data di nascita (formato gg/mm/aaaa)
        data_iso = None
        if data_nascita_str.strip():
            try:
                d = datetime.strptime(data_nascita_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data di nascita non valida. Usa il formato gg/mm/aaaa (es. 19/01/1975).")
                conn.close()
                return

        # Codice fiscale (opzionale) con controllo
        cf_clean = (codice_fiscale or "").strip().upper()
        if cf_clean and not valida_codice_fiscale(cf_clean):
            st.warning(
                "Il codice fiscale inserito non sembra valido rispetto all'algoritmo di controllo. "
                "Puoi comunque salvarlo, ma verifica con attenzione."
            )

        # Inserimento paziente + recupero ID
        paz_id = None
        try:
            if _DB_BACKEND == "postgres":
                cur.execute(
                    """
                    INSERT INTO Pazienti
                    (Cognome, Nome, Data_Nascita, Sesso, Telefono, Email,
                     Indirizzo, CAP, Citta, Provincia, Codice_Fiscale, Stato_Paziente)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    RETURNING ID
                    """,
                    (
                        cognome.strip(),
                        nome.strip(),
                        data_iso,
                        sesso,
                        telefono.strip(),
                        email.strip(),
                        indirizzo.strip(),
                        cap.strip(),
                        citta.strip(),
                        provincia.strip().upper(),
                        cf_clean or None,
                        "ATTIVO",
                    ),
                )
                row = cur.fetchone()
                # RowCI wrapper supports ["ID"] and ["id"]
                paz_id = int(row["ID"]) if isinstance(row, dict) else int(row[0])
            else:
                cur.execute(
                    """
                    INSERT INTO Pazienti
                    (Cognome, Nome, Data_Nascita, Sesso, Telefono, Email,
                     Indirizzo, CAP, Citta, Provincia, Codice_Fiscale, Stato_Paziente)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        cognome.strip(),
                        nome.strip(),
                        data_iso,
                        sesso,
                        telefono.strip(),
                        email.strip(),
                        indirizzo.strip(),
                        cap.strip(),
                        citta.strip(),
                        provincia.strip().upper(),
                        cf_clean or None,
                        "ATTIVO",
                    ),
                )
                try:
                    paz_id = int(getattr(cur, "lastrowid", None) or 0) or None
                except Exception:
                    paz_id = None

            now_iso = datetime.now().isoformat(timespec="seconds")
            tipo_db = "MINORE" if (tipo_privacy == "Minore") else "ADULTO"
            cur.execute(
                """
                INSERT INTO Consensi_Privacy
                (Paziente_ID, Data_Ora, Tipo, Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
                 Consenso_Trattamento, Consenso_Comunicazioni, Consenso_Marketing,
                 Canale_Email, Canale_SMS, Canale_WhatsApp, Usa_Klaviyo, Note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    paz_id,
                    now_iso,
                    tipo_db,
                    (tutore_nome or "").strip(),
                    (tutore_cf or "").strip().upper(),
                    (tutore_tel or "").strip(),
                    (tutore_email or "").strip(),
                    1 if consenso_trattamento else 0,
                    1 if consenso_comunicazioni else 0,
                    1 if consenso_marketing else 0,
                    1 if canale_email else 0,
                    1 if canale_sms else 0,
                    1 if canale_whatsapp else 0,
                    1 if (usa_klaviyo and consenso_marketing) else 0,
                    (note_privacy or "").strip(),
                ),
            )

            conn.commit()
            st.success("Paziente salvato correttamente (privacy registrata).")

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            st.error("Errore durante il salvataggio del paziente/privacy.")
            st.write(str(e))

    st.markdown("---")
    st.subheader("Elenco pazienti")

    # Filtro ricerca
    filtro = st.text_input("Cerca per cognome/nome/codice fiscale", "")

    query = "SELECT * FROM Pazienti"
    params = []
    if filtro.strip():
        query += " WHERE Cognome LIKE ? OR Nome LIKE ? OR Codice_Fiscale LIKE ?"
        like = f"%{filtro.strip()}%"
        params = [like, like, like]
    query += " ORDER BY Cognome, Nome"

    cur.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        st.info("Nessun paziente trovato.")
        conn.close()
        return

    # Etichette ricche: ID + Cognome Nome + data nascita + CF
    options = []
    for r in rows:
        nascita_it = ""
        if r["Data_Nascita"]:
            try:
                nascita_it = datetime.strptime(r["Data_Nascita"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                nascita_it = r["Data_Nascita"]
        cf = (r["Codice_Fiscale"] or "").upper()
        label = f"{r['ID']} - {r['Cognome']} {r['Nome']}"
        extra = []
        if nascita_it:
            extra.append(f"nato il {nascita_it}")
        if cf:
            extra.append(f"CF: {cf}")
        if extra:
            label += " (" + " | ".join(extra) + ")"
        options.append(label)

    selected = st.selectbox("Seleziona un paziente per modificare / archiviare", options, key="pz_sel_mod")
    sel_id = int(selected.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == sel_id)

    st.write(f"Stato attuale: **{rec['Stato_Paziente']}**")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Archivia paziente", key="archivia"):
            cur.execute("UPDATE Pazienti SET Stato_Paziente = 'ARCHIVIATO' WHERE ID = ?", (sel_id,))
            conn.commit()
            st.success("Paziente archiviato.")
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
    with col_b:
        if st.button("Riattiva paziente", key="riattiva"):
            cur.execute("UPDATE Pazienti SET Stato_Paziente = 'ATTIVO' WHERE ID = ?", (sel_id,))
            conn.commit()
            st.success("Paziente riattivato.")
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
    with col_c:
        if st.button("Elimina definitivamente", key="elimina"):
            cur.execute("DELETE FROM Anamnesi WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Valutazioni_Visive WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Sedute WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Coupons WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Pazienti WHERE ID = ?", (sel_id,))
            conn.commit()
            st.success("Paziente e dati associati eliminati.")
            conn.close()
            st.stop()

    st.markdown("### Modifica dati paziente")
    with st.form("modifica_paziente"):
        col1, col2 = st.columns(2)
        with col1:
            cognome_m = st.text_input("Cognome", rec["Cognome"] or "", key=f"m_cognome_{sel_id}")
            data_nascita_m = st.text_input(
                "Data di nascita (gg/mm/aaaa)",
                datetime.strptime(rec["Data_Nascita"], "%Y-%m-%d").strftime("%d/%m/%Y")
                if rec["Data_Nascita"] else "",
                key=f"m_data_nascita_{sel_id}",
            )
        with col2:
            nome_m = st.text_input("Nome", rec["Nome"] or "", key=f"m_nome_{sel_id}")
            sesso_m = st.selectbox(
                "Sesso",
                ["", "M", "F", "Altro"],
                index=(["", "M", "F", "Altro"].index(rec["Sesso"]) if rec["Sesso"] in ["", "M", "F", "Altro"] else 0),
                key=f"m_sesso_{sel_id}",
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            indirizzo_m = st.text_input("Indirizzo", rec["Indirizzo"] or "", key=f"m_indirizzo_{sel_id}")
        with col4:
            cap_m = st.text_input("CAP", rec["CAP"] or "", key=f"m_cap_{sel_id}")
        with col5:
            provincia_m = st.text_input("Provincia", rec["Provincia"] or "", key=f"m_provincia_{sel_id}")

        col6, col7 = st.columns(2)
        with col6:
            citta_m = st.text_input("Città", rec["Citta"] or "", key=f"m_citta_{sel_id}")
        with col7:
            cf_m = st.text_input("Codice fiscale", (rec["Codice_Fiscale"] or "").upper(), key=f"m_cf_{sel_id}")

        col8, col9 = st.columns(2)
        with col8:
            telefono_m = st.text_input("Telefono", rec["Telefono"] or "", key=f"m_tel_{sel_id}")
        with col9:
            email_m = st.text_input("Email", rec["Email"] or "", key=f"m_email_{sel_id}")

        stato_m = st.selectbox(
            "Stato paziente",
            ["ATTIVO", "ARCHIVIATO"],
            index=(0 if (rec["Stato_Paziente"] or "ATTIVO") == "ATTIVO" else 1),
            key=f"m_stato_{sel_id}",
        )

        salva_mod = st.form_submit_button("Salva modifiche")

    if salva_mod:
        if not cognome_m or not nome_m:
            st.error("Cognome e Nome sono obbligatori.")
        else:
            data_iso_m = None
            if data_nascita_m.strip():
                try:
                    d = datetime.strptime(data_nascita_m.strip(), "%d/%m/%Y").date()
                    data_iso_m = d.isoformat()
                except ValueError:
                    st.error("Data di nascita non valida. Usa il formato gg/mm/aaaa.")
                    conn.close()
                    return

            cf_clean_m = (cf_m or "").strip().upper()
            if cf_clean_m and not valida_codice_fiscale(cf_clean_m):
                st.warning(
                    "Il codice fiscale inserito non sembra valido rispetto all'algoritmo di controllo. "
                    "Puoi comunque salvarlo, ma verifica con attenzione."
                )

            cur.execute(
                """
                UPDATE Pazienti
                SET Cognome = ?, Nome = ?, Data_Nascita = ?, Sesso = ?,
                    Telefono = ?, Email = ?, Indirizzo = ?, CAP = ?, Citta = ?, Provincia = ?,
                    Codice_Fiscale = ?, Stato_Paziente = ?
                WHERE ID = ?
                """,
                (
                    cognome_m.strip(),
                    nome_m.strip(),
                    data_iso_m,
                    sesso_m,
                    telefono_m.strip(),
                    email_m.strip(),
                    indirizzo_m.strip(),
                    cap_m.strip(),
                    citta_m.strip(),
                    provincia_m.strip().upper(),
                    cf_clean_m or None,
                    stato_m,
                    sel_id,
                ),
            )
            conn.commit()
            st.success("Dati paziente aggiornati.")

    conn.close()



    # -----------------------------
    # UI: Anamnesi
    # -----------------------------

def ui_anamnesi():
    # UI: Valutazione PNEV (ex Anamnesi) — scheda scalabile via JSON
    st.header("Valutazione PNEV")

    conn = get_connection()
    cur = conn.cursor()

    # Seleziona paziente
    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    options = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options)
    paz_id = int(sel.split(" - ", 1)[0])

    # --- Migrazione legacy -> PNEV (sicura, non sovrascrive) ---
    with st.expander("🧬 Migrazione legacy → PNEV", expanded=False):
        st.caption("Popola pnev_json/pnev_summary per le vecchie schede (che avevano solo testo libero). Non sovrascrive schede già migrate.")
        colm1, colm2 = st.columns([1, 1])
        with colm1:
            do_migrate_this = st.button("Migra SOLO questo paziente", key="migrate_pnev_this")
        with colm2:
            do_migrate_all = st.button("Migra TUTTI i pazienti (TEST)", key="migrate_pnev_all")

        if do_migrate_this or do_migrate_all:
            try:
                pid = None if do_migrate_all else paz_id
                stats = migrate_anamnesi_legacy_to_pnev(cur, paziente_id=pid, limit=100000)
                conn.commit()
                st.success(
                    f"Scansionate: {stats['scanned']} | Aggiornate: {stats['updated']} | "
                    f"Già migrate: {stats['skipped_has_pnev']} | Vuote: {stats['skipped_no_content']}"
                )
                st.rerun()
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Errore migrazione: {e}")


    # -----------------------------
    # NUOVA VALUTAZIONE PNEV
    # -----------------------------
    with st.form("nuova_pnev"):
        st.subheader("Nuova Valutazione PNEV")

        data_str = st.text_input("Data (gg/mm/aaaa)", datetime.today().strftime("%d/%m/%Y"))
        motivo = st.text_area("Domanda clinica / motivo dell'invio")

        # visita_snapshot qui può essere minimale (questa sezione è trasversale, non solo visiva)
        visita_snapshot = {"paziente_id": paz_id, "motivo": motivo}

        pnev_data_new, pnev_summary_new = pnev.pnev_collect_ui(prefix="pnev_new", visita=visita_snapshot, existing=None)

        # --- Questionario INPPS (Genitori) agganciato al PNEV ---
        inpps_existing = (pnev_data_new.get("questionari", {}) or {}).get("inpps_screening_genitori") if isinstance(pnev_data_new, dict) else None
        inpps_data_new, inpps_summary_new = inpps_collect_ui(prefix="inpps_new", existing=inpps_existing)
        # merge nel PNEV JSON scalabile
        try:
            pnev_data_new.setdefault("questionari", {})
            pnev_data_new["questionari"]["inpps_screening_genitori"] = inpps_data_new
        except Exception:
            pass
        # aggiorna summary (non distruttivo)
        if inpps_summary_new and (inpps_summary_new not in (pnev_summary_new or "")):
            pnev_summary_new = ((pnev_summary_new or "").strip() + "\n" + inpps_summary_new).strip()

        note = st.text_area("Note cliniche aggiuntive (per uso interno)")

        col_ai1, col_ai2, col_save = st.columns([1, 1, 1])
        with col_ai1:
            ai_hyp = st.form_submit_button("🤖 IA: bozza ipotesi", help="Genera una bozza (TEST) basata su PNEV compilata.")
        with col_ai2:
            ai_plan = st.form_submit_button("🤖 IA: bozza piano", help="Genera obiettivi/piano (TEST) basati su PNEV.")
        with col_save:
            salva = st.form_submit_button("Salva Valutazione PNEV")

    # --- IA helper (TEST only) ---
    if 'ai_hyp' in locals() and (ai_hyp or ai_plan):
        if not _ai_enabled():
            st.warning("IA disattivata. Abilitala solo in TEST nei Secrets: [ai] ENABLED=true")
        else:
            if not PNEV_AI_AVAILABLE or pnev_ai is None:
                st.warning("Stub IA non disponibile (pnev_ai.py non importabile).")
            else:
                try:
                    if ai_hyp:
                        sug = pnev_ai.generate_hypothesis(visita_snapshot, pnev_data_new)
                        pnev_ai.apply_to_session("pnev_new", sug)
                        st.success("Bozza ipotesi applicata ai campi PNEV (modificabile).")
                        st.rerun()
                    if ai_plan:
                        sug = pnev_ai.generate_plan(visita_snapshot, pnev_data_new)
                        pnev_ai.apply_to_session("pnev_new", sug)
                        st.success("Bozza piano applicata ai campi PNEV (modificabile).")
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore IA (stub): {e}")

    if 'salva' in locals() and salva:
        data_iso = None
        if data_str.strip():
            try:
                d = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return

        # Compatibilità: Motivo e Storia restano popolati, ma la fonte principale è pnev_json/pnev_summary
        storia = (pnev_summary_new or "").strip()
        try:
            pnev_dumped = pnev.pnev_dump(pnev_data_new)
        except Exception:
            pnev_dumped = "{}"

        cur.execute(
            """
            INSERT INTO Anamnesi (Paziente_ID, Data_Anamnesi, Motivo, Storia, Note, pnev_json, pnev_summary)
            VALUES (?,?,?,?,?,?,?)
            """,
            (paz_id, data_iso, motivo, storia, note, pnev_dumped, (pnev_summary_new or "")),
        )
        conn.commit()
        st.success("Valutazione PNEV salvata.")
        st.rerun()

    st.markdown("---")
    st.subheader("Valutazioni PNEV esistenti")

    cur.execute(
        "SELECT * FROM Anamnesi WHERE Paziente_ID = ? ORDER BY Data_Anamnesi DESC, ID DESC",
        (paz_id,),
    )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna Valutazione PNEV per questo paziente.")
        conn.close()
        return

    labels = [
        f"{r['ID']} - {r['Data_Anamnesi'] or ''} - { (r['Motivo'][:40] + '...') if r['Motivo'] and len(r['Motivo'])>40 else (r['Motivo'] or '') }"
        for r in rows
    ]
    sel_an = st.selectbox("Seleziona una Valutazione PNEV da modificare/cancellare", labels)
    an_id = int(sel_an.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == an_id)

    # carica json PNEV esistente (fallback: se manca usa {})
    try:
        existing_pnev_raw = rec.get("pnev_json") if hasattr(rec, "get") else None
    except Exception:
        existing_pnev_raw = None
    pnev_existing = pnev.pnev_load(existing_pnev_raw)

    with st.form("modifica_pnev"):
        data_m = st.text_input(
            "Data (gg/mm/aaaa)",
            datetime.strptime(rec["Data_Anamnesi"], "%Y-%m-%d").strftime("%d/%m/%Y")
            if rec["Data_Anamnesi"] else "",
        )
        motivo_m = st.text_area("Domanda clinica / motivo", rec["Motivo"] or "")

        visita_snapshot_m = {"paziente_id": paz_id, "motivo": motivo_m}
        pnev_data_m, pnev_summary_m = pnev.pnev_collect_ui(prefix=f"pnev_edit_{an_id}", visita=visita_snapshot_m, existing=pnev_existing)

        # --- Questionario INPPS (Genitori) agganciato al PNEV ---
        inpps_existing_m = (pnev_data_m.get("questionari", {}) or {}).get("inpps_screening_genitori") if isinstance(pnev_data_m, dict) else None
        inpps_data_m, inpps_summary_m2 = inpps_collect_ui(prefix=f"inpps_edit_{an_id}", existing=inpps_existing_m)
        try:
            pnev_data_m.setdefault("questionari", {})
            pnev_data_m["questionari"]["inpps_screening_genitori"] = inpps_data_m
        except Exception:
            pass
        if inpps_summary_m2 and (inpps_summary_m2 not in (pnev_summary_m or "")):
            pnev_summary_m = ((pnev_summary_m or "").strip() + "\n" + inpps_summary_m2).strip()

        note_m = st.text_area("Note cliniche aggiuntive (per uso interno)", rec["Note"] or "")

        col_ai1, col_ai2, col_save, col_del = st.columns([1, 1, 1, 1])
        with col_ai1:
            ai_hyp_m = st.form_submit_button("🤖 IA: bozza ipotesi", help="Genera una bozza (TEST) basata su PNEV.")
        with col_ai2:
            ai_plan_m = st.form_submit_button("🤖 IA: bozza piano", help="Genera obiettivi/piano (TEST) basati su PNEV.")
        with col_save:
            salva_m = st.form_submit_button("Salva modifiche")
        with col_del:
            cancella = st.form_submit_button("Elimina Valutazione PNEV")

    # --- IA helper (TEST only) per modifica ---
    if 'ai_hyp_m' in locals() and (ai_hyp_m or ai_plan_m):
        if not _ai_enabled():
            st.warning("IA disattivata. Abilitala solo in TEST nei Secrets: [ai] ENABLED=true")
        else:
            if not PNEV_AI_AVAILABLE or pnev_ai is None:
                st.warning("Stub IA non disponibile (pnev_ai.py non importabile).")
            else:
                try:
                    if ai_hyp_m:
                        sug = pnev_ai.generate_hypothesis(visita_snapshot_m, pnev_data_m)
                        pnev_ai.apply_to_session(f"pnev_edit_{an_id}", sug)
                        st.success("Bozza ipotesi applicata ai campi PNEV (modificabile).")
                        st.rerun()
                    if ai_plan_m:
                        sug = pnev_ai.generate_plan(visita_snapshot_m, pnev_data_m)
                        pnev_ai.apply_to_session(f"pnev_edit_{an_id}", sug)
                        st.success("Bozza piano applicata ai campi PNEV (modificabile).")
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore IA (stub): {e}")

    if 'salva_m' in locals() and salva_m:
        data_iso_m = None
        if data_m.strip():
            try:
                d = datetime.strptime(data_m.strip(), "%d/%m/%Y").date()
                data_iso_m = d.isoformat()
            except ValueError:
                st.error("Data non valida.")
                conn.close()
                return

        try:
            pnev_dumped_m = pnev.pnev_dump(pnev_data_m)
        except Exception:
            pnev_dumped_m = "{}"

        cur.execute(
            """
            UPDATE Anamnesi
            SET Data_Anamnesi = ?, Motivo = ?, Storia = ?, Note = ?, pnev_json = ?, pnev_summary = ?
            WHERE ID = ?
            """,
            (data_iso_m, motivo_m, (pnev_summary_m or ""), note_m, pnev_dumped_m, (pnev_summary_m or ""), an_id),
        )
        conn.commit()
        st.success("Valutazione PNEV aggiornata.")
        st.rerun()

    if 'cancella' in locals() and cancella:
        cur.execute("DELETE FROM Anamnesi WHERE ID = ?", (an_id,))
        conn.commit()
        st.success("Valutazione PNEV eliminata.")
        st.rerun()

    conn.close()


# -----------------------------
# UI: Valutazioni visive / oculistiche
# -----------------------------

def ui_valutazioni_visive():
    st.header("Valutazioni visive / oculistiche")

    conn = get_connection()
    cur = conn.cursor()

    # Seleziona paziente
    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    options = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options)
    paz_id = int(sel.split(" - ", 1)[0])
    # Recupero anagrafica completa del paziente (serve per referti e prescrizioni)
    cur.execute("SELECT * FROM Pazienti WHERE ID = ?", (paz_id,))
    paziente = cur.fetchone()


    with st.form("nuova_val_visiva"):
        st.subheader("Nuova valutazione visiva / oculistica")
        data_str = st.text_input("Data (gg/mm/aaaa)", datetime.today().strftime("%d/%m/%Y"))
        tipo = st.text_input("Tipo visita (es. Valutazione optometrica, controllo, ecc.)")
        professionista = st.text_input("Professionista", "")

        st.markdown("### Acuità visiva")

        st.markdown("**Acuità naturale**")
        col1, col2, col3 = st.columns(3)
        with col1:
            ac_nat_od = av_select("OD (naturale)", "", key="ac_nat_od_new")
        with col2:
            ac_nat_os = av_select("OS (naturale)", "", key="ac_nat_os_new")
        with col3:
            ac_nat_oo = av_select("OO (naturale)", "", key="ac_nat_oo_new")

        st.markdown("**Acuità corretta**")
        col4, col5, col6 = st.columns(3)
        with col4:
            ac_cor_od = av_select("OD (corretta)", "", key="ac_cor_od_new")
        with col5:
            ac_cor_os = av_select("OS (corretta)", "", key="ac_cor_os_new")
        with col6:
            ac_cor_oo = av_select("OO (corretta)", "", key="ac_cor_oo_new")

        st.markdown("### Refrazione")

        st.markdown("**Refrazione oggettiva (SF / CIL / AX)**")
        col_od1, col_od2, col_od3 = st.columns(3)
        with col_od1:
            sf_ogg_od = st.number_input("OD SF oggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_ogg_od")
        with col_od2:
            cil_ogg_od = st.number_input("OD CIL oggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_ogg_od")
        with col_od3:
            ax_ogg_od = st.number_input("OD AX oggettiva (°)", 0, 180, 0, 1, key="ax_ogg_od")

        col_os1, col_os2, col_os3 = st.columns(3)
        with col_os1:
            sf_ogg_os = st.number_input("OS SF oggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_ogg_os")
        with col_os2:
            cil_ogg_os = st.number_input("OS CIL oggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_ogg_os")
        with col_os3:
            ax_ogg_os = st.number_input("OS AX oggettiva (°)", 0, 180, 0, 1, key="ax_ogg_os")

        st.markdown("**Refrazione soggettiva (SF / CIL / AX)**")
        col_od4, col_od5, col_od6 = st.columns(3)
        with col_od4:
            sf_sogg_od = st.number_input("OD SF soggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_sogg_od")
        with col_od5:
            cil_sogg_od = st.number_input("OD CIL soggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_sogg_od")
        with col_od6:
            ax_sogg_od = st.number_input("OD AX soggettiva (°)", 0, 180, 0, 1, key="ax_sogg_od")

        col_os4, col_os5, col_os6 = st.columns(3)
        with col_os4:
            sf_sogg_os = st.number_input("OS SF soggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_sogg_os")
        with col_os5:
            cil_sogg_os = st.number_input("OS CIL soggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_sogg_os")
        with col_os6:
            ax_sogg_os = st.number_input("OS AX soggettiva (°)", 0, 180, 0, 1, key="ax_sogg_os")

        st.markdown("### Cheratometria")
        col_kod1, col_kod2, col_kod3, col_kod4 = st.columns(4)
        with col_kod1:
            k1_od_mm = st.number_input("OD K1 (mm)", 6.0, 9.5, 7.80, 0.01, key="k1_od_mm")
        with col_kod2:
            k1_od_D = st.number_input("OD K1 (D)", 35.0, 50.0, 43.00, 0.25, key="k1_od_D")
        with col_kod3:
            k2_od_mm = st.number_input("OD K2 (mm)", 6.0, 9.5, 7.80, 0.01, key="k2_od_mm")
        with col_kod4:
            k2_od_D = st.number_input("OD K2 (D)", 35.0, 50.0, 43.00, 0.25, key="k2_od_D")

        col_kos1, col_kos2, col_kos3, col_kos4 = st.columns(4)
        with col_kos1:
            k1_os_mm = st.number_input("OS K1 (mm)", 6.0, 9.5, 7.80, 0.01, key="k1_os_mm")
        with col_kos2:
            k1_os_D = st.number_input("OS K1 (D)", 35.0, 50.0, 43.00, 0.25, key="k1_os_D")
        with col_kos3:
            k2_os_mm = st.number_input("OS K2 (mm)", 6.0, 9.5, 7.80, 0.01, key="k2_os_mm")
        with col_kos4:
            k2_os_D = st.number_input("OS K2 (D)", 35.0, 50.0, 43.00, 0.25, key="k2_os_D")

        st.markdown("### Tonometria / Pressione oculare")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tono_od = st.number_input("Tonometria OD (mmHg)", 0.0, 60.0, 15.0, 0.5, key="tono_od")
        with col_t2:
            tono_os = st.number_input("Tonometria OS (mmHg)", 0.0, 60.0, 15.0, 0.5, key="tono_os")

        st.markdown("### Motilità, cover test, stereopsi, PPC")
        motilita = st.text_input("Motilità oculare", "")
        cover_test = st.text_input("Cover test (lontano/vicino, OD/OS)", "")
        stereopsi = st.text_input("Stereopsi (secondi d'arco / test)", "")
        ppc_cm = st.number_input("PPC (punto prossimo di convergenza, cm)", 0.0, 50.0, 10.0, 0.5, key="ppc_cm")

        st.markdown("### Colori, pachimetria, esami di struttura/funzione")
        ishihara = st.text_input("Tavole di Ishihara (esito)", "")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            pachim_od = st.number_input("Pachimetria OD (µm)", 400.0, 700.0, 540.0, 1.0, key="pachim_od")
        with col_p2:
            pachim_os = st.number_input("Pachimetria OS (µm)", 400.0, 700.0, 540.0, 1.0, key="pachim_os")

        fondo = st.text_area("Fondo oculare (descrizione)", "")
        campo_visivo = st.text_area("Campo visivo (descrizione / esito)", "")
        oct = st.text_area("OCT (descrizione)", "")
        topo = st.text_area("Topografia corneale (descrizione)", "")


        st.markdown("### Esame obiettivo (strutture oculari)")
        cornea = st.text_area("Cornea", "")
        camera_ant = st.text_area("Camera anteriore", "")
        cristallino = st.text_area("Cristallino", "")
        congiuntiva = st.text_area("Congiuntiva / Sclera", "")
        iride_pupilla = st.text_area("Iride / Pupilla", "")
        vitreo = st.text_area("Vitreo", "")


        col7, col8 = st.columns(2)
        with col7:
            costo = st.number_input("Costo visita", min_value=0.0, step=5.0, value=0.0)
        with col8:
            pagato = st.checkbox("Pagato", value=False)

        note_libere = st.text_area("Note cliniche libere (aggiuntive)")

        # --- PNEV (Psico‑Neuro‑Evolutivo) – struttura scalabile ---
        visita_snapshot = pnev.pnev_pack_visita(
            Acuita_Nat_OD=ac_nat_od, Acuita_Nat_OS=ac_nat_os, Acuita_Nat_OO=ac_nat_oo,
            Acuita_Corr_OD=ac_cor_od, Acuita_Corr_OS=ac_cor_os, Acuita_Corr_OO=ac_cor_oo,
            Tonometria_OD=tono_od, Tonometria_OS=tono_os,
            Motilita=motilita, Cover_Test=cover_test, Stereopsi=stereopsi, PPC=ppc_cm,
            Ishihara=ishihara,
        )
        pnev_data_new, pnev_summary_new = pnev.pnev_collect_ui(prefix="pnev_new", visita=visita_snapshot, existing=None)

        col_ai1, col_ai2, col_save = st.columns([1,1,1])
        with col_ai1:
            ai_hyp = st.form_submit_button("🤖 IA: bozza ipotesi", help="Genera una bozza (TEST) basata sulla visita attuale + PNEV compilata.")
        with col_ai2:
            ai_plan = st.form_submit_button("🤖 IA: bozza piano", help="Genera obiettivi/piano (TEST) basati su visita attuale + PNEV.")
        with col_save:
            salva = st.form_submit_button("Salva valutazione visiva")

    if salva:
        data_iso = None
        if data_str.strip():
            try:
                d = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return

        # Prepariamo un blocco strutturato con tutti i dati oculistici
        dettaglio = f"""
ACUITÀ VISIVA
- NAT: OD {ac_nat_od} | OS {ac_nat_os} | OO {ac_nat_oo}
- CORR: OD {ac_cor_od} | OS {ac_cor_os} | OO {ac_cor_oo}

REFRAZIONE OGGETTIVA (SF / CIL x AX)
- OD: {sf_ogg_od:+.2f} ({cil_ogg_od:+.2f} x {ax_ogg_od}°)
- OS: {sf_ogg_os:+.2f} ({cil_ogg_os:+.2f} x {ax_ogg_os}°)

REFRAZIONE SOGGETTIVA (SF / CIL x AX)
- OD: {sf_sogg_od:+.2f} ({cil_sogg_od:+.2f} x {ax_sogg_od}°)
- OS: {sf_sogg_os:+.2f} ({cil_sogg_os:+.2f} x {ax_sogg_os}°)

CHERATOMETRIA
- OD: K1 {k1_od_mm:.2f} mm / {k1_od_D:.2f} D; K2 {k2_od_mm:.2f} mm / {k2_od_D:.2f} D
- OS: K1 {k1_os_mm:.2f} mm / {k1_os_D:.2f} D; K2 {k2_os_mm:.2f} mm / {k2_os_D:.2f} D

TONOMETRIA
- OD: {tono_od:.1f} mmHg
- OS: {tono_os:.1f} mmHg

MOTILITÀ / ALLINEAMENTO
- Motilità oculare: {motilita}
- Cover test: {cover_test}
- Stereopsi: {stereopsi}
- PPC: {ppc_cm:.1f} cm

COLORI / PACHIMETRIA
- Ishihara: {ishihara}
- Pachimetria OD: {pachim_od:.0f} µm
- Pachimetria OS: {pachim_os:.0f} µm


ESAME OBIETTIVO (STRUTTURE OCULARI)
- Cornea: {cornea}
- Camera anteriore: {camera_ant}
- Cristallino: {cristallino}
- Congiuntiva / Sclera: {congiuntiva}
- Iride / Pupilla: {iride_pupilla}
- Vitreo: {vitreo}

ESAMI STRUTTURALI / FUNZIONALI
- Fondo oculare: {fondo}
- Campo visivo: {campo_visivo}
- OCT: {oct}
- Topografia corneale: {topo}
        """.strip()

        note_finali = dettaglio + "\n\nVALUTAZIONE PNEV:\n" + (pnev_summary_new or "") + "\n\nNOTE LIBERE:\n" + (note_libere or "")

        cur.execute(
            """
            INSERT INTO Valutazioni_Visive
            (Paziente_ID, Data_Valutazione, Tipo_Visita, Professionista,
             Anamnesi, pnev_json, pnev_summary,
             Acuita_Nat_OD, Acuita_Nat_OS, Acuita_Nat_OO,
             Acuita_Corr_OD, Acuita_Corr_OS, Acuita_Corr_OO,
             Cornea, Camera_Anteriore, Cristallino, Congiuntiva_Sclera, Iride_Pupilla, Vitreo,
             Costo, Pagato, Note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paz_id,
                data_iso,
                tipo,
                professionista,
                (pnev_summary_new or ''),
                pnev.pnev_dump(pnev_data_new),
                (pnev_summary_new or ''),
                ac_nat_od,
                ac_nat_os,
                ac_nat_oo,
                ac_cor_od,
                ac_cor_os,
                ac_cor_oo,
                cornea,
                camera_ant,
                cristallino,
                congiuntiva,
                iride_pupilla,
                vitreo,
                float(costo),
                1 if pagato else 0,
                note_finali,
            ),
        )
        conn.commit()
        st.success("Valutazione visiva salvata.")

    # -------- Strumenti optometrici/oculistici stand-alone --------
    st.markdown("---")
    st.subheader("Strumenti di supporto optometrici / oculistici")

    # Cheratometria
    with st.expander("Cheratometria rapida (mm ⇄ diottrie)"):
        modo = st.radio("Tipo di conversione", ["mm → diottrie", "diottrie → mm"], key="cherato_modo")
        if modo == "mm → diottrie":
            raggio = st.number_input("Raggio corneale (mm)", min_value=6.0, max_value=9.5, value=7.80, step=0.01, key="cherato_r_mm")
            if st.button("Calcola potere (D)", key="btn_cherato_mmD"):
                D = cherato_mm_to_D(raggio)
                st.success(f"Potere corneale ≈ {D:.2f} D")
        else:
            D_val = st.number_input("Potere corneale (D)", min_value=35.0, max_value=50.0, value=43.00, step=0.25, key="cherato_D")
            if st.button("Calcola raggio (mm)", key="btn_cherato_Dmm"):
                r = cherato_D_to_mm(D_val)
                st.success(f"Raggio corneale ≈ {r:.2f} mm")

    # 
    # -------- Privacy & Consensi (storico + stampa PDF) --------
    st.markdown("---")
    st.subheader("Privacy e Consensi (storico)")

    cons_rows = fetch_privacy_consents(cur, paz_id)
    if not cons_rows:
        st.info("Nessun consenso privacy registrato per questo paziente.")
    else:
        # tabella compatta
        def _yesno(v):
            try:
                return "SI" if int(v) == 1 else "NO"
            except Exception:
                return "SI" if v else "NO"

        preview = []
        for r in cons_rows:
            preview.append({
                "ID": r["ID"],
                "Data/Ora": r.get("Data_Ora",""),
                "Tipo": r.get("Tipo",""),
                "Firmato": "✅" if _is_firmato(r) else "—",
                "Trattamento": _yesno(r.get("Consenso_Trattamento")),
                "Servizio": _yesno(r.get("Consenso_Comunicazioni")),
                "Marketing": _yesno(r.get("Consenso_Marketing")),
                "Klaviyo": _yesno(r.get("Usa_Klaviyo")),
                "Email": _yesno(r.get("Canale_Email")),
                "SMS": _yesno(r.get("Canale_SMS")),
                "WhatsApp": _yesno(r.get("Canale_WhatsApp")),
            })
        st.dataframe(preview, use_container_width=True, hide_index=True)

        ids = [str(r["ID"]) for r in cons_rows]
        sel_cons_id = st.selectbox("Seleziona un consenso per stampare il PDF", ids, key="sel_privacy_id")
        cons_rec = next(r for r in cons_rows if str(r["ID"]) == str(sel_cons_id))

        # Badge firma digitale (se presente URL firma importato da Google Sheet)
        firma_val = _extract_firma_url(cons_rec)
        if firma_val:
            st.success("✅ Consenso firmato (firma acquisita via Google Form).")
            st.caption(f"Firma (valore/link): {firma_val}")
        else:
            st.info("ℹ️ Nessuna firma digitale registrata per questo consenso (se usi Google Form, assicurati che nel form ci sia un campo 'Caricamento file' per la firma e che lo Sheet lo riporti).")


        colp1, colp2 = st.columns(2)
        with colp1:
            pdf_priv_int = genera_privacy_pdf(paziente, cons_rec, include_header=True)
            st.download_button(
                "Scarica Privacy PDF (con intestazione)",
                data=pdf_priv_int,
                file_name=f"privacy_{paziente['Cognome']}_{paziente['Nome']}_{sel_cons_id}_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_priv_int_{sel_cons_id}",
            )
        with colp2:
            pdf_priv_no = genera_privacy_pdf(paziente, cons_rec, include_header=False)
            st.download_button(
                "Scarica Privacy PDF (senza intestazione)",
                data=pdf_priv_no,
                file_name=f"privacy_{paziente['Cognome']}_{paziente['Nome']}_{sel_cons_id}_senza_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_priv_no_{sel_cons_id}",
            )

    

        st.markdown("#### Firma digitale da remoto (Google Form)")
        st.caption("Apri il modulo Google con i campi precompilati. Per una firma 'grafometrica' vera, usa la firma su tablet direttamente nel PDF in studio; su Google Forms la firma è tipicamente tramite caricamento file (foto della firma).")

        # Motivo/contesto (es. Visita oculistica)
        motivo_default = "Visita Oculistica/esame oggettivo"
        motivo = st.text_input("Motivo/contesto (precompila nel form)", value=motivo_default, key="privacy_motivo_prefill")

        # se esiste un consenso MINORE, usa l'ultimo tutore come fallback per precompilare
        tut_fallback = {}
        try:
            last_min = next((r for r in cons_rows if str(r.get("Tipo","")).upper().startswith("MIN")), None)
            if last_min:
                tut_fallback = dict(last_min)
        except Exception:
            tut_fallback = {}

        colf1, colf2 = st.columns(2)
        with colf1:
            url_ad = build_google_form_url_adulto(paziente, motivo=motivo)
            st.link_button("Apri Google Form – Privacy ADULTO", url_ad)
        with colf2:
            url_mi = build_google_form_url_minore(paziente, motivo=motivo, tutore_fallback=tut_fallback)
            st.link_button("Apri Google Form – Privacy MINORE", url_mi)

        st.markdown("#### Importa dallo Sheet (risposte Google Forms) nello storico")
        st.caption("Usa gli Sheet ESISTENTI: pubblica il foglio risposte come CSV e inserisci l'URL in Secrets (PRIVACY_SHEET_ADULTO_CSV_URL / PRIVACY_SHEET_MINORE_CSV_URL).")
        colim1, colim2 = st.columns(2)
        with colim1:
            if st.button("Importa ultima risposta ADULTO per questo paziente", key="imp_priv_ad"):
                try:
                    ins_id = import_privacy_from_sheet_csv(cur, paziente, tipo="ADULTO")
                    if ins_id:
                        st.success(f"Import riuscito (ID consenso: {ins_id}). Aggiorna la pagina per vederlo nello storico.")
                    else:
                        st.warning("Nessun match trovato nello Sheet (per CF o Email) oppure CSV non configurato nei Secrets.")
                except Exception as e:
                    st.error(f"Errore import: {e}")
        with colim2:
            if st.button("Importa ultima risposta MINORE per questo paziente", key="imp_priv_min"):
                try:
                    ins_id = import_privacy_from_sheet_csv(cur, paziente, tipo="MINORE")
                    if ins_id:
                        st.success(f"Import riuscito (ID consenso: {ins_id}). Aggiorna la pagina per vederlo nello storico.")
                    else:
                        st.warning("Nessun match trovato nello Sheet (per CF o Email) oppure CSV non configurato nei Secrets.")
                except Exception as e:
                    st.error(f"Errore import: {e}")

    st.markdown("#### Registra un nuovo consenso (se cambiano le scelte)")
    with st.form("privacy_update_form"):
        tipo_priv = st.radio("Tipo", ["Adulto", "Minore"], horizontal=True, key="upd_tipo_priv")

        t_nome = t_cf = t_tel = t_mail = ""
        if tipo_priv == "Minore":
            st.markdown("**Dati del genitore/tutore**")
            c1, c2 = st.columns(2)
            with c1:
                t_nome = st.text_input("Nome e cognome tutore", "", key="upd_t_nome")
                t_tel = st.text_input("Telefono tutore", "", key="upd_t_tel")
            with c2:
                t_cf = st.text_input("Codice fiscale tutore", "", key="upd_t_cf").upper()
                t_mail = st.text_input("Email tutore", "", key="upd_t_mail")

        st.markdown("**Consensi**")
        c_tratt = st.checkbox("✅ Consenso trattamento dati (obbligatorio)", value=True, key="upd_c_tratt")
        c_serv = st.checkbox("Consenso comunicazioni di servizio", value=True, key="upd_c_serv")

        st.markdown("**Canali autorizzati**")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            ch_email = st.checkbox("Email", value=True, key="upd_ch_email")
        with cc2:
            ch_sms = st.checkbox("SMS", value=False, key="upd_ch_sms")
        with cc3:
            ch_wa = st.checkbox("WhatsApp", value=True, key="upd_ch_wa")

        st.markdown("**Marketing / Klaviyo**")
        c_mark = st.checkbox("Consenso marketing/offerte", value=False, key="upd_c_mark")
        use_kl = st.checkbox("Autorizzo uso Klaviyo (solo se marketing attivo)", value=False, key="upd_use_kl")
        n_priv = st.text_area("Note (facoltative)", "", key="upd_note")
        firma_file = st.file_uploader("Firma (immagine PNG/JPG) – opzionale (se firmi in studio)", type=["png","jpg","jpeg"], key="upd_firma_img")

        save_priv = st.form_submit_button("Registra consenso")

    if save_priv:
        if not c_tratt:
            st.error("Il consenso al trattamento dati è obbligatorio.")
        else:
            payload = {
                "Data_Ora": _now_iso_dt(),
                "Tipo": "MINORE" if tipo_priv == "Minore" else "ADULTO",
                "Tutore_Nome": t_nome,
                "Tutore_CF": t_cf,
                "Tutore_Telefono": t_tel,
                "Tutore_Email": t_mail,
                "Consenso_Trattamento": c_tratt,
                "Consenso_Comunicazioni": c_serv,
                "Consenso_Marketing": c_mark,
                "Canale_Email": ch_email,
                "Canale_SMS": ch_sms,
                "Canale_WhatsApp": ch_wa,
                "Usa_Klaviyo": (use_kl and c_mark),
                "Firma_Blob": (firma_file.getvalue() if firma_file is not None else None),
                "Firma_Filename": (firma_file.name if firma_file is not None else ""),
                "Firma_URL": "",
                "Firma_Source": ("upload" if firma_file is not None else ""),
                "Pdf_Blob": None,
                "Pdf_Filename": "",
                "Note": n_priv,
            }
            insert_privacy_consent(cur, paz_id, payload)
            conn.commit()
            st.success("Consenso registrato nello storico.")
            st.rerun()
    # Conversione occhiali -> CL
    with st.expander("Conversione occhiali → lenti a contatto (sfera + cilindro)"):
        st.write("Conversione approssimata, da verificare sempre con la prova in studio.")
        vertex = st.number_input("Distanza vertebrale occhiali (mm)", min_value=8.0, max_value=16.0, value=12.0, step=0.5, key="cl_vertex")

        st.markdown("**Occhio destro (OD)**")
        col_od1, col_od2, col_od3 = st.columns(3)
        with col_od1:
            sph_od = st.number_input("Sfera occhiali OD (D)", min_value=-30.0, max_value=30.0, value=0.0, step=0.25, key="sph_od")
        with col_od2:
            cyl_od = st.number_input("Cilindro occhiali OD (D)", min_value=-10.0, max_value=10.0, value=0.0, step=0.25, key="cyl_od")
        with col_od3:
            ax_od = st.number_input("Asse occhiali OD (°)", min_value=0, max_value=180, value=0, step=1, key="ax_od")

        st.markdown("**Occhio sinistro (OS)**")
        col_os1, col_os2, col_os3 = st.columns(3)
        with col_os1:
            sph_os = st.number_input("Sfera occhiali OS (D)", min_value=-30.0, max_value=30.0, value=0.0, step=0.25, key="sph_os")
        with col_os2:
            cyl_os = st.number_input("Cilindro occhiali OS (D)", min_value=-10.0, max_value=10.0, value=0.0, step=0.25, key="cyl_os")
        with col_os3:
            ax_os = st.number_input("Asse occhiali OS (°)", min_value=0, max_value=180, value=0, step=1, key="ax_os")

        if st.button("Calcola lenti a contatto", key="btn_cl_conv"):
            sph_cl_od, cyl_cl_od, ax_cl_od = convert_occhiali_to_cl(sph_od, cyl_od, ax_od, vertex_mm=vertex)
            sph_cl_os, cyl_cl_os, ax_cl_os = convert_occhiali_to_cl(sph_os, cyl_os, ax_os, vertex_mm=vertex)

            st.success(
                f"**OD (CL):** {sph_cl_od:+.2f} D  {cyl_cl_od:+.2f} D x {ax_cl_od:.0f}°"
            )
            st.success(
                f"**OS (CL):** {sph_cl_os:+.2f} D  {cyl_cl_os:+.2f} D x {ax_cl_os:.0f}°"
            )
            st.info("Puoi arrotondare ulteriormente secondo le disponibilità reali delle lenti a contatto.")

    # -------- Valutazioni esistenti --------
    st.markdown("---")
    st.subheader("Valutazioni esistenti")

    cur.execute(
        "SELECT * FROM Valutazioni_Visive WHERE Paziente_ID = ? ORDER BY Data_Valutazione DESC, ID DESC",
        (paz_id,),
    )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna valutazione per questo paziente.")
        conn.close()
        return

    labels = [
        f"{r['ID']} - {r['Data_Valutazione'] or ''} - { (r['Tipo_Visita'][:40] + '...') if r['Tipo_Visita'] and len(r['Tipo_Visita'])>40 else (r['Tipo_Visita'] or '') }"
        for r in rows
    ]
    sel_v = st.selectbox("Seleziona una valutazione da modificare/cancellare", labels)
    val_id = int(sel_v.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == val_id)
    st.markdown("#### Referto oculistico in PDF (A4)")

    if not REPORTLAB_AVAILABLE:
        st.info("Per generare il referto in PDF installa il pacchetto 'reportlab' (es. `pip install reportlab`).")
    else:
        pdf_bytes_int = genera_referto_oculistico_pdf(paziente, rec, include_header=True)
        pdf_bytes_no = genera_referto_oculistico_pdf(paziente, rec, include_header=False)
        base_name = f"{paziente['Cognome']}_{paziente['Nome']}_{val_id}"

        colr1, colr2 = st.columns(2)
        with colr1:
            st.download_button(
                "Scarica referto A4 (con intestazione)",
                data=pdf_bytes_int,
                file_name=f"referto_{base_name}_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_ref_int_{val_id}",
            )
        with colr2:
            st.download_button(
                "Scarica referto A4 (senza intestazione)",
                data=pdf_bytes_no,
                file_name=f"referto_{base_name}_senza_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_ref_no_{val_id}",
            )

    with st.form("modifica_val_visiva"):
        data_m = st.text_input(
            "Data (gg/mm/aaaa)",
            datetime.strptime(rec["Data_Valutazione"], "%Y-%m-%d").strftime("%d/%m/%Y")
            if rec["Data_Valutazione"] else "",
        )
        tipo_m = st.text_input("Tipo visita", rec["Tipo_Visita"] or "")
        professionista_m = st.text_input("Professionista", rec["Professionista"] or "")

        st.markdown("**Acuità naturale**")
        col1, col2, col3 = st.columns(3)
        with col1:
            ac_nat_od_m = av_select("OD (naturale)", rec["Acuita_Nat_OD"], key="ac_nat_od_m")
        with col2:
            ac_nat_os_m = av_select("OS (naturale)", rec["Acuita_Nat_OS"], key="ac_nat_os_m")
        with col3:
            ac_nat_oo_m = av_select("OO (naturale)", rec["Acuita_Nat_OO"], key="ac_nat_oo_m")

        st.markdown("**Acuità corretta**")
        col4, col5, col6 = st.columns(3)
        with col4:
            ac_cor_od_m = av_select("OD (corretta)", rec["Acuita_Corr_OD"], key="ac_cor_od_m")
        with col5:
            ac_cor_os_m = av_select("OS (corretta)", rec["Acuita_Corr_OS"], key="ac_cor_os_m")
        with col6:
            ac_cor_oo_m = av_select("OO (corretta)", rec["Acuita_Corr_OO"], key="ac_cor_oo_m")

        st.markdown("### Esame obiettivo (strutture oculari)")
        cornea_m = st.text_area("Cornea", rec.get("Cornea") or "", key="cornea_m")
        camera_ant_m = st.text_area("Camera anteriore", rec.get("Camera_Anteriore") or "", key="camera_ant_m")
        cristallino_m = st.text_area("Cristallino", rec.get("Cristallino") or "", key="cristallino_m")
        congiuntiva_m = st.text_area("Congiuntiva / Sclera", rec.get("Congiuntiva_Sclera") or "", key="congiuntiva_m")
        iride_pupilla_m = st.text_area("Iride / Pupilla", rec.get("Iride_Pupilla") or "", key="iride_pupilla_m")
        vitreo_m = st.text_area("Vitreo", rec.get("Vitreo") or "", key="vitreo_m")

        costo_m = st.number_input(
            "Costo visita",
            min_value=0.0,
            step=5.0,
            value=float(rec["Costo"] or 0.0),
            key="costo_m",
        )
        pagato_m = st.checkbox("Pagato", value=bool(rec["Pagato"]), key="pagato_m")

        note_m = st.text_area("Note (blocco completo, inclusi dati oculistici strutturati)", rec["Note"] or "")

        # --- PNEV (Psico‑Neuro‑Evolutivo) ---
        try:
            existing_pnev_raw = rec.get("pnev_json") if hasattr(rec, "get") else None
        except Exception:
            existing_pnev_raw = None
        pnev_existing = pnev.pnev_load(existing_pnev_raw)
        visita_snapshot_m = pnev.pnev_pack_visita(
            Acuita_Nat_OD=ac_nat_od_m, Acuita_Nat_OS=ac_nat_os_m, Acuita_Nat_OO=ac_nat_oo_m,
            Acuita_Corr_OD=ac_cor_od_m, Acuita_Corr_OS=ac_cor_os_m, Acuita_Corr_OO=ac_cor_oo_m,
        )
        pnev_data_m, pnev_summary_m = pnev.pnev_collect_ui(prefix=f"pnev_edit_{val_id}", visita=visita_snapshot_m, existing=pnev_existing)

        col_ai1, col_ai2, col_save, col_del = st.columns([1,1,1,1])
        with col_ai1:
            ai_hyp_m = st.form_submit_button("🤖 IA: bozza ipotesi", help="Genera una bozza (TEST) basata sulla visita attuale + PNEV.")
        with col_ai2:
            ai_plan_m = st.form_submit_button("🤖 IA: bozza piano", help="Genera obiettivi/piano (TEST) basati su visita attuale + PNEV.")
        with col_save:
            salva_m = st.form_submit_button("Salva modifiche")
        with col_del:
            cancella = st.form_submit_button("Elimina valutazione")

    if salva_m:
        data_iso_m = None
        if data_m.strip():
            try:
                d = datetime.strptime(data_m.strip(), "%d/%m/%Y").date()
                data_iso_m = d.isoformat()
            except ValueError:
                st.error("Data non valida.")
                conn.close()
                return
        cur.execute(
            """
            UPDATE Valutazioni_Visive
            SET Data_Valutazione = ?, Tipo_Visita = ?, Professionista = ?,
                Acuita_Nat_OD = ?, Acuita_Nat_OS = ?, Acuita_Nat_OO = ?,
                Acuita_Corr_OD = ?, Acuita_Corr_OS = ?, Acuita_Corr_OO = ?,
                Cornea = ?, Camera_Anteriore = ?, Cristallino = ?, Congiuntiva_Sclera = ?, Iride_Pupilla = ?, Vitreo = ?,
                Anamnesi = ?, pnev_json = ?, pnev_summary = ?,
                Costo = ?, Pagato = ?, Note = ?
            WHERE ID = ?
            """,
            (
                data_iso_m,
                tipo_m,
                professionista_m,
                ac_nat_od_m,
                ac_nat_os_m,
                ac_nat_oo_m,
                ac_cor_od_m,
                ac_cor_os_m,
                ac_cor_oo_m,
                cornea_m,
                camera_ant_m,
                cristallino_m,
                congiuntiva_m,
                iride_pupilla_m,
                vitreo_m,
                (pnev_summary_m or ''),
                pnev.pnev_dump(pnev_data_m),
                (pnev_summary_m or ''),
                float(costo_m),
                1 if pagato_m else 0,
                note_m,
                val_id,
            ),
        )
        conn.commit()
        st.success("Valutazione aggiornata.")

    if cancella:
        cur.execute("DELETE FROM Valutazioni_Visive WHERE ID = ?", (val_id,))
        conn.commit()
        st.success("Valutazione eliminata.")
    st.markdown("---")
    st.subheader("Prescrizione occhiali (stampa A5 / A4 2×A5)")

    if not REPORTLAB_AVAILABLE:
        st.info("Per generare la prescrizione in PDF installa il pacchetto 'reportlab' (es. `pip install reportlab`).")
    else:
        st.write("Compila la prescrizione finale e scarica un PDF A5 pronto per la stampa.")

        with st.form("prescrizione_a5_form"):
            data_prescr_str = st.text_input(
                "Data prescrizione (gg/mm/aaaa)",
                datetime.today().strftime("%d/%m/%Y"),
                key="data_prescr_a5",
            )

            # SOLO A4: nessuna scelta formato
            formato_stampa = "A4"
            divider_line = False

            con_cirillo = st.checkbox(
                "Intestazione con Dott. Cirillo",
                value=True,
                key="prescr_con_cirillo",
            )

            st.markdown("**LONTANO**")
            colL1, colL2 = st.columns(2)
            with colL1:
                sf_lon_od = st.number_input("OD SF lontano (D)", -30.0, 30.0, 0.0, 0.25, key="sf_lon_od_a5")
                cil_lon_od = st.number_input("OD CIL lontano (D)", -10.0, 10.0, 0.0, 0.25, key="cil_lon_od_a5")
                ax_lon_od = st.number_input("OD AX lontano (°)", 0, 180, 0, 1, key="ax_lon_od_a5")
            with colL2:
                sf_lon_os = st.number_input("OS SF lontano (D)", -30.0, 30.0, 0.0, 0.25, key="sf_lon_os_a5")
                cil_lon_os = st.number_input("OS CIL lontano (D)", -10.0, 10.0, 0.0, 0.25, key="cil_lon_os_a5")
                ax_lon_os = st.number_input("OS AX lontano (°)", 0, 180, 0, 1, key="ax_lon_os_a5")

            st.markdown("**INTERMEDIO**")
            colI1, colI2 = st.columns(2)
            with colI1:
                sf_int_od = st.number_input("OD SF intermedio (D)", -30.0, 30.0, 0.0, 0.25, key="sf_int_od_a5")
                cil_int_od = st.number_input("OD CIL intermedio (D)", -10.0, 10.0, 0.0, 0.25, key="cil_int_od_a5")
                ax_int_od = st.number_input("OD AX intermedio (°)", 0, 180, 0, 1, key="ax_int_od_a5")
            with colI2:
                sf_int_os = st.number_input("OS SF intermedio (D)", -30.0, 30.0, 0.0, 0.25, key="sf_int_os_a5")
                cil_int_os = st.number_input("OS CIL intermedio (D)", -10.0, 10.0, 0.0, 0.25, key="cil_int_os_a5")
                ax_int_os = st.number_input("OS AX intermedio (°)", 0, 180, 0, 1, key="ax_int_os_a5")

            st.markdown("**VICINO**")
            colV1, colV2 = st.columns(2)
            with colV1:
                sf_vic_od = st.number_input("OD SF vicino (D)", -30.0, 30.0, 0.0, 0.25, key="sf_vic_od_a5")
                cil_vic_od = st.number_input("OD CIL vicino (D)", -10.0, 10.0, 0.0, 0.25, key="cil_vic_od_a5")
                ax_vic_od = st.number_input("OD AX vicino (°)", 0, 180, 0, 1, key="ax_vic_od_a5")
            with colV2:
                sf_vic_os = st.number_input("OS SF vicino (D)", -30.0, 30.0, 0.0, 0.25, key="sf_vic_os_a5")
                cil_vic_os = st.number_input("OS CIL vicino (D)", -10.0, 10.0, 0.0, 0.25, key="cil_vic_os_a5")
                ax_vic_os = st.number_input("OS AX vicino (°)", 0, 180, 0, 1, key="ax_vic_os_a5")

            lenti_possibili = [
                "Progressive",
                "Per vicino/intermedio",
                "Fotocromatiche",
                "Polarizzate",
                "Controllo miopia",
                "Trattamento antiriflesso",
            ]
            lenti_scelte = st.multiselect(
                "Lenti consigliate",
                options=lenti_possibili,
                key="lenti_scelte_a5",
            )

            altri_trattamenti = st.text_input(
                "Altri trattamenti (facoltativo)",
                key="altro_tratt_a5",
            )

            note_prescrizione = st.text_area(
                "Note aggiuntive per la prescrizione",
                key="note_prescr_a5",
            )

            genera_pdf = st.form_submit_button("Genera PDF")

        if genera_pdf:
            data_iso_prescr = None
            if data_prescr_str.strip():
                try:
                    d = datetime.strptime(data_prescr_str.strip(), "%d/%m/%Y").date()
                    data_iso_prescr = d.isoformat()
                except ValueError:
                    st.error("Data prescrizione non valida. Usa il formato gg/mm/aaaa.")
                    data_iso_prescr = None

            
            common_kwargs = dict(
                paziente=paziente,
                data_prescrizione_iso=data_iso_prescr,
                sf_lon_od=sf_lon_od, cil_lon_od=cil_lon_od, ax_lon_od=ax_lon_od,
                sf_lon_os=sf_lon_os, cil_lon_os=cil_lon_os, ax_lon_os=ax_lon_os,
                sf_int_od=sf_int_od, cil_int_od=cil_int_od, ax_int_od=ax_int_od,
                sf_int_os=sf_int_os, cil_int_os=cil_int_os, ax_int_os=ax_int_os,
                sf_vic_od=sf_vic_od, cil_vic_od=cil_vic_od, ax_vic_od=ax_vic_od,
                sf_vic_os=sf_vic_os, cil_vic_os=cil_vic_os, ax_vic_os=ax_vic_os,
                lenti_scelte=lenti_scelte,
                altri_trattamenti=altri_trattamenti,
                note=note_prescrizione,
            )

            # SOLO FORMATO A4 (niente A5)
            pdf_bytes = genera_prescrizione_occhiali_a4_pdf(**common_kwargs, con_cirillo=con_cirillo)
            filename = f"prescrizione_occhiali_{paziente['Cognome']}_{paziente['Nome']}_A4.pdf"
            label_btn = "Scarica prescrizione occhiali (A4)"

            st.download_button(
                label_btn,
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                key="dl_prescr",
            )
    conn.close()

# -----------------------------
# UI: Sedute / Terapie
# -----------------------------

def ui_sedute():
    st.header("Sedute / Terapie")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    options = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options)
    paz_id = int(sel.split(" - ", 1)[0])

    with st.form("nuova_seduta"):
        st.subheader("Nuova seduta")
        data_str = st.text_input("Data (gg/mm/aaaa)", datetime.today().strftime("%d/%m/%Y"))
        terapia = st.text_input("Tipo di terapia (es. logopedia, neuropsicomotricità, optometria...)", "")
        professionista = st.text_input("Professionista", "")
        col1, col2 = st.columns(2)
        with col1:
            costo = st.number_input("Costo seduta", min_value=0.0, step=5.0, value=0.0)
        with col2:
            pagato = st.checkbox("Pagato", value=False)
        note = st.text_area("Note")
        salva = st.form_submit_button("Salva seduta")

    if salva:
        data_iso = None
        if data_str.strip():
            try:
                d = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return
        cur.execute(
            """
            INSERT INTO Sedute
            (Paziente_ID, Data_Seduta, Terapia, Professionista, Costo, Pagato, Note)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                paz_id,
                data_iso,
                terapia,
                professionista,
                float(costo),
                1 if pagato else 0,
                note,
            ),
        )
        conn.commit()
        st.success("Seduta salvata.")

    st.markdown("---")
    st.subheader("Sedute esistenti")

    cur.execute(
        "SELECT * FROM Sedute WHERE Paziente_ID = ? ORDER BY Data_Seduta DESC, ID DESC",
        (paz_id,),
    )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna seduta per questo paziente.")
        conn.close()
        return

    labels = [
        f"{r['ID']} - {r['Data_Seduta'] or ''} - { (r['Terapia'][:40] + '...') if r['Terapia'] and len(r['Terapia'])>40 else (r['Terapia'] or '') }"
        for r in rows
    ]
    sel_s = st.selectbox("Seleziona una seduta da modificare/cancellare", labels)
    sed_id = int(sel_s.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == sed_id)

    with st.form("modifica_seduta"):
        data_m = st.text_input(
            "Data (gg/mm/aaaa)",
            datetime.strptime(rec["Data_Seduta"], "%Y-%m-%d").strftime("%d/%m/%Y")
            if rec["Data_Seduta"] else "",
        )
        terapia_m = st.text_input("Terapia", rec["Terapia"] or "")
        professionista_m = st.text_input("Professionista", rec["Professionista"] or "")
        col1, col2 = st.columns(2)
        with col1:
            costo_m = st.number_input(
                "Costo seduta",
                min_value=0.0,
                step=5.0,
                value=float(rec["Costo"] or 0.0),
                key="costo_sed_m",
            )
        with col2:
            pagato_m = st.checkbox("Pagato", value=bool(rec["Pagato"]), key="pagato_sed_m")
        note_m = st.text_area("Note", rec["Note"] or "")

        col3, col4 = st.columns(2)
        with col3:
            salva_m = st.form_submit_button("Salva modifiche")
        with col4:
            cancella = st.form_submit_button("Elimina seduta")

    if salva_m:
        data_iso_m = None
        if data_m.strip():
            try:
                d = datetime.strptime(data_m.strip(), "%d/%m/%Y").date()
                data_iso_m = d.isoformat()
            except ValueError:
                st.error("Data non valida.")
                conn.close()
                return
        cur.execute(
            """
            UPDATE Sedute
            SET Data_Seduta = ?, Terapia = ?, Professionista = ?, Costo = ?, Pagato = ?, Note = ?
            WHERE ID = ?
            """,
            (
                data_iso_m,
                terapia_m,
                professionista_m,
                float(costo_m),
                1 if pagato_m else 0,
                note_m,
                sed_id,
            ),
        )
        conn.commit()
        st.success("Seduta aggiornata.")

    if cancella:
        cur.execute("DELETE FROM Sedute WHERE ID = ?", (sed_id,))
        conn.commit()
        st.success("Seduta eliminata.")

    conn.close()
def ui_coupons():
    st.header("Gestione coupon OF / SDS")

    conn = get_connection()
    cur = conn.cursor()

    # Elenco pazienti
    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    opt_paz = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", opt_paz)
    paz_id = int(sel.split(" - ", 1)[0])

    st.markdown("### Aggiungi nuovo coupon")

    with st.form("form_nuovo_coupon"):
        col1, col2 = st.columns(2)
        with col1:
            tipo_coupon = st.selectbox("Tipo coupon", ["OF", "SDS"], key="tipo_coupon_new")
        with col2:
            codice_coupon = st.text_input("Codice / numero coupon", key="codice_coupon_new")

        col3, col4 = st.columns(2)
        with col3:
            data_c_str = st.text_input(
                "Data assegnazione (gg/mm/aaaa)",
                datetime.today().strftime("%d/%m/%Y"),
                key="data_coupon_new",
            )
        with col4:
            usato_flag = st.checkbox("Già utilizzato", value=False, key="usato_coupon_new")

        note_coupon = st.text_input("Note coupon (facoltative)", key="note_coupon_new")

        salva_c = st.form_submit_button("Aggiungi coupon")

    if salva_c:
        data_c_iso = None
        if data_c_str.strip():
            try:
                d = datetime.strptime(data_c_str.strip(), "%d/%m/%Y").date()
                data_c_iso = d.isoformat()
            except ValueError:
                st.error("Data coupon non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return

        cur.execute(
            """
            INSERT INTO Coupons
            (Paziente_ID, Tipo_Coupon, Codice_Coupon, Data_Assegnazione, Note, Utilizzato)
            VALUES (?,?,?,?,?,?)
            """,
            (
                paz_id,
                tipo_coupon,
                codice_coupon.strip() or None,
                data_c_iso,
                note_coupon.strip() or None,
                1 if usato_flag else 0,
            ),
        )
        conn.commit()
        st.success("Coupon aggiunto correttamente.")
        st.rerun()

    st.markdown("---")
    st.subheader("Coupon del paziente selezionato")

    cur.execute(
        "SELECT * FROM Coupons WHERE Paziente_ID = ? ORDER BY Data_Assegnazione DESC, ID DESC",
        (paz_id,),
    )
    coupons = cur.fetchall()

    if not coupons:
        st.info("Nessun coupon per questo paziente.")
        conn.close()
        return

    for c in coupons:
        data_it = ""
        if c["Data_Assegnazione"]:
            try:
                data_it = datetime.strptime(c["Data_Assegnazione"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                data_it = c["Data_Assegnazione"]

        stato = "USATO" if c["Utilizzato"] else "NON USATO"

        col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
        with col1:
            st.write(
                f"**ID {c['ID']}** – {c['Tipo_Coupon']} – "
                f"{c['Codice_Coupon'] or '-'} – {data_it or 'data n/d'}"
            )
            if c["Note"]:
                st.caption(f"Note: {c['Note']}")
        with col2:
            st.write(f"Stato: **{stato}**")
        with col3:
            if c["Utilizzato"]:
                if st.button("Segna NON usato", key=f"c_notused_{c['ID']}"):
                    cur.execute(
                        "UPDATE Coupons SET Utilizzato = 0 WHERE ID = ?",
                        (c["ID"],),
                    )
                    conn.commit()
                    st.rerun()
            else:
                if st.button("Segna USATO", key=f"c_used_{c['ID']}"):
                    cur.execute(
                        "UPDATE Coupons SET Utilizzato = 1 WHERE ID = ?",
                        (c["ID"],),
                    )
                    conn.commit()
                    st.rerun()
        with col4:
            if st.button("Elimina", key=f"c_del_{c['ID']}"):
                cur.execute("DELETE FROM Coupons WHERE ID = ?", (c["ID"],))
                conn.commit()
                st.rerun()

    conn.close()


   
# -----------------------------
# UI: Dashboard incassi
# -----------------------------

def ui_dashboard():
    st.header("Dashboard incassi")

    conn = get_connection()
    cur = conn.cursor()

    st.subheader("Filtri")

    oggi = date.today()
    col1, col2, col3 = st.columns(3)
    with col1:
        data_da_str = st.text_input("Dal (gg/mm/aaaa)", oggi.strftime("%d/%m/%Y"))
    with col2:
        data_a_str = st.text_input("Al (gg/mm/aaaa)", oggi.strftime("%d/%m/%Y"))
    with col3:
        professionista_f = st.text_input("Filtra per professionista (facoltativo)", "")

    try:
        data_da = datetime.strptime(data_da_str.strip(), "%d/%m/%Y").date()
        data_a = datetime.strptime(data_a_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        st.error("Formato data non valido. Usa gg/mm/aaaa.")
        conn.close()
        return

    if data_a < data_da:
        st.error("La data finale non può essere precedente a quella iniziale.")
        conn.close()
        return

    data_da_iso = data_da.isoformat()
    data_a_iso = data_a.isoformat()

    # --- Incassi da Valutazioni Visive ---
    st.markdown("### Incassi da valutazioni visive / oculistiche")

    query_v = """
        SELECT Data_Valutazione AS Data, Professionista, Costo, Pagato
        FROM Valutazioni_Visive
        WHERE Data_Valutazione BETWEEN ? AND ?
    """
    params_v = [data_da_iso, data_a_iso]
    if professionista_f.strip():
        query_v += " AND Professionista LIKE ?"
        params_v.append(f"%{professionista_f.strip()}%")

    cur.execute(query_v, params_v)
    vis = cur.fetchall()

    incasso_vis = sum((r["Costo"] or 0.0) for r in vis if r["Pagato"])
    st.write(f"**Totale incassi visite (periodo): € {incasso_vis:.2f}**")

    # --- Incassi da Sedute ---
    st.markdown("### Incassi da sedute / terapie")

    query_s = """
        SELECT Data_Seduta AS Data, Professionista, Terapia, Costo, Pagato
        FROM Sedute
        WHERE Data_Seduta BETWEEN ? AND ?
    """
    params_s = [data_da_iso, data_a_iso]
    if professionista_f.strip():
        query_s += " AND Professionista LIKE ?"
        params_s.append(f"%{professionista_f.strip()}%")

    cur.execute(query_s, params_s)
    sed = cur.fetchall()

    incasso_sed = sum((r["Costo"] or 0.0) for r in sed if r["Pagato"])
    st.write(f"**Totale incassi sedute (periodo): € {incasso_sed:.2f}**")

    st.markdown("### Totale studio")
    st.success(f"**Totale generale incassato: € {incasso_vis + incasso_sed:.2f}**")

    conn.close()


# ==========================
# Osteopatia (AUTO) - sezione menu
# ==========================
def ui_osteopatia_section():
    """
    Sezione Osteopatia indipendente dalla sezione Pazienti:
    - seleziona paziente
    - apre UI osteopatia (anamnesi, seduta, storico+PDF A4, dashboard)
    """
    import streamlit as st

    try:
        from modules.osteopatia.ui_osteopatia import ui_osteopatia
    except Exception as e:
        st.error("Errore nel modulo Osteopatia. Verifica di aver copiato modules/osteopatia e che non ci siano errori di sintassi.")
        st.exception(e)
        return

    conn = get_connection()

    paz_list, paz_table, paz_colmap = fetch_pazienti_for_select(conn)
    if not paz_list:
        st.error("Nessun paziente trovato nel database (AUTO).")
        st.info("Apri la sezione 🛠️ Debug DB per vedere quali tabelle sono presenti su Neon.")
        if paz_table or paz_colmap:
            st.caption(f"Rilevato: {paz_table} • Colonne: {paz_colmap}")
        return

    def _label(p):
        pid, cogn, nome, dn, scuola, eta = p
        dn_s = dn or ""
        extra = ""
        if eta: extra += f" • {eta} anni"
        if scuola: extra += f" • {scuola}"
        return f"{cogn} {nome} (ID {pid}) {dn_s}{extra}".strip()

    sel = st.selectbox("Seleziona paziente", paz_list, format_func=_label)

    if isinstance(sel, dict):
        paziente_id = sel.get("id") or sel.get("paziente_id")
        cognome = sel.get("cognome") or ""
        nome = sel.get("nome") or ""
    else:
        try:
            paziente_id = sel[0]
            cognome = sel[1] if len(sel) > 1 else ""
            nome = sel[2] if len(sel) > 2 else ""
        except Exception:
            paziente_id = None
            cognome = ""
            nome = ""

    if not paziente_id:
        st.error("Errore: ID paziente non determinabile.")
        return

    paziente_label = f"{cognome} {nome}".strip() or f"Paziente ID {paziente_id}"

    ui_osteopatia(paziente_id=int(paziente_id), get_conn=get_connection, paziente_label=paziente_label)

# -----------------------------
# Main
# -----------------------------


# ==========================
# Dashboard Evolutiva Paziente
# ==========================
def ui_dashboard_evolutiva():
    """Dashboard evolutiva basata su relazioni_cliniche."""
    import streamlit as st
    import os

    conn = get_connection()
    cur = conn.cursor()

    _ensure_relazioni_cliniche_table(conn)

    st.header("📊 Dashboard evolutiva")

    # Selezione paziente (AUTO) - indipendente dalla sezione Pazienti
    paz_list, paz_table, paz_colmap = fetch_pazienti_for_select(conn)
    if not paz_list:
        st.error("Nessun paziente trovato nel database (AUTO).")
        st.info("Apri la sezione 🛠️ Debug DB per vedere quali tabelle sono presenti su Neon.")
        if paz_table or paz_colmap:
            st.caption(f"Rilevato: {paz_table} • Colonne: {paz_colmap}")
        return

    def _label(p):
        pid, cogn, nome, dn, scuola, eta = p
        dn_s = dn or ""
        extra = ""
        if eta: extra += f" • {eta} anni"
        if scuola: extra += f" • {scuola}"
        return f"{cogn} {nome} (ID {pid}) {dn_s}{extra}".strip()

    sel = st.selectbox("Seleziona paziente", paz_list, format_func=_label)
    # robust handling for dict / tuple / sqlite Row
    if isinstance(sel, dict):
        paziente_id = sel.get("id") or sel.get("paziente_id")
    else:
        try:
            paziente_id = sel[0]
        except Exception:
            paziente_id = None

    if not paziente_id:
        st.error("Errore: ID paziente non determinabile dalla selezione.")
        return
    # Carica relazioni (PostgreSQL/SQLite)
    try:
        cur.execute(
            """
            SELECT id, titolo, tipo, data_relazione, docx_path, pdf_path
            FROM relazioni_cliniche
            WHERE paziente_id = %s
            ORDER BY data_relazione ASC
            """ % ("?" if _DB_BACKEND == "sqlite" else "%s"),
            (paziente_id,)
        )
        rows = cur.fetchall()
    except Exception:
        # se la tabella non esiste ancora (cloud/Neon), la creo e riprovo
        _ensure_relazioni_cliniche_table(conn)
        try:
            cur.execute(
                """
                SELECT id, titolo, tipo, data_relazione, docx_path, pdf_path
                FROM relazioni_cliniche
                WHERE paziente_id = %s
                ORDER BY data_relazione ASC
                """ % ("?" if _DB_BACKEND == "sqlite" else "%s"),
                (paziente_id,)
            )
            rows = cur.fetchall()
        except Exception:
            rows = []

    if not rows:
        st.info("Nessuna relazione presente per questo paziente.")
        return

    def area_from_title(titolo: str) -> str:
        t = (titolo or "").lower()
        if "follow" in t: return "🔁 Follow-up"
        if "linguaggio" in t: return "🗣️ Linguaggio"
        if "neuropsico" in t: return "🧠 Neuropsicologica"
        if "neuroevol" in t: return "🌱 Neuroevolutiva"
        if "sensori" in t or "psico-motor" in t: return "🧍 Sensori-motoria"
        if "smof" in t or "oro" in t: return "👅 SMOF / Oro-linguale"
        if "scuola" in t: return "🏫 Scuola / ASL"
        return "📄 Altro"

    grouped = {}
    for r in rows:
        area = area_from_title(r[1])
        grouped.setdefault(area, []).append(r)

    for area, items in grouped.items():
        with st.expander(area, expanded=True):
            for r in items:
                rid, titolo, tipo, data_rel, docx_path, pdf_path = r
                st.markdown(f"**{data_rel} – {titolo}**")
                cols = st.columns(2)

                if docx_path and os.path.exists(docx_path):
                    with cols[0]:
                        with open(docx_path, "rb") as f:
                            st.download_button("⬇️ Word", f, file_name=os.path.basename(docx_path), key=f"dw_{rid}")
                else:
                    with cols[0]:
                        st.caption("Word non disponibile")

                if pdf_path and os.path.exists(pdf_path):
                    with cols[1]:
                        with open(pdf_path, "rb") as f:
                            st.download_button("⬇️ PDF", f, file_name=os.path.basename(pdf_path), key=f"dp_{rid}")
                else:
                    with cols[1]:
                        st.caption("PDF non disponibile (cloud)")




def ui_debug_db():
    import streamlit as st
    st.header("🛠️ Debug DB (The Organism)")
    st.caption("Questa schermata NON mostra credenziali. Serve solo a capire tabelle/colonne presenti su Neon.")

    conn = get_connection()
    tables = _debug_list_tables(conn)

    if not tables:
        st.error("Nessuna tabella rilevata. Possibile problema di connessione o schema.")
        return

    st.write(f"Tabelle rilevate: {len(tables)}")

    filtro = st.text_input("Filtro nome tabella (es. paz, patient)", value="paz")
    filtered = [t for t in tables if filtro.lower() in str(t[1] or "").lower()] if filtro else tables

    st.write(f"Mostrate: {len(filtered)}")

    def _lab(t):
        return f"{t[0] or '?'} . {t[1] or '?'}"
    sel = st.selectbox("Seleziona tabella", filtered, format_func=_lab)

    schema, table = sel[0], sel[1]
    cols = _debug_table_columns(conn, schema, table)
    cnt = _debug_count_rows(conn, schema, table)

    st.subheader("Righe")
    st.write(cnt if cnt is not None else "N/D")

    st.subheader("Colonne")
    if cols:
        st.dataframe([{"colonna": (c[0] or ""), "tipo": (c[1] or "")} for c in cols], use_container_width=True)
    else:
        st.info("Nessuna colonna letta (schema diverso o permessi).")




def ui_import_pazienti():
    import streamlit as st
    st.header("📥 Import Pazienti su Neon (Cloud)")
    st.caption("Carica un file CSV o Excel con almeno: Cognome, Nome (consigliato anche Data_Nascita). I dati verranno inseriti su Neon.")

    if _DB_BACKEND != "postgres":
        st.error("Import disponibile solo con PostgreSQL (Neon). Configura [db].DATABASE_URL nei Secrets.")
        return

    up = st.file_uploader("Carica CSV / XLSX", type=["csv", "xlsx"])
    if not up:
        st.info("Carica un file per iniziare.")
        return

    try:
        import pandas as pd
    except Exception:
        st.error("Dipendenza mancante: pandas. Aggiungi 'pandas' a requirements.txt")
        return

    try:
        if up.name.lower().endswith(".csv"):
            df = pd.read_csv(up)
        else:
            df = pd.read_excel(up)
    except Exception as e:
        st.error(f"Errore lettura file: {e}")
        return

    st.subheader("Anteprima")
    st.dataframe(df.head(30), use_container_width=True)

    cols = {str(c).lower().strip(): c for c in df.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    col_cognome = pick("cognome", "surname", "last_name", "lastname")
    col_nome = pick("nome", "name", "first_name", "firstname", "given_name")
    col_dn = pick("data_nascita", "data nascita", "birth_date", "dob")

    if not col_cognome or not col_nome:
        st.error("Colonne minime non trovate. Servono almeno: Cognome e Nome (o equivalenti).")
        st.write({"trovato_cognome": col_cognome, "trovato_nome": col_nome, "trovato_data_nascita": col_dn})
        return

    st.subheader("Mapping (auto)")
    st.write({"Cognome": col_cognome, "Nome": col_nome, "Data_Nascita": col_dn})

    if st.button("Importa su Neon"):
        try:
            init_db()
        except Exception:
            pass

        conn = get_connection()
        cur = conn.cursor()

        def s(x):
            if x is None:
                return None
            v = str(x).strip()
            return v if v else None

        records = []
        for _, row in df.iterrows():
            cogn = s(row.get(col_cognome))
            nom = s(row.get(col_nome))
            if not cogn or not nom:
                continue
            dn = s(row.get(col_dn)) if col_dn else None
            records.append((cogn, nom, dn))

        if not records:
            st.warning("Nessun record valido trovato (serve almeno Cognome e Nome).")
            return

        try:
            if col_dn:
                cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_pazienti_nat ON "Pazienti" ("Cognome","Nome","Data_Nascita")')
            else:
                cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_pazienti_nat ON "Pazienti" ("Cognome","Nome")')
            conn.commit()
        except Exception:
            try:
                conn.commit()
            except Exception:
                pass

        ok = 0
        err = 0
        for cogn, nom, dn in records:
            if col_dn:
                sql = 'INSERT INTO "Pazienti" ("Cognome","Nome","Data_Nascita") VALUES (?,?,?) ON CONFLICT ("Cognome","Nome","Data_Nascita") DO NOTHING;'
                params = (cogn, nom, dn)
            else:
                sql = 'INSERT INTO "Pazienti" ("Cognome","Nome") VALUES (?,?) ON CONFLICT ("Cognome","Nome") DO NOTHING;'
                params = (cogn, nom)
            try:
                cur.execute(sql, params)
                ok += 1
            except Exception:
                err += 1

        try:
            conn.commit()
        except Exception:
            pass

        st.success(f"Import completato. Righe valide: {len(records)} • Tentativi insert: {ok} • Errori: {err}")




# ================================
# PRIVACY PDF (Compilabili) + Cloud privato (Presigned 24h)
# ================================
import io
import os
import hashlib
import datetime as _dt
import urllib.parse as _urlparse
import json
import hmac

try:
    import boto3
except Exception:
    boto3 = None

try:
    from pypdf import PdfReader, PdfWriter
except Exception:
    PdfReader = None
    PdfWriter = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    from streamlit_drawable_canvas import st_canvas
except Exception:
    st_canvas = None


PDF_PRIVACY_ADULTO_TEMPLATE = "assets/privacy/Consenso_Informato_Privacy_Adulto_The_Organism_STAMPABILE_COMPLETO_v5.pdf"
PDF_PRIVACY_MINORE_TEMPLATE = "assets/privacy/Consenso_Informato_Privacy_Minore_The_Organism_STAMPABILE_COMPLETO_v5.pdf"

def _ensure_documenti_table(conn):
    cur = conn.cursor()
    if _DB_BACKEND == "sqlite":
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documenti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paziente_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                s3_key TEXT NOT NULL,
                filename TEXT,
                sha256 TEXT NOT NULL,
                mime TEXT DEFAULT 'application/pdf',
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
        return
    # postgres
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.documenti (
          id BIGSERIAL PRIMARY KEY,
          paziente_id BIGINT NOT NULL,
          tipo TEXT NOT NULL,
          s3_key TEXT NOT NULL,
          filename TEXT,
          sha256 TEXT NOT NULL,
          mime TEXT DEFAULT 'application/pdf',
          created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documenti_paziente ON public.documenti(paziente_id);")
    except Exception:
        pass
    conn.commit()

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _s3_put_private(key: str, data: bytes, content_type: str = "application/pdf") -> tuple[bool, str]:
    """Upload bytes to private S3. Never raises. Returns (ok, message)."""
    try:
        cli = _s3_client()
        cli.put_object(
            Bucket=_s3_bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True, "OK"
    except Exception as e:
        try:
            import botocore
            if isinstance(e, botocore.exceptions.ClientError):
                err = getattr(e, "response", {}).get("Error", {})
                code = err.get("Code", "ClientError")
                msg = err.get("Message", "")
                return False, f"{code}: {msg}"
        except Exception:
            pass
        return False, f"{type(e).__name__}: {e}"


def _s3_put_private(key: str, data: bytes, content_type: str = "application/pdf") -> tuple[bool, str]:
    """Upload bytes to private S3. Never raises. Returns (ok, message)."""
    try:
        cli = _s3_client()
        cli.put_object(
            Bucket=_s3_bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True, "OK"
    except Exception as e:
        try:
            import botocore
            if isinstance(e, botocore.exceptions.ClientError):
                err = getattr(e, "response", {}).get("Error", {})
                return False, f"{err.get('Code','ClientError')}: {err.get('Message','')}"
        except Exception:
            pass
        return False, f"{type(e).__name__}: {e}"


def _s3_client():
    if boto3 is None:
        raise RuntimeError("Manca boto3. Aggiungi 'boto3' in requirements.txt")
    cfg = st.secrets.get("storage", {})
    return boto3.client(
        "s3",
        endpoint_url=_valid_endpoint_url(cfg.get("S3_ENDPOINT_URL")),
        region_name=cfg.get("S3_REGION") or None,
        aws_access_key_id=cfg.get("S3_ACCESS_KEY"),
        aws_secret_access_key=cfg.get("S3_SECRET_KEY"),
    )

def _s3_bucket():
    cfg = st.secrets.get("storage", {})
    b = cfg.get("S3_BUCKET")
    if not b:
        raise RuntimeError("Secrets mancanti: [storage].S3_BUCKET")
    return b

def _presign_expires():
    cfg = st.secrets.get("storage", {})
    # default 24h
    return int(cfg.get("PRESIGN_EXPIRE_SECONDS", 86400))

def _s3_put_private(key: str, data: bytes, content_type: str = "application/pdf") -> tuple[bool, str]:
    """Upload bytes to private S3.

    Returns:
        (True, "OK") on success
        (False, "<errore>") on failure (does not crash the app)
    """
    try:
        cli = _s3_client()
        cli.put_object(
            Bucket=_s3_bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True, "OK"
    except Exception as e:
        # Try to surface useful info on Streamlit without leaking secrets
        msg = f"{type(e).__name__}: {e}"
        try:
            import botocore
            if isinstance(e, botocore.exceptions.ClientError):
                err = getattr(e, "response", {}).get("Error", {})
                msg = f"{err.get('Code','ClientError')} – {err.get('Message','')}"
        except Exception:
            pass
        try:
            st.error(f"Upload S3 disabilitato: {msg}")
        except Exception:
            pass
        return False, msg

def _s3_presign_get(key: str) -> str:
    cli = _s3_client()
    return cli.generate_presigned_url(
        "get_object",
        Params={"Bucket": _s3_bucket(), "Key": key},
        ExpiresIn=_presign_expires(),
    )

def _db_insert_documento(conn, paziente_id: int, tipo: str, s3_key: str, sha256: str, filename: str):
    cur = conn.cursor()
    if _DB_BACKEND == "sqlite":
        cur.execute(
            """INSERT INTO documenti (paziente_id, tipo, s3_key, filename, sha256, mime)
                 VALUES (?, ?, ?, ?, ?, 'application/pdf')""",
            (paziente_id, tipo, s3_key, filename, sha256),
        )
    else:
        cur.execute(
            """INSERT INTO public.documenti (paziente_id, tipo, s3_key, filename, sha256, mime)
                 VALUES (%s, %s, %s, %s, %s, 'application/pdf')""",
            (paziente_id, tipo, s3_key, filename, sha256),
        )
    conn.commit()

def _db_list_documenti(conn, paziente_id: int, tipo: str | None = None):
    cur = conn.cursor()
    if _DB_BACKEND == "sqlite":
        if tipo:
            cur.execute(
                "SELECT id, tipo, s3_key, filename, sha256, created_at FROM documenti WHERE paziente_id=? AND tipo=? ORDER BY id DESC",
                (paziente_id, tipo),
            )
        else:
            cur.execute(
                "SELECT id, tipo, s3_key, filename, sha256, created_at FROM documenti WHERE paziente_id=? ORDER BY id DESC",
                (paziente_id,),
            )
        return cur.fetchall()
    else:
        if tipo:
            cur.execute(
                "SELECT id, tipo, s3_key, filename, sha256, created_at FROM public.documenti WHERE paziente_id=%s AND tipo=%s ORDER BY id DESC",
                (paziente_id, tipo),
            )
        else:
            cur.execute(
                "SELECT id, tipo, s3_key, filename, sha256, created_at FROM public.documenti WHERE paziente_id=%s ORDER BY id DESC",
                (paziente_id,),
            )
        return cur.fetchall()

def _prefill_pdf(template_path: str, fields: dict) -> bytes:
    """SAFE VERSION: returns the static PDF template as-is (no AcroForm)."""
    with open(template_path, "rb") as f:
        return f.read()


def _extract_pdf_field_values(pdf_bytes: bytes) -> dict:
    """Legge valori dei campi modulo dal PDF (se presenti)."""
    if PdfReader is None:
        return {}
    try:
        r = PdfReader(io.BytesIO(pdf_bytes))
        f = r.get_fields() or {}
        out = {}
        for k, v in f.items():
            try:
                val = v.get("/V")
            except Exception:
                val = None
            # normalizza bytes / NameObject
            if val is None:
                out[k] = ""
            else:
                out[k] = str(val)
        return out
    except Exception:
        return {}

def _validate_required_fields(doc_type: str, values: dict) -> list[str]:
    """Checklist minima: radio Sì/No devono essere selezionati."""
    missing = []
    if doc_type == "adulto":
        required = ["a_gdpr_letto", "a_cons_dati", "a_cons_salute", "a_cons_marketing"]
    else:
        required = ["m_gdpr_letto", "m_cons_dati", "m_cons_salute", "m_cons_marketing"]
    for k in required:
        v = (values.get(k, "") or "").strip()
        if v == "" or v.lower() in ("none", "null"):
            missing.append(k)
    return missing

def _image_to_pdf_bytes(img_bytes: bytes) -> bytes:
    if Image is None:
        raise RuntimeError("Manca Pillow. Aggiungi 'Pillow' in requirements.txt")
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=300.0)
    return buf.getvalue()

def _merge_files_to_single_pdf(files) -> tuple[bytes, str]:
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError("Manca pypdf. Aggiungi 'pypdf' in requirements.txt")
    writer = PdfWriter()
    base_name = "consenso_cartaceo"
    if files and getattr(files[0], "name", None):
        base_name = os.path.splitext(files[0].name)[0]
    for f in files:
        raw = f.read()
        ext = os.path.splitext(f.name)[1].lower()
        if ext in (".jpg", ".jpeg", ".png"):
            pdf_bytes = _image_to_pdf_bytes(raw)
            reader = PdfReader(io.BytesIO(pdf_bytes))
        else:
            reader = PdfReader(io.BytesIO(raw))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), f"{base_name}_FRONTE_RETRO.pdf"

def _whatsapp_link(text: str) -> str:
    return "https://wa.me/?text=" + _urlparse.quote(text)

def _mailto_link(subject: str, body: str) -> str:
    return "mailto:?subject=" + _urlparse.quote(subject) + "&body=" + _urlparse.quote(body)

# --- TOKEN (link pubblico firma) ---
def _b64url(b: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    import base64
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)

def _token_secret() -> bytes:
    sec = st.secrets.get("privacy", {}).get("TOKEN_SECRET")
    if not sec:
        raise RuntimeError("Secrets mancanti: [privacy].TOKEN_SECRET (string lunga e casuale)")
    return sec.encode("utf-8")

def _make_sign_token(paziente_id: int, doc_type: str, expires_seconds: int) -> str:
    payload = {
        "pid": int(paziente_id),
        "doc": str(doc_type),
        "exp": int(_dt.datetime.utcnow().timestamp()) + int(expires_seconds),
        "v": 1,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(_token_secret(), raw, hashlib.sha256).digest()
    return _b64url(raw) + "." + _b64url(sig)

def _parse_sign_token(tok: str) -> dict:
    try:
        a, b = tok.split(".", 1)
        raw = _b64url_decode(a)
        sig = _b64url_decode(b)
        exp_sig = hmac.new(_token_secret(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, exp_sig):
            raise ValueError("bad signature")
        payload = json.loads(raw.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(_dt.datetime.utcnow().timestamp()):
            raise ValueError("expired")
        return payload
    except Exception:
        return {}

def _public_sign_url(token: str) -> str:
    # usa base url configurabile, altrimenti prova a ricostruire dal browser
    base = st.secrets.get("privacy", {}).get("PUBLIC_BASE_URL", "")
    if base:
        return base.rstrip("/") + "/?sign=" + _urlparse.quote(token)
    # fallback: url relativo
    return "?sign=" + _urlparse.quote(token)

# --- EMAIL (invio a entrambi) ---
import smtplib
from email.message import EmailMessage

def _smtp_cfg():
    cfg = st.secrets.get("smtp", {})
    if not cfg.get("HOST") or not cfg.get("PORT") or not cfg.get("USERNAME") or not cfg.get("PASSWORD"):
        raise RuntimeError("Secrets mancanti: [smtp] HOST, PORT, USERNAME, PASSWORD. (Facoltativi: FROM, USE_TLS)")
    return cfg

def _send_email_with_pdf(to_list: list[str], subject: str, body: str, pdf_bytes: bytes, filename: str, pdf2_bytes: bytes | None = None, filename2: str | None = None):
    cfg = _smtp_cfg()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.get("FROM") or cfg.get("USERNAME")
    msg["To"] = ", ".join([x for x in to_list if x])
    msg.set_content(body)
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)
    if pdf2_bytes and filename2:
        msg.add_attachment(pdf2_bytes, maintype="application", subtype="pdf", filename=filename2)

    host = cfg["HOST"]
    port = int(cfg["PORT"])
    use_tls = str(cfg.get("USE_TLS", "true")).lower() in ("1","true","yes","y")
    if use_tls:
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(cfg["USERNAME"], cfg["PASSWORD"])
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port) as s:
            s.login(cfg["USERNAME"], cfg["PASSWORD"])
            s.send_message(msg)

def _clinic_email() -> str:
    return st.secrets.get("privacy", {}).get("CLINIC_EMAIL") or st.secrets.get("smtp", {}).get("FROM") or st.secrets.get("smtp", {}).get("USERNAME") or ""

def ui_privacy_pdf():
    st.subheader("📄 Privacy & Consensi (PDF)")

    # diagnostica rapida file template (non blocca la UI)
    try:
        _check_privacy_templates_ui()
    except Exception:
        pass


    # Sezione dedicata alla generazione/stampa dei PDF (cartaceo) e al salvataggio su cloud privato (se S3 configurato)
    conn = get_connection()

    # (facoltativo) assicurati che esista la tabella documenti se la usi
    try:
        _ensure_documenti_table(conn)
    except Exception:
        pass

    # Selezione paziente
    paz, _ptab, _pcolmap = fetch_pazienti_for_select(conn)
    if not paz:
        st.info("Nessun paziente presente.")
        return

    options = {f"{cognome} {nome} (ID {pid})": pid for (pid, cognome, nome, _dn, _sc, _eta) in paz}
    sel = st.selectbox("Seleziona paziente", list(options.keys()))
    pid = options[sel]

    doc_type = st.radio("Tipo consenso", ["adulto", "minore"], horizontal=True)
    template = PDF_PRIVACY_ADULTO_TEMPLATE if doc_type == "adulto" else PDF_PRIVACY_MINORE_TEMPLATE

    st.markdown("### ✍️ Firma online (link pubblico)")
    st.caption("Genera un link pubblico per la firma (senza login). Il link scade secondo PRESIGN_EXPIRE_SECONDS o un valore dedicato.")
    # scadenza token: usa privacy.TOKEN_EXPIRE_SECONDS se presente, altrimenti 48h
    exp = int(st.secrets.get("privacy", {}).get("TOKEN_EXPIRE_SECONDS", 172800))
    if st.button("🔗 Genera link firma online", key=f"gen_sign_{pid}_{doc_type}"):
        try:
            token = _make_sign_token(int(pid), doc_type, exp)
            url = _public_sign_url(token)
            st.success("Link generato ✅")
            st.code(url)
            # Link rapidi
            mail_body = "Apri questo link per firmare online:\n" + url
            st.markdown(f"- 📩 Email: {_mailto_link('Firma consenso privacy – Studio The Organism', mail_body)}")
            st.markdown(f"- 💬 WhatsApp: {_whatsapp_link('Apri questo link per firmare online: ' + url)}")
        except Exception as e:
            st.error(f"Impossibile generare il link: {type(e).__name__}: {e}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🖨️ Stampa / Scarica (cartaceo)")
        try:
            with open(_privacy_abs_path(template), "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                "⬇️ Scarica PDF da stampare",
                data=pdf_bytes,
                file_name=f"privacy_{doc_type}_stampabile.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Impossibile leggere il template PDF: {e}")
            return

    with col2:
        st.markdown("### ☁️ Archivia su Cloud (opzionale)")
        st.caption("Usa questa funzione solo se hai configurato S3 nei Secrets.")
        if st.button("📤 Carica su cloud il PDF (template) per questo paziente"):
            # Key univoca (template associato al paziente)
            digest = _sha256_bytes(pdf_bytes)
            key = f"consensi/{pid}/template/privacy_{doc_type}_{digest[:10]}.pdf"

            ok_s3, msg_s3 = (True, "S3 disabilitato (archiviazione su Neon)")
            if not ok_s3:
                st.error(f"Upload S3 disabilitato: {msg_s3}")
                return

            # salva su DB SOLO se upload ok
            try:
                _db_insert_documento(conn, int(pid), f"privacy_{doc_type}_template", key, digest, f"privacy_{doc_type}_template.pdf")
                st.success("Caricato e registrato nel DB ✅")
            except Exception as e:
                st.warning(f"Caricato su S3, ma DB non aggiornato: {e}")

            # link presigned (se disponibile)
            try:
                url = _s3_presign_get(key)
                st.write("Link (24h):")
                st.code(url)
            except Exception:
                pass

def ui_public_sign_page():
    """Pagina pubblica: compilazione + firma online (canvas) + invio PDF a clinica e paziente."""
    st.set_page_config(page_title="The Organism – Consenso online", layout="centered")
    qp = st.query_params
    tok = qp.get("sign", "")
    payload = _parse_sign_token(tok) if tok else {}
    if not payload:
        st.error("Link non valido o scaduto. Richiedi un nuovo link allo studio.")
        return

    pid = int(payload["pid"])
    doc_type = payload["doc"]  # 'adulto' / 'minore'
    # connessione DB
    conn = get_connection()
    _ensure_documenti_table(conn)

    # recupera paziente per prefill (se disponibile)
    paz_list, _, _ = fetch_pazienti_for_select(conn)
    paz_row = None
    for r in paz_list:
        if int(r[0]) == pid:
            paz_row = r
            break
    cogn = paz_row[1] if paz_row else ""
    nome = paz_row[2] if paz_row else ""

    template_path = _privacy_abs_path(PDF_PRIVACY_ADULTO_SIGN_TEMPLATE if doc_type == "adulto" else PDF_PRIVACY_MINORE_SIGN_TEMPLATE)

    # diagnostica template (utile se manca il file in cloud)
    try:
        _check_privacy_templates_ui()
    except Exception:
        pass
    if not os.path.exists(template_path):
        st.error("Template consenso non disponibile. Contatta lo studio.")
        return

    st.title("Consenso informato e privacy")
    st.caption("Compila i dati e firma. Alla conferma, riceverai una copia via email.")

    # campi base
    if doc_type == "adulto":
        email = st.text_input("Email", value="")
        tel = st.text_input("Telefono", value="")
        nome_cognome = st.text_input("Nome e Cognome", value=f"{nome} {cogn}".strip())
    else:
        email = st.text_input("Email Genitore/Tutore (per ricevere copia)", value="")
        tel = st.text_input("Telefono Genitore/Tutore", value="")
        nome_cognome = st.text_input("Nome e Cognome del minore", value=f"{nome} {cogn}".strip())

    st.subheader("Firma")
    if st_canvas is None:
        st.warning("Firma online non disponibile (manca dipendenza). Carica un PDF firmato oppure contatta lo studio.")
        st.stop()

    canvas = st_canvas(
        fill_color="rgba(0, 0, 0, 0)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#ffffff",
        height=180,
        width=520,
        drawing_mode="freedraw",
        key="sigcanvas"
    )

    st.subheader("Consensi (Sì/No)")
    # radio minimi
    if doc_type == "adulto":
        gdpr_letto = st.radio("Ho letto l'informativa GDPR (pag. 2)", ["SI", "NO"], horizontal=True, index=0)
        cons_dati = st.radio("Consenso trattamento dati personali", ["SI", "NO"], horizontal=True, index=0)
        cons_salute = st.radio("Consenso trattamento dati salute", ["SI", "NO"], horizontal=True, index=0)
        cons_marketing = st.radio("Consenso comunicazioni informative/marketing (facoltativo)", ["SI", "NO"], horizontal=True, index=1)
    else:
        gdpr_letto = st.radio("Abbiamo letto l'informativa GDPR (pag. 2)", ["SI", "NO"], horizontal=True, index=0)
        cons_dati = st.radio("Consenso trattamento dati personali del minore", ["SI", "NO"], horizontal=True, index=0)
        cons_salute = st.radio("Consenso trattamento dati salute del minore", ["SI", "NO"], horizontal=True, index=0)
        cons_marketing = st.radio("Consenso comunicazioni informative/marketing (facoltativo)", ["SI", "NO"], horizontal=True, index=1)

    confirm = st.checkbox("Confermo che i dati inseriti sono corretti e presto il consenso come sopra indicato.", value=False)

    if st.button("Invia consenso"):
        if not confirm:
            st.error("Spunta la conferma prima di inviare.")
            st.stop()
        if not email.strip():
            st.error("Inserisci un'email valida per ricevere la copia.")
            st.stop()

        # estrai firma come immagine PNG
        try:
            import numpy as np
            import PIL.Image
            arr = canvas.image_data
            if arr is None:
                raise ValueError("no canvas")
            img = PIL.Image.fromarray(arr.astype('uint8'), 'RGBA')
            # riduci trasparenza su bianco
            bg = PIL.Image.new("RGBA", img.size, (255,255,255,255))
            bg.alpha_composite(img)
            sig_rgb = bg.convert("RGB")
            sig_buf = io.BytesIO()
            sig_rgb.save(sig_buf, format="PNG")
            sig_png = sig_buf.getvalue()
            has_sig = sig_rgb.getbbox() is not None
        except Exception:
            sig_png = b""
            has_sig = False

        if not has_sig:
            st.error("Firma mancante: disegna la firma nel riquadro.")
            st.stop()

        # genera PDF precompilato
        fields = {}
        if doc_type == "adulto":
            fields = {
                "a_nome_cognome": nome_cognome.strip(),
                "a_email": email.strip(),
                "a_tel": tel.strip(),
                "a_gdpr_letto": gdpr_letto,
                "a_cons_dati": cons_dati,
                "a_cons_salute": cons_salute,
                "a_cons_marketing": cons_marketing,
            }
        else:
            fields = {
                "m_nome_cognome": nome_cognome.strip(),
                "g1_email": email.strip(),
                "g1_tel": tel.strip(),
                "m_gdpr_letto": gdpr_letto,
                "m_cons_dati": cons_dati,
                "m_cons_salute": cons_salute,
                "m_cons_marketing": cons_marketing,
            }

        base_pdf = _prefill_pdf(template_path, fields)
        extra_pdf = None
        extra_name = None

        # crea una pagina "firma" con immagine + timestamp, e la unisce al PDF
        from reportlab.pdfgen import canvas as _rl_canvas
        from reportlab.lib.pagesizes import A4 as _A4
        from reportlab.lib.units import mm as _mm
        sig_page = io.BytesIO()
        c = _rl_canvas.Canvas(sig_page, pagesize=_A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20*_mm, 285*_mm, "Firma elettronica (grafometrica) – Allegato")
        c.setFont("Helvetica", 10)
        c.drawString(20*_mm, 275*_mm, f"Paziente ID: {pid} – Tipo: {doc_type}")
        c.drawString(20*_mm, 268*_mm, f"Data/ora (UTC): {_dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(20*_mm, 261*_mm, f"Email: {email.strip()}")
        c.drawString(20*_mm, 254*_mm, "Firma acquisita tramite pagina web; copia inviata a studio e interessato.")
        # disegna immagine firma
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(sig_png)
            tmp_path = tmp.name
        c.drawImage(tmp_path, 20*_mm, 190*_mm, width=120*_mm, height=40*_mm, preserveAspectRatio=True, mask='auto')
        c.rect(20*_mm, 190*_mm, 120*_mm, 40*_mm)
        c.showPage()
        c.save()
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        sig_page_bytes = sig_page.getvalue()

        # init
        extra_pdf = None
        extra_name = None

        # merge base_pdf + sig_page (robusto: se il PDF base è illeggibile/monco, inviamo 2 allegati separati)
        final_pdf = None
        extra_pdf = None
        extra_name = None
        try:
            r1 = PdfReader(io.BytesIO(base_pdf))
            r2 = PdfReader(io.BytesIO(sig_page_bytes))
            w = PdfWriter()
            for p in r1.pages:
                w.add_page(p)
            for p in r2.pages:
                w.add_page(p)
            out = io.BytesIO()
            w.write(out)
            final_pdf = out.getvalue()
        except Exception:
            # fallback: non bloccare il consenso online
            final_pdf = base_pdf
            extra_pdf = sig_page_bytes
            extra_name = f"Firma_Allegato_{doc_type}.pdf"
        # --- ARCHIVIAZIONE SU CLOUD PRIVATO (NO AcroForm) ---
        if not final_pdf or len(final_pdf) < 1000:
            # fallback: at least send/archivia the base template
            final_pdf = base_pdf
        digest = _sha256_bytes(final_pdf)
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"consensi/{pid}/firmati/privacy_{doc_type}/online_{ts}_{digest[:10]}.pdf"
        ok_s3, msg_s3 = (True, "S3 disabilitato (archiviazione su Neon)")
        ok_upload = ok_s3
        if not ok_upload:
            st.error(f"Upload S3 disabilitato: {msg_s3}")
            st.warning("Documento archiviato su Neon. (S3 disabilitato). Il PDF verrà comunque inviato via email se configurata.")
        else:
            _db_insert_documento(conn, int(pid), f"privacy_{doc_type}_online", key, digest, f"privacy_{doc_type}_online.pdf")

        
        # --- SALVATAGGIO CONSENSO SU DB (Consensi_Privacy) ---
        try:
            cur = conn.cursor()
            payload_db = {
                "Data_Ora": _now_iso_dt(),
                "Tipo": "MINORE" if doc_type == "minore" else "ADULTO",
                "Tutore_Nome": "",
                "Tutore_CF": "",
                "Tutore_Telefono": "",
                "Tutore_Email": "",
                # mapping consensi (pagina online)
                "Consenso_Trattamento": bool(cons_dati),
                "Consenso_Comunicazioni": True,   # gestione appuntamenti / comunicazioni di servizio
                "Consenso_Marketing": bool(cons_marketing),
                "Canale_Email": True,
                "Canale_SMS": False,
                "Canale_WhatsApp": False,
                "Usa_Klaviyo": bool(cons_marketing),
                "Firma_Blob": sig_png,
                "Firma_Filename": "firma_online.png",
                "Firma_URL": "",
                "Firma_Source": "online",
                "Pdf_Blob": final_pdf,
                "Pdf_Filename": f"Consenso_{doc_type}_online.pdf",
                "Note": "Consenso firmato online",
            }
            insert_privacy_consent(cur, int(pid), payload_db)
            conn.commit()
        except Exception as e:
            st.warning(f"Consenso inviato/archiviato, ma non salvato nello storico DB: {e}")


# Se il merge fallisce, archiviamo anche la pagina firma separata
        extra_key = None
        if extra_pdf is not None and extra_name:
            extra_digest = _sha256_bytes(extra_pdf)
            extra_key = f"consensi/{pid}/firmati/privacy_{doc_type}/online_{ts}_{extra_digest[:10]}_{extra_name}"
            _s3_put_private(extra_key, extra_pdf, content_type="application/pdf")
            _db_insert_documento(conn, int(pid), f"privacy_{doc_type}_online_firma", extra_key, extra_digest, extra_name)


        # invio email a entrambi
    email_ok = True
    try:
        to_list = [email.strip(), _clinic_email()]
        subject = "Consenso informato e privacy – Studio The Organism"
        body = "In allegato trovi copia del consenso informato e privacy firmato.\n\nStudio The Organism"
        _send_email_with_pdf(to_list, subject, body, final_pdf, f"Consenso_{doc_type}.pdf", extra_pdf, extra_name)
    except Exception as e:
        email_ok = False
        st.warning(f"Consenso archiviato su Neon, ma invio email non riuscito: {e}")

    if email_ok:
        st.success("✅ Consenso archiviato su Neon e inviato via email. Puoi chiudere questa pagina.")
    else:
        st.success("✅ Consenso archiviato su Neon. Puoi chiudere questa pagina.")
def main():
    st.set_page_config(
        page_title="The Organism – Gestionale Studio",
        layout="wide"
    )

    # --- PUBLIC SIGN PAGE (no login) ---
    if st.query_params.get('sign'):
        ui_public_sign_page()
        return

    _sidebar_db_indicator()

    # inizializza il database (se le tabelle non ci sono le crea)
    init_db()

    # login obbligatorio
    if not login(get_connection):
        return

    # menu laterale
    st.sidebar.title("Navigazione")
    sections = [
        "Pazienti",
        "Valutazione PNEV",
        "Valutazioni visive / oculistiche",
        "Sedute / Terapie",
        "Osteopatia",
        "Coupon OF / SDS",
        "Dashboard incassi",
        "🗂️ Relazioni cliniche",
        "📊 Dashboard evolutiva",
        "📄 Privacy & Consensi (PDF)",
        "🛠️ Debug DB",
        "📥 Import Pazienti",
    ]
    if is_admin():
        sections.append("👥 Utenti / Ruoli")

    if APP_MODE == "test":
        sections.append("🧹 Pulizia DB (TEST)")
    sezione = st.sidebar.radio("Vai a", sections)

    # routing alle varie sezioni
    if sezione == "Pazienti":
        ui_pazienti()
    elif sezione == "Valutazione PNEV":
        ui_anamnesi()
    elif sezione == "Valutazioni visive / oculistiche":
        ui_valutazioni_visive()
    elif sezione == "Sedute / Terapie":
        ui_sedute()
    elif sezione == "Osteopatia":
        ui_osteopatia_section()
    elif sezione == "Coupon OF / SDS":
        ui_coupons()
    elif sezione == "Dashboard incassi":
        ui_dashboard()
    elif sezione == "🗂️ Relazioni cliniche":
        ui_relazioni_cliniche()
    elif sezione == "📊 Dashboard evolutiva":
        ui_dashboard_evolutiva()
    elif sezione == "📄 Privacy & Consensi (PDF)":
        ui_privacy_pdf()
    elif sezione == "🛠️ Debug DB":
        ui_debug_db()
    elif sezione == "📥 Import Pazienti":
        ui_import_pazienti()
    elif sezione == "👥 Utenti / Ruoli":
        ui_gestione_utenti(get_connection)
    elif sezione == "🧹 Pulizia DB (TEST)":
        ui_db_cleanup()


# ================================
# RELAZIONI CLINICHE - THE ORGANISM
# ================================
import shutil as _shutil

try:
    from docxtpl import DocxTemplate
except Exception:
    DocxTemplate = None

def _ensure_relazioni_cliniche_table(conn):
    """Crea la tabella relazioni_cliniche sia su SQLite che su PostgreSQL (Neon)."""
    cur = conn.cursor()
    # Prova prima sintassi PostgreSQL (psycopg2)
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS relazioni_cliniche (
          id BIGSERIAL PRIMARY KEY,
          paziente_id BIGINT NOT NULL,
          tipo TEXT NOT NULL,
          titolo TEXT NOT NULL,
          data_relazione DATE NOT NULL,
          docx_path TEXT NOT NULL,
          pdf_path TEXT NOT NULL,
          note TEXT,
          created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
        except Exception:
            pass
        conn.commit()
        return
    except Exception:
        # Fallback SQLite
        pass

    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS relazioni_cliniche (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paziente_id INTEGER NOT NULL,
          tipo TEXT NOT NULL,
          titolo TEXT NOT NULL,
          data_relazione TEXT NOT NULL,
          docx_path TEXT NOT NULL,
          pdf_path TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL
        )
        """)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
        except Exception:
            pass
        conn.commit()
    except Exception:
        # ultima risorsa: non bloccare l'app
        try:
            conn.rollback()
        except Exception:
            pass

def _render_docx_docxtpl(template_path, out_docx_path, context):
    if DocxTemplate is None:
        raise RuntimeError("Dipendenza mancante: docxtpl. Aggiungi a requirements.txt: docxtpl")
    doc = DocxTemplate(template_path)
    doc.render(context)
    os.makedirs(os.path.dirname(out_docx_path), exist_ok=True)
    doc.save(out_docx_path)

def _convert_pdf_if_possible(docx_path, out_pdf_path):
    # Streamlit Cloud: spesso NON disponibile. In locale funziona se LibreOffice è installato.
    soffice_ok = _shutil.which("soffice") is not None
    if not soffice_ok:
        return False, ""
    import subprocess, shutil
    out_dir = os.path.dirname(out_pdf_path)
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        "soffice","--headless","--nologo","--nolockcheck","--nodefault","--norestore",
        "--convert-to","pdf","--outdir", out_dir, docx_path
    ]
    subprocess.run(cmd, check=True)
    gen = os.path.join(out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if not os.path.exists(gen):
        return False, ""
    shutil.move(gen, out_pdf_path)
    return True, out_pdf_path

# ==========================
# Bibliografia (PNEV / INPP- INPPS) — inserita automaticamente in TUTTE le relazioni cliniche
# Nota: nei template .docx inserisci il placeholder: {{ BIBLIOGRAFIA }}
# ==========================
BIBLIOGRAFIA_PNEV = """
BIBLIOGRAFIA E RIFERIMENTI CLINICO-SCIENTIFICI (selezione)

INPP / INPPS – neuromotor readiness, riflessi primitivi e apprendimento
• Demiy A, Kalemba A, Lorent M, Pecuch A, Wolańska E, Telenga M, Gieysztor EZ. (2020).
  A Child’s Perception of Their Developmental Difficulties in Relation to Their Adult Assessment.
  Analysis of the INPP Questionnaire. Journal of Personalized Medicine, 10(4), 156.

• Goddard Blythe S. (2005). Reflexes, Learning and Behavior: A Window into the Child’s Mind. Fern Ridge Press.
• Goddard Blythe S. (2009). Attention, Balance and Coordination: The A.B.C. of Learning Success. Wiley-Blackwell.
• Goddard Blythe S. (2012). Assessing Neuromotor Readiness for Learning:
  The INPP Developmental Screening Test and School Intervention Programme. Wiley-Blackwell.

Nota clinica (screening):
Nel protocollo PNEV/INPPS, un numero elevato di affermazioni positive ai questionari di screening
è considerato indicativo di possibile immaturità neuromotoria e richiede conferma tramite valutazione clinica diretta.
"""

TEMPLATES = {
  # Linguaggio (ospedaliero) - unico template
  "linguaggio_invio_ospedaliero": {
    "titolo": "Relazione Linguaggio – Invio Ospedaliero",
    "files": {"std": "relazione_linguaggio_invio_ospedaliero.docx"}
  },
  # Neuropsicologica
  "neuropsicologica_3_6": {
    "titolo": "Relazione Neuropsicologica – Invio Ospedaliero (3–6)",
    "files": {"std": "relazione_neuropsicologica_invio_ospedaliero_3_6.docx"}
  },
  "neuropsicologica_6_10": {
    "titolo": "Relazione Neuropsicologica – Invio Ospedaliero (6–10)",
    "files": {"std": "relazione_neuropsicologica_invio_ospedaliero_6_10.docx"}
  },
  # Neuroevolutiva integrata
  "neuroevolutiva_3_6": {
    "titolo": "Relazione Neuroevolutiva Integrata (3–6)",
    "files": {"std": "relazione_neuroevolutiva_integrata_3_6.docx"}
  },
  "neuroevolutiva_6_10": {
    "titolo": "Relazione Neuroevolutiva Integrata (6–10)",
    "files": {"std": "relazione_neuroevolutiva_integrata_6_10.docx"}
  },
  # Scuola / ASL
  "scuola_asl_3_6": {
    "titolo": "Relazione Scuola / ASL (3–6)",
    "files": {"std": "relazione_scuola_asl_3_6.docx"}
  },
  "scuola_asl_6_10": {
    "titolo": "Relazione Scuola / ASL (6–10)",
    "files": {"std": "relazione_scuola_asl_6_10.docx"}
  },
  # Sensori-motoria / Neuro-psico-motoria
  "sensori_motorio_3_6": {
    "titolo": "Relazione Sensori-motoria / Neuro-psico-motoria (3–6)",
    "files": {"std": "relazione_sensori_motorio_neuropsicomotorio_3_6.docx"}
  },
  "sensori_motorio_6_10": {
    "titolo": "Relazione Sensori-motoria / Neuro-psico-motoria (6–10)",
    "files": {"std": "relazione_sensori_motorio_neuropsicomotorio_6_10.docx"}
  },
  # SMOF
  "smof_3_6": {
    "titolo": "Relazione SMOF / Oro-linguale (3–6)",
    "files": {"std": "relazione_smof_oro_linguale_3_6.docx"}
  },
  "smof_6_10": {
    "titolo": "Relazione SMOF / Oro-linguale (6–10)",
    "files": {"std": "relazione_smof_oro_linguale_6_10.docx"}
  },
  # Follow-up
  "followup_3_6": {
    "titolo": "Relazione Follow-up (3–6)",
    "files": {"std": "relazione_followup_3_6.docx"}
  },
  "followup_6_10": {
    "titolo": "Relazione Follow-up (6–10)",
    "files": {"std": "relazione_followup_6_10.docx"}
  },
}

def ui_relazioni_cliniche(templates_dir="templates", output_base="output"):
    import streamlit as st
    from datetime import date


    # conn & selezione paziente (AUTO) - indipendente dalla sezione Pazienti
    conn = get_connection()
    paz_list, paz_table, paz_colmap = fetch_pazienti_for_select(conn)
    if not paz_list:
        st.error("Nessun paziente trovato nel database (AUTO).")
        st.info("Apri la sezione 🛠️ Debug DB per vedere quali tabelle sono presenti su Neon.")
        if paz_table or paz_colmap:
            st.caption(f"Rilevato: {paz_table} • Colonne: {paz_colmap}")
        return

    cur = conn.cursor()

    def _label(p):
        pid, cogn, nome, dn, scuola, eta = p
        dn_s = dn or ""
        extra = ""
        if eta: extra += f" • {eta} anni"
        if scuola: extra += f" • {scuola}"
        return f"{cogn} {nome} (ID {pid}) {dn_s}{extra}".strip()

    sel = st.selectbox("Seleziona paziente", paz_list, format_func=_label)
    try:
        paziente_id = sel[0]
    except Exception:
        paziente_id = None
    if not paziente_id:
        st.error("Errore: ID paziente non determinabile.")
        return

    # carica dati base paziente (nome/cognome/data nascita) per template
    paziente = {"id": paziente_id, "cognome": sel[1], "nome": sel[2], "data_nascita": sel[3], "scuola": sel[4], "eta": sel[5]}

    _ensure_relazioni_cliniche_table(conn)

    st.header("🗂️ Relazioni cliniche")
    st.caption("Generazione: Word sempre (cloud) • PDF solo in locale se LibreOffice è disponibile")

    # Selezione tipo relazione
    keys = list(TEMPLATES.keys())
    labels = [TEMPLATES[k]["titolo"] for k in keys]
    idx = 0
    scelta = st.selectbox("Tipo relazione", options=list(range(len(keys))), format_func=lambda i: labels[i])
    rel_key = keys[scelta]
    rel = TEMPLATES[rel_key]

    c1, c2 = st.columns(2)
    with c1:
        data_valutazione = st.date_input("Data valutazione", value=date.today())
    with c2:
        data_relazione = st.date_input("Data relazione", value=date.today())

    periodo_followup = ""
    if "followup" in rel_key:
        periodo_followup = st.text_input("Periodo follow-up (es. Gen–Mar 2026)", value="")

    note = st.text_area("Note cliniche (facoltative)", height=140)

    # Context placeholder comune
    nome_cognome = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip()
    # --- Aggancio automatico screening INPPS (se presente in PNEV) ---
    try:
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT pnev_json, pnev_summary FROM Anamnesi WHERE Paziente_ID = ? ORDER BY Data_Anamnesi DESC, ID DESC LIMIT 1",
            (paziente_id,),
        )
        r_inpps = cur2.fetchone()
        if r_inpps:
            pnev_obj = pnev.pnev_load(r_inpps.get("pnev_json") if hasattr(r_inpps, "get") else r_inpps[0])
            inpps_obj = (pnev_obj.get("questionari", {}) or {}).get("inpps_screening_genitori")
            if isinstance(inpps_obj, dict):
                scr = inpps_obj.get("screening") or {}
                if isinstance(scr, dict) and scr.get("totale_positivi") is not None:
                    tot = scr.get("totale_positivi")
                    cutoff = scr.get("cutoff", 7)
                    flag = bool(scr.get("flag_possibile_immaturita_neuromotoria"))
                    txt = f"Screening INPPS (genitori): totale positivi {tot} (cut-off ≥ {cutoff}). "
                    if flag:
                        txt += "Indicativo di possibile immaturità neuromotoria (screening) – raccomandata conferma clinica diretta."
                    else:
                        txt += "Nessun alert da screening."
                    NOTE_CLINICHE = (NOTE_CLINICHE or "").strip()
                    NOTE_CLINICHE = (NOTE_CLINICHE + "\n\n" + txt).strip() if NOTE_CLINICHE else txt
    except Exception:
        pass


    context = {
        "NOME_COGNOME": nome_cognome,
        "DATA_NASCITA": paziente.get("data_nascita",""),
        "ETA": paziente.get("eta",""),
        "SCUOLA": paziente.get("scuola",""),
        "DATA_VALUTAZIONE": data_valutazione.strftime("%d/%m/%Y"),
        "DATA_RELAZIONE": data_relazione.strftime("%d/%m/%Y"),
        "NOTE_CLINICHE": note.strip(),
        "PERIODO_FOLLOWUP": periodo_followup.strip(),
        "BIBLIOGRAFIA": BIBLIOGRAFIA_PNEV.strip(),

    }

    template_file = rel["files"]["std"]
    template_path = os.path.join(templates_dir, template_file)

    if st.button("📄 Genera Word ( + PDF se disponibile )", type="primary"):
        if not os.path.exists(template_path):
            st.error(f"Template mancante: {template_path}")
            st.stop()

        pid = paziente.get("id")
        safe_name = (nome_cognome.replace(" ", "_") or f"PAZ_{pid}")
        out_dir = os.path.join(output_base, f"{pid}_{safe_name}", "relazioni_cliniche")
        os.makedirs(out_dir, exist_ok=True)

        base = f"{data_relazione.strftime('%Y-%m-%d')}_{rel_key}_{safe_name}"
        out_docx = os.path.join(out_dir, base + ".docx")
        out_pdf  = os.path.join(out_dir, base + ".pdf")

        try:
            _render_docx_docxtpl(template_path, out_docx, context)
        except Exception as e:
            st.error(f"Errore Word: {e}")
            st.stop()

        pdf_ok, pdf_path = _convert_pdf_if_possible(out_docx, out_pdf)
        if not pdf_ok:
            pdf_path = ""  # cloud-safe

        # salva DB
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO relazioni_cliniche (paziente_id, tipo, titolo, data_relazione, docx_path, pdf_path, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (pid, rel_key, rel["titolo"], data_relazione.strftime("%Y-%m-%d"), out_docx, pdf_path, note.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

        st.success("Relazione generata ✅")
        with open(out_docx, "rb") as f:
            st.download_button("⬇️ Scarica Word", f, file_name=os.path.basename(out_docx), key=f"dw_{rel_key}_{pid}")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Scarica PDF", f, file_name=os.path.basename(pdf_path), key=f"dp_{rel_key}_{pid}")
        else:
            st.info("PDF non disponibile in cloud: apri il Word e salva in PDF dal PC in studio.")

if __name__ == "__main__":
    main()
