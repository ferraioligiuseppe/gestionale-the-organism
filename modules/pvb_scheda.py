# -*- coding: utf-8 -*-
"""
modules/pvb_scheda.py

Scheda di registrazione PVB — «Il Primo Vocabolario del Bambino»
(Caselli, Casadio et al.). Uso interno allo studio.

IMPORTANTE — perché questa è una scheda di REGISTRAZIONE e non il test:
il PVB è uno strumento pubblicato e protetto da diritto d'autore. Gli item
(la lista lessicale e quella dei gesti) NON sono riprodotti qui: il test si
somministra con la propria copia autorizzata, e in questa scheda si
registrano i punteggi ottenuti e il percentile letto dalle tabelle normative
del manuale. Così il dato entra nella cartella del paziente, nel Quadro
storico e nelle relazioni, senza redistribuire lo strumento.
"""

import json
import datetime
import streamlit as st

FORME = {
    "gesti_parole": {
        "nome": "Gesti e Parole (8–24 mesi)",
        "campi": [
            ("parole_comprese",  "Parole comprese", 0, 408),
            ("parole_prodotte",  "Parole prodotte", 0, 408),
            ("gesti_azioni",     "Azioni e gesti", 0, 63),
        ],
    },
    "parole_frasi": {
        "nome": "Parole e Frasi (18–36 mesi)",
        "campi": [
            ("parole_prodotte",  "Parole prodotte", 0, 670),
            ("frasi_lunghezza",  "Lunghezza media enunciati (LME)", 0, 12),
            ("frasi_complessita", "Complessità frasale (punti)", 0, 37),
        ],
    },
}


def _assicura_tabella(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pvb_schede (
            id           BIGSERIAL PRIMARY KEY,
            studio_id    BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            paziente_id  BIGINT NOT NULL,
            data_somm    DATE,
            forma        TEXT,
            eta_mesi     INT,
            punteggi     JSONB,
            percentili   JSONB,
            note         TEXT,
            creato_il    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("""CREATE INDEX IF NOT EXISTS ix_pvb_paziente
                   ON pvb_schede (paziente_id, data_somm DESC);""")
    cur.execute("ALTER TABLE pvb_schede ENABLE ROW LEVEL SECURITY;")
    cur.execute("ALTER TABLE pvb_schede FORCE ROW LEVEL SECURITY;")
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies
                           WHERE tablename='pvb_schede' AND policyname='pvb_schede_studio') THEN
                CREATE POLICY pvb_schede_studio ON pvb_schede
                    USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                    WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
            END IF;
        END $$;
    """)
    conn.commit()


def _salva(conn, paz_id, d):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pvb_schede (paziente_id, data_somm, forma, eta_mesi,
                                punteggi, percentili, note)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (paz_id, d["data_somm"], d["forma"], d["eta_mesi"],
          json.dumps(d["punteggi"]), json.dumps(d["percentili"]), d["note"]))
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def _storico(conn, paz_id):
    cur = conn.cursor()
    cur.execute("""SELECT * FROM pvb_schede WHERE paziente_id=%s
                   ORDER BY data_somm DESC, id DESC LIMIT 30""", (paz_id,))
    return cur.fetchall()


def _elimina(conn, rid):
    cur = conn.cursor()
    cur.execute("DELETE FROM pvb_schede WHERE id=%s", (rid,))
    conn.commit()


def _g(r, k, d=None):
    try:
        v = r[k] if hasattr(r, "keys") else None
        return v if v is not None else d
    except Exception:
        return d


def _lettura(perc):
    """Traduce il percentile più basso in una riga di lettura clinica."""
    validi = [p for p in perc.values() if isinstance(p, (int, float)) and p > 0]
    if not validi:
        return None, ""
    minimo = min(validi)
    if minimo <= 5:
        return "grave", ("Prestazione molto al di sotto dell'atteso (≤5° percentile): "
                         "profilo compatibile con un ritardo espressivo significativo. "
                         "Indicata presa in carico e verifica delle basi uditive e oro-motorie.")
    if minimo <= 10:
        return "attenzione", ("Prestazione sotto l'atteso (≤10° percentile): criterio "
                              "classico di «parlatore tardivo». Monitoraggio ravvicinato "
                              "e approfondimento delle basi sensoriali.")
    if minimo <= 25:
        return "lieve", ("Prestazione nella fascia bassa della norma (≤25° percentile): "
                         "da rivalutare a distanza di 3 mesi.")
    return "norma", "Prestazione nella norma per età."


def render_pvb(conn, paz_id, paziente=None):
    st.markdown("#### 📗 PVB — Il Primo Vocabolario del Bambino")
    st.caption(
        "Scheda di **registrazione**: il test si somministra con la propria copia "
        "del PVB (Caselli, Casadio et al.), qui si annotano i punteggi grezzi e i "
        "percentili letti dalle tabelle normative del manuale. Gli item non sono "
        "riprodotti nel gestionale."
    )
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella PVB non disponibile: {e}")
        return

    # ── Storico ───────────────────────────────────────────────────────
    righe = _storico(conn, paz_id)
    if righe:
        st.markdown("##### Somministrazioni precedenti")
        for r in righe:
            rid = _g(r, "id")
            forma = FORME.get(_g(r, "forma", ""), {}).get("nome", _g(r, "forma", "—"))
            data = _g(r, "data_somm")
            pg = _g(r, "punteggi") or {}
            pc = _g(r, "percentili") or {}
            if isinstance(pg, str):
                try: pg = json.loads(pg)
                except Exception: pg = {}
            if isinstance(pc, str):
                try: pc = json.loads(pc)
                except Exception: pc = {}
            liv, testo = _lettura(pc)
            badge = {"grave": "🔴", "attenzione": "🟠", "lieve": "🟡",
                     "norma": "🟢"}.get(liv, "⚪")
            with st.expander(f"{badge} {data} — {forma} · {_g(r,'eta_mesi','?')} mesi"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Punteggi grezzi**")
                    for k, v in (pg or {}).items():
                        st.markdown(f"- {k.replace('_',' ').capitalize()}: **{v}**")
                with c2:
                    st.markdown("**Percentili**")
                    for k, v in (pc or {}).items():
                        st.markdown(f"- {k.replace('_',' ').capitalize()}: **{v}°**")
                if testo:
                    st.info(testo)
                if _g(r, "note"):
                    st.caption(f"Note: {_g(r,'note')}")
                if st.button("🗑️ Elimina", key=f"pvb_del_{rid}"):
                    _elimina(conn, rid)
                    st.rerun()
        st.markdown("---")

    # ── Nuova somministrazione ────────────────────────────────────────
    st.markdown("##### Nuova somministrazione")
    forma_k = st.radio("Forma del PVB",
                       list(FORME.keys()),
                       format_func=lambda k: FORME[k]["nome"],
                       horizontal=True, key="pvb_forma")

    with st.form(f"pvb_form_{paz_id}"):
        c1, c2 = st.columns(2)
        data_s = c1.date_input("Data somministrazione", datetime.date.today())
        eta = c2.number_input("Età del bambino (mesi)", 6, 48, 24, 1)

        st.markdown("**Punteggi grezzi** — dal foglio di spoglio")
        punteggi, percentili = {}, {}
        for chiave, etichetta, minimo, massimo in FORME[forma_k]["campi"]:
            cc1, cc2 = st.columns([2, 1])
            punteggi[chiave] = cc1.number_input(
                etichetta, min_value=float(minimo), max_value=float(massimo),
                value=0.0, step=1.0, key=f"pvb_p_{chiave}")
            percentili[chiave] = cc2.number_input(
                "percentile", min_value=0, max_value=100, value=0, step=1,
                key=f"pvb_pc_{chiave}",
                help="Letto dalle tabelle normative del manuale, per età e sesso. "
                     "Lascia 0 se non calcolato.")

        note = st.text_area("Note cliniche", height=80, key="pvb_note",
                            placeholder="Collaborazione, attendibilità del riferito, "
                                       "osservazioni qualitative…")
        salva = st.form_submit_button("💾 Salva scheda PVB", type="primary",
                                      use_container_width=True)

    if salva:
        try:
            _salva(conn, paz_id, {
                "data_somm": data_s.isoformat(), "forma": forma_k,
                "eta_mesi": int(eta), "punteggi": punteggi,
                "percentili": percentili, "note": note,
            })
            st.success("Scheda PVB salvata nella cartella.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore nel salvataggio: {e}")

    with st.expander("ℹ️ Come si legge il PVB"):
        st.markdown(
            "- **≤10° percentile** nella produzione lessicale a 24 mesi è il criterio "
            "classico di *late talker* (parlatore tardivo).\n"
            "- Uno scarto ampio fra **comprensione** e **produzione** orienta verso un "
            "ritardo espressivo puro; una comprensione anch'essa ridotta è un quadro "
            "più impegnativo e va approfondito.\n"
            "- I **gesti** contano: un bambino con poche parole ma gesti ricchi ha una "
            "prognosi diversa da chi non compensa con il canale gestuale.\n"
            "- Nel metodo PNEV il dato va sempre letto insieme alle basi uditive "
            "(Fisher, elaborazione uditiva) e oro-motorie."
        )
