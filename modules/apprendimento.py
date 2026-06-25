# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  APPRENDIMENTO PNEV — imparare da TUTTI i pazienti (Mattone C, v1)   ║
║                                                                      ║
║  Non è un'AI che "si addestra": è una BASE DI CONOSCENZA che cresce  ║
║  con i tuoi dati. Aggrega gli esiti registrati su tutti i pazienti   ║
║  dello studio e calcola, per ogni intervento, quante volte ha dato   ║
║  miglioramento / stabilità / peggioramento. Poi l'AI usa questo      ║
║  sapere accumulato per suggerire, sul paziente attuale, le strade    ║
║  che storicamente hanno reso di più.                                 ║
║                                                                      ║
║  Privacy: lavora su dati AGGREGATI e anonimi (nessun nome paziente). ║
║  L'isolamento per studio (RLS) garantisce che veda solo i TUOI casi. ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

try:
    from .quadro_storico import _query, carica_paziente
    from .diagnosi_assistita import _riassunto_storico
except Exception:
    def _query(conn, sql, params=()):
        try:
            cur = conn.cursor(); cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return None
    def carica_paziente(conn, paz_id):
        return None
    def _riassunto_storico(conn, paz_id):
        return ""


def _classe_esito(e: str) -> str:
    e = (e or "").lower()
    if "miglior" in e:
        return "migliorato"
    if "peggior" in e:
        return "peggiorato"
    if "ferm" in e or "stabil" in e:
        return "fermo"
    return "non valutabile"


def _aggrega(conn):
    """Per ogni intervento: conteggi per classe d'esito (su tutti i pazienti)."""
    rows = _query(conn, "SELECT intervento, esito FROM esiti_pnev", ())
    if not rows:
        return []
    mappa = {}
    for r in rows:
        interv = (r.get("intervento") or "—").strip()
        cls = _classe_esito(r.get("esito"))
        d = mappa.setdefault(interv, {"migliorato": 0, "fermo": 0,
                                      "peggiorato": 0, "non valutabile": 0, "tot": 0})
        d[cls] += 1
        d["tot"] += 1
    out = []
    for interv, d in mappa.items():
        valutati = d["migliorato"] + d["fermo"] + d["peggiorato"]
        perc = round(100 * d["migliorato"] / valutati) if valutati else 0
        out.append({"intervento": interv, **d, "perc_migl": perc})
    out.sort(key=lambda x: (-x["tot"], -x["perc_migl"]))
    return out


def _testo_conoscenza(agg) -> str:
    righe = ["BASE DI CONOSCENZA ESITI (tutti i pazienti dello studio):"]
    for a in agg:
        righe.append(
            f"- {a['intervento']}: usato {a['tot']} volte; "
            f"migliorato {a['migliorato']}, fermo {a['fermo']}, "
            f"peggiorato {a['peggiorato']} "
            f"(tasso miglioramento {a['perc_migl']}%)")
    return "\n".join(righe)


def render_apprendimento(conn=None, paz_id=None, paziente=None):
    st.header("🧪 Apprendimento PNEV — casi e pattern")
    st.caption("Cosa ha funzionato, su tutti i tuoi pazienti. La base cresce a ogni "
               "esito che registri. Dati aggregati e anonimi.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return

    agg = _aggrega(conn)
    if not agg:
        st.info("Ancora nessun esito registrato. Più follow-up inserisci "
                "(📈 Esiti), più questa base diventa intelligente.")
        return

    # ── Tabella conoscenza (funziona senza AI) ────────────────────────
    st.markdown("#### 📊 Cosa funziona — base di conoscenza")
    tot_casi = sum(a["tot"] for a in agg)
    st.caption(f"{len(agg)} interventi monitorati · {tot_casi} esiti registrati in totale")
    try:
        import pandas as pd
        df = pd.DataFrame([{
            "Intervento": a["intervento"], "Usi": a["tot"],
            "🟢 Migl.": a["migliorato"], "🟡 Fermo": a["fermo"],
            "🔴 Peggio": a["peggiorato"], "% miglioramento": a["perc_migl"],
        } for a in agg])
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        for a in agg:
            st.markdown(f"- **{a['intervento']}** — {a['tot']} usi · "
                        f"🟢 {a['migliorato']} · 🟡 {a['fermo']} · 🔴 {a['peggiorato']} "
                        f"· **{a['perc_migl']}%** migliorati")

    # ── Suggerimento AI sul paziente attivo ───────────────────────────
    st.markdown("---")
    st.markdown("#### 💡 Suggerimento per il paziente in lavorazione")

    if not paz_id:
        paz_id = st.session_state.get("paziente_attivo_id")
    if not paz_id:
        st.caption("Seleziona un paziente (header in alto) per avere un suggerimento "
                   "basato sui casi accumulati.")
        return

    if not isinstance(paziente, dict):
        paziente = carica_paziente(conn, paz_id) or {}
    nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    if nome:
        st.caption(f"Paziente: {nome}")

    try:
        from .ai_estrazione import genera_testo, ai_disponibile
    except Exception:
        st.caption("Motore AI non disponibile.")
        return
    if not ai_disponibile():
        st.caption("AI non configurata: la tabella qui sopra funziona comunque.")
        return

    if st.button("💡 Cosa suggeriscono i casi simili", type="primary",
                 key="appr_btn"):
        storico = _riassunto_storico(conn, paz_id)
        conoscenza = _testo_conoscenza(agg)
        sistema = (
            "Sei il co-pilota clinico dello Studio The Organism (Metodo PNEV). "
            "Hai a disposizione: (1) lo storico del paziente attuale e (2) una base "
            "di conoscenza aggregata sugli ESITI di tutti i pazienti dello studio. "
            "Confronta il quadro del paziente con i pattern della base di conoscenza e "
            "suggerisci quali interventi hanno storicamente reso di più per quadri "
            "simili, e cosa evitare. Cita i numeri della base quando utile. NON "
            "inventare: usa solo i dati forniti. La decisione resta del clinico.")
        richiesta = (
            "Rispondi in due sezioni:\n"
            "🎯 STRADE CONSIGLIATE (con il perché, citando i tassi di miglioramento)\n"
            "⚠️ DA USARE CON CAUTELA (interventi con esiti deboli per quadri simili)\n\n"
            "=== STORICO PAZIENTE ATTUALE ===\n" + (storico or "non disponibile") +
            "\n\n=== " + conoscenza + "\n")
        with st.spinner("Confronto con i casi accumulati…"):
            out = genera_testo(richiesta, sistema=sistema)
        st.markdown(out)
        st.caption("⚠️ Suggerimento statistico-clinico generato dall'AI: "
                   "va sempre validato dal clinico.")
