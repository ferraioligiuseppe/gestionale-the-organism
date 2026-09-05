# -*- coding: utf-8 -*-
"""
Diario clinico — registro per paziente, ibrido automatico/manuale.
"""

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

from .trascrizione_audio import trascrivi_audio, trascrizione_disponibile

TZ = ZoneInfo("Europe/Rome")

TIPI_VOCE = {
    "anamnesi": "Anamnesi",
    "valutazione": "Valutazione / Testing",
    "seduta": "Seduta",
    "verifica": "Verifica intermedia",
    "colloquio": "Colloquio famiglia",
    "programma": "Programma / Piano di lavoro",
    "comunicazione": "Comunicazione esterna",
    "chiusura": "Chiusura percorso",
    "nota": "Nota libera",
}

DDL = """
CREATE TABLE IF NOT EXISTS diario_clinico (
    id                  BIGSERIAL PRIMARY KEY,
    studio_id           BIGINT      NOT NULL,
    paziente_id         BIGINT      NOT NULL,
    data_voce           TIMESTAMPTZ NOT NULL DEFAULT now(),
    tipo_voce           TEXT        NOT NULL,
    titolo              TEXT,
    riassunto           TEXT,
    testo               TEXT,
    generato_da         TEXT        NOT NULL DEFAULT 'manuale',
    modulo_origine      TEXT,
    riferimento_id      BIGINT,
    autore              TEXT,
    visibile_in_referto BOOLEAN     NOT NULL DEFAULT TRUE,
    eliminato           BOOLEAN     NOT NULL DEFAULT FALSE,
    creato_il           TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_diario_tipo
        CHECK (tipo_voce IN ('anamnesi','valutazione','seduta','verifica',
                             'colloquio','programma','comunicazione',
                             'chiusura','nota')),
    CONSTRAINT chk_diario_generato
        CHECK (generato_da IN ('auto','manuale','auto_modificato'))
);

CREATE INDEX IF NOT EXISTS idx_diario_paziente
    ON diario_clinico (studio_id, paziente_id, data_voce DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_diario_origine
    ON diario_clinico (studio_id, modulo_origine, riferimento_id)
    WHERE modulo_origine IS NOT NULL AND riferimento_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS diario_clinico_audio (
    id          BIGSERIAL PRIMARY KEY,
    studio_id   BIGINT      NOT NULL,
    voce_id     BIGINT      NOT NULL REFERENCES diario_clinico(id) ON DELETE CASCADE,
    ordine      INT         NOT NULL,
    speaker     TEXT        NOT NULL,
    mime        TEXT        NOT NULL DEFAULT 'audio/wav',
    dati        BYTEA       NOT NULL,
    trascritto  TEXT,
    creato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_diario_audio_speaker CHECK (speaker IN ('professionista', 'paziente'))
);

CREATE INDEX IF NOT EXISTS idx_diario_audio_voce
    ON diario_clinico_audio (voce_id, ordine);
"""

RLS = """
ALTER TABLE diario_clinico ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_diario_tenant ON diario_clinico;
CREATE POLICY pol_diario_tenant ON diario_clinico
    USING (studio_id = current_setting('app.studio_id')::BIGINT)
    WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);

ALTER TABLE diario_clinico_audio ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_diario_audio_tenant ON diario_clinico_audio;
CREATE POLICY pol_diario_audio_tenant ON diario_clinico_audio
    USING (studio_id = current_setting('app.studio_id')::BIGINT)
    WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
"""


def _adesso():
    return datetime.now(TZ)


def crea_schema(conn):
    """Idempotente: chiamata a ogni apertura del modulo."""
    try:
        conn.rollback()
    except Exception:
        pass
    cur = conn.cursor()
    cur.execute(DDL)
    try:
        cur.execute(RLS)
    except Exception:
        conn.rollback()
        cur = conn.cursor()
        cur.execute(DDL)
    conn.commit()


# ---------------------------------------------------------------------------
# Scrittura
# ---------------------------------------------------------------------------
def registra_voce_diario(conn, studio_id, paziente_id, tipo_voce, modulo_origine,
                         riferimento_id, riassunto, testo=None, titolo=None,
                         autore=None, data_voce=None):
    """Chiamata dai moduli clinici in coda al salvataggio."""
    if tipo_voce not in TIPI_VOCE:
        raise ValueError("tipo_voce non valido: %s" % tipo_voce)
    data_voce = data_voce or _adesso()
    sql = """
        INSERT INTO diario_clinico
            (studio_id, paziente_id, data_voce, tipo_voce, titolo,
             riassunto, testo, generato_da, modulo_origine, riferimento_id, autore)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'auto', %s, %s, %s)
        ON CONFLICT (studio_id, modulo_origine, riferimento_id)
        DO UPDATE SET
            data_voce = EXCLUDED.data_voce, tipo_voce = EXCLUDED.tipo_voce,
            titolo = EXCLUDED.titolo, riassunto = EXCLUDED.riassunto,
            testo = EXCLUDED.testo, aggiornato_il = now()
        WHERE diario_clinico.generato_da = 'auto'
        RETURNING id;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, paziente_id, data_voce, tipo_voce, titolo,
                      riassunto, testo, modulo_origine, riferimento_id, autore))
    row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def salva_clip_audio(conn, studio_id, voce_id, ordine, speaker, mime, dati, trascritto=None):
    sql = """
        INSERT INTO diario_clinico_audio
            (studio_id, voce_id, ordine, speaker, mime, dati, trascritto)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, voce_id, ordine, speaker, mime, dati, trascritto))
    nuovo_id = cur.fetchone()[0]
    conn.commit()
    return nuovo_id


def lista_clip_audio(conn, studio_id, voce_id):
    sql = """
        SELECT id, ordine, speaker, mime, dati, trascritto, creato_il
          FROM diario_clinico_audio
         WHERE studio_id = %s AND voce_id = %s
         ORDER BY ordine ASC;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, voce_id))
    righe = cur.fetchall()
    chiavi = ["id", "ordine", "speaker", "mime", "dati", "trascritto", "creato_il"]
    return [dict(zip(chiavi, r)) for r in righe]


def aggiungi_nota(conn, studio_id, paziente_id, tipo_voce, testo, titolo=None,
                  riassunto=None, autore=None, data_voce=None):
    if tipo_voce not in TIPI_VOCE:
        raise ValueError("tipo_voce non valido: %s" % tipo_voce)
    data_voce = data_voce or _adesso()
    if not riassunto:
        riassunto = (testo or "")[:200]
    sql = """
        INSERT INTO diario_clinico
            (studio_id, paziente_id, data_voce, tipo_voce, titolo,
             riassunto, testo, generato_da, autore)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'manuale', %s)
        RETURNING id;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, paziente_id, data_voce, tipo_voce, titolo,
                      riassunto, testo, autore))
    nuovo_id = cur.fetchone()[0]
    conn.commit()
    return nuovo_id


def aggiorna_voce(conn, studio_id, voce_id, titolo=None, riassunto=None, testo=None,
                  tipo_voce=None, visibile_in_referto=None):
    campi, valori = [], []
    for nome, val in (("titolo", titolo), ("riassunto", riassunto),
                      ("testo", testo), ("tipo_voce", tipo_voce),
                      ("visibile_in_referto", visibile_in_referto)):
        if val is not None:
            campi.append("%s = %%s" % nome)
            valori.append(val)
    if not campi:
        return False
    campi.append("aggiornato_il = now()")
    campi.append("generato_da = CASE WHEN generato_da = 'auto' "
                 "THEN 'auto_modificato' ELSE generato_da END")
    sql = ("UPDATE diario_clinico SET " + ", ".join(campi) +
           " WHERE id = %s AND studio_id = %s AND eliminato = FALSE;")
    valori.extend([voce_id, studio_id])
    cur = conn.cursor()
    cur.execute(sql, tuple(valori))
    ok = cur.rowcount > 0
    conn.commit()
    return ok


def elimina_voce(conn, studio_id, voce_id):
    cur = conn.cursor()
    cur.execute(
        "UPDATE diario_clinico SET eliminato = TRUE, aggiornato_il = now() "
        "WHERE id = %s AND studio_id = %s;", (voce_id, studio_id))
    ok = cur.rowcount > 0
    conn.commit()
    return ok


# ---------------------------------------------------------------------------
# Lettura
# ---------------------------------------------------------------------------
_COLONNE = """id, paziente_id, data_voce, tipo_voce, titolo, riassunto, testo,
              generato_da, modulo_origine, riferimento_id, autore,
              visibile_in_referto, creato_il, aggiornato_il"""


def _riga_dict(r):
    chiavi = [c.strip() for c in _COLONNE.replace("\n", "").split(",")]
    return dict(zip(chiavi, r))


def lista_voci(conn, studio_id, paziente_id, tipi=None, solo_referto=False, limite=None):
    sql = ("SELECT " + _COLONNE + " FROM diario_clinico "
           "WHERE studio_id = %s AND paziente_id = %s AND eliminato = FALSE")
    valori = [studio_id, paziente_id]
    if tipi:
        sql += " AND tipo_voce = ANY(%s)"
        valori.append(list(tipi))
    if solo_referto:
        sql += " AND visibile_in_referto = TRUE"
    sql += " ORDER BY data_voce DESC, id DESC"
    if limite:
        sql += " LIMIT %s"
        valori.append(limite)
    cur = conn.cursor()
    cur.execute(sql, tuple(valori))
    righe = cur.fetchall()
    return [_riga_dict(r) for r in righe]


def conteggio_per_tipo(conn, studio_id, paziente_id):
    sql = """
        SELECT tipo_voce, COUNT(*) FROM diario_clinico
         WHERE studio_id = %s AND paziente_id = %s AND eliminato = FALSE
      GROUP BY tipo_voce;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, paziente_id))
    return {t: n for t, n in cur.fetchall()}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def _render_registratore_seduta(conn, studio_id, paz_id):
    chiave_turni = f"diario_turni_{paz_id}"
    if chiave_turni not in st.session_state:
        st.session_state[chiave_turni] = []
    turni = st.session_state[chiave_turni]

    with st.expander("🎙️ Registra la seduta (professionista / paziente)", expanded=bool(turni)):
        if not trascrizione_disponibile():
            st.warning("Trascrizione automatica non configurata (manca chiave AI nei Secrets). "
                       "Puoi comunque registrare: l'audio verrà salvato senza testo.")

        speaker = st.radio("Chi sta parlando in questo turno?",
                          ["professionista", "paziente"],
                          format_func=lambda s: "🧑‍⚕️ Professionista" if s == "professionista" else "🧒 Paziente",
                          horizontal=True, key=f"diario_speaker_{paz_id}")

        audio_val = st.audio_input("Registra questo turno", key=f"diario_rec_{paz_id}_{len(turni)}")
        if audio_val is not None:
            dati = audio_val.getvalue()
            mime = audio_val.type or "audio/wav"
            with st.spinner("Trascrizione in corso..."):
                testo = trascrivi_audio(dati, mime) if trascrizione_disponibile() else ""
            turni.append({"speaker": speaker, "mime": mime, "dati": dati, "testo": testo})
            st.rerun()

        if turni:
            st.divider()
            st.caption(f"{len(turni)} turno/i registrato/i in questa sessione:")
            for i, t in enumerate(turni):
                etichetta = "🧑‍⚕️ Professionista" if t["speaker"] == "professionista" else "🧒 Paziente"
                st.markdown(f"**{i+1}. {etichetta}**")
                st.audio(t["dati"], format=t["mime"])
                if t["testo"].startswith("⚠️"):
                    st.caption(t["testo"])
                elif t["testo"]:
                    st.write(t["testo"])
                else:
                    st.caption("(nessuna trascrizione)")

            c1, c2, c3 = st.columns([1, 1, 2])
            if c1.button("↩️ Rimuovi ultimo turno", key=f"diario_rec_undo_{paz_id}"):
                turni.pop()
                st.rerun()
            if c2.button("🗑️ Scarta tutto", key=f"diario_rec_clear_{paz_id}"):
                st.session_state[chiave_turni] = []
                st.rerun()
            if c3.button("✅ Salva seduta nel diario", type="primary", key=f"diario_rec_save_{paz_id}"):
                transcript = "\n\n".join(
                    f"[{'Professionista' if t['speaker']=='professionista' else 'Paziente'}] {t['testo']}"
                    for t in turni if t["testo"] and not t["testo"].startswith("⚠️")
                )
                autore = st.session_state.get("utente_nome") or st.session_state.get("username")
                nuovo_id = aggiungi_nota(conn, studio_id, paz_id, "seduta",
                                        transcript or "(seduta registrata senza trascrizione)",
                                        titolo="Seduta registrata", autore=autore)
                for i, t in enumerate(turni):
                    salva_clip_audio(conn, studio_id, nuovo_id, i, t["speaker"], t["mime"],
                                    t["dati"], t["testo"] or None)
                st.session_state[chiave_turni] = []
                st.success("Seduta salvata nel diario.")
                st.rerun()


def render_diario(conn, paz_id=None, paziente=None):
    st.header("🗓️ Diario clinico")
    st.caption("Timeline del percorso del paziente: voci generate automaticamente "
               "dai moduli, note scritte liberamente e registrazioni di seduta.")

    if not paz_id:
        st.info("Seleziona un paziente per vedere o scrivere sul suo diario.")
        return

    try:
        crea_schema(conn)
    except Exception as e:
        st.error(f"Errore inizializzazione tabella diario: {e}")
        return

    studio_id = st.session_state.get("studio_id", 1)

    _render_registratore_seduta(conn, studio_id, paz_id)

    with st.expander("✏️ Aggiungi voce manuale (testo)", expanded=False):
        with st.form("form_nuova_voce_diario", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            tipo = c1.selectbox("Tipo", list(TIPI_VOCE.keys()),
                                format_func=lambda k: TIPI_VOCE[k], index=8)
            titolo = c2.text_input("Titolo (opzionale)")
            testo = st.text_area("Testo", height=120)
            visibile = st.checkbox("Visibile nel referto", value=True)
            invia = st.form_submit_button("Salva voce")
            if invia:
                if not testo.strip():
                    st.warning("Scrivi un testo prima di salvare.")
                else:
                    autore = st.session_state.get("utente_nome") or st.session_state.get("username")
                    nuovo_id = aggiungi_nota(conn, studio_id, paz_id, tipo, testo.strip(),
                                            titolo=titolo.strip() or None, autore=autore)
                    if not visibile:
                        aggiorna_voce(conn, studio_id, nuovo_id, visibile_in_referto=False)
                    st.success("Voce salvata.")
                    st.rerun()

    conteggi = conteggio_per_tipo(conn, studio_id, paz_id)
    if conteggi:
        cols = st.columns(len(conteggi))
        for col, (tipo, n) in zip(cols, sorted(conteggi.items())):
            col.metric(TIPI_VOCE.get(tipo, tipo), n)

    filtro_tipi = st.multiselect("Filtra per tipo", list(TIPI_VOCE.keys()),
                                 format_func=lambda k: TIPI_VOCE[k])
    voci = lista_voci(conn, studio_id, paz_id, tipi=filtro_tipi or None)

    if not voci:
        st.info("Nessuna voce nel diario di questo paziente ancora.")
        return

    st.divider()
    for v in voci:
        badge = {"auto": "🤖 auto", "manuale": "✍️ manuale",
                 "auto_modificato": "🤖✏️ auto modificato"}.get(v["generato_da"], "")
        data_str = v["data_voce"].strftime("%d/%m/%Y %H:%M") if v["data_voce"] else ""
        titolo_riga = v["titolo"] or TIPI_VOCE.get(v["tipo_voce"], v["tipo_voce"])
        with st.expander(f"{data_str} — {titolo_riga}  ·  {badge}"):
            st.caption(f"{TIPI_VOCE.get(v['tipo_voce'], v['tipo_voce'])}"
                      + (f" · {v['autore']}" if v.get('autore') else ""))
            if v["riassunto"]:
                st.markdown(f"**{v['riassunto']}**")
            if v["testo"]:
                st.write(v["testo"])
            clip = lista_clip_audio(conn, studio_id, v["id"])
            if clip:
                st.markdown("**🎙️ Registrazione seduta:**")
                etichette = {"professionista": "🧑‍⚕️ Professionista", "paziente": "🧒 Paziente"}
                for c in clip:
                    st.caption(etichette.get(c["speaker"], c["speaker"]))
                    st.audio(bytes(c["dati"]), format=c["mime"])
            if not v["visibile_in_referto"]:
                st.caption("🚫 non incluso nel referto")

            c1, c2 = st.columns(2)
            if c1.button("Modifica", key=f"diario_edit_{v['id']}"):
                st.session_state[f"diario_editing_{v['id']}"] = True
            if c2.button("🗑️ Elimina", key=f"diario_del_{v['id']}"):
                elimina_voce(conn, studio_id, v["id"])
                st.rerun()

            if st.session_state.get(f"diario_editing_{v['id']}"):
                nuovo_testo = st.text_area("Testo", value=v["testo"] or "",
                                           key=f"diario_txt_{v['id']}")
                nuovo_riass = st.text_input("Riassunto", value=v["riassunto"] or "",
                                            key=f"diario_riass_{v['id']}")
                if st.button("Salva modifica", key=f"diario_save_{v['id']}"):
                    aggiorna_voce(conn, studio_id, v["id"], testo=nuovo_testo,
                                 riassunto=nuovo_riass)
                    st.session_state[f"diario_editing_{v['id']}"] = False
                    st.rerun()
