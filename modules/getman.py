# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  GETMAN — Test di Manipolazione Visiva (G.N. Getman)                 ║
║  Fattore: manipolazione visiva / rotazione mentale.                  ║
║                                                                      ║
║  4 forme-modello (Triangolo, Semisfera, T, L). Per ciascuna 3        ║
║  domande: come appare dal punto di vista dell'esaminatore (POV),     ║
║  capovolta (Upside-down), entrambe (Both). Il bambino indica il      ║
║  numero (1-12) sul foglio risposte. 1 punto per risposta esatta      ║
║  (max 12). Il totale → equivalente di classe (norme Getman).         ║
║                                                                      ║
║  Interattivo (mostra modelli + foglio, registra e calcola) +         ║
║  cartaceo (scheda stampabile).                                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import streamlit.components.v1 as components

try:
    from .getman_data import IMAGES as _IMG
except Exception:
    _IMG = {}

# Chiave risposte: forma -> {pov, upside, both}
KEY = {
    "Triangolo": {"pov": 2, "upside": 8, "both": 11},
    "Semisfera": {"pov": 1, "upside": 6, "both": 11},
    "T":         {"pov": 4, "upside": 8, "both": 10},
    "L":         {"pov": 2, "upside": 7, "both": 9},
}
FORME = ["Triangolo", "Semisfera", "T", "L"]
COLONNE = [("pov", "Punto di vista"), ("upside", "Capovolta"), ("both", "Entrambe")]

# Norme: punteggio totale -> classe equivalente
# CLASSE  K  1  2  3  4  5  6  7  8
# NORME   4  5  6  7  8  9 10 11 12
_NORME = {4: "Asilo (K)", 5: "1ª elem.", 6: "2ª elem.", 7: "3ª elem.",
          8: "4ª elem.", 9: "5ª elem.", 10: "6ª (1ª media)",
          11: "7ª (2ª media)", 12: "8ª (3ª media)"}
CLASSI = ["Asilo (K)", "1ª elementare", "2ª elementare", "3ª elementare",
          "4ª elementare", "5ª elementare", "1ª media", "2ª media", "3ª media"]
_CLASSE_ATTESA = {  # classe reale -> punteggio atteso
    "Asilo (K)": 4, "1ª elementare": 5, "2ª elementare": 6, "3ª elementare": 7,
    "4ª elementare": 8, "5ª elementare": 9, "1ª media": 10, "2ª media": 11,
    "3ª media": 12}


def _equivalente(tot: int) -> str:
    if tot <= 4:
        return _NORME[4]
    if tot >= 12:
        return _NORME[12]
    return _NORME.get(tot, "—")


def render_getman(conn=None, paz_id=None, paziente=None):
    st.header("👁️ Getman — Test di Manipolazione Visiva")
    st.caption("Rotazione mentale delle forme. 1 punto per risposta esatta (max 12) "
               "→ equivalente di classe.")

    tab_int, tab_cart = st.tabs(["✍️ Interattivo", "🖨️ Cartaceo (stampa)"])

    with tab_int:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Carte-modello** (mostra al bambino)")
            if _IMG.get("modelli"):
                st.image(_IMG["modelli"], use_container_width=True)
        with c2:
            st.markdown("**Foglio risposte** (il bambino indica il numero)")
            if _IMG.get("risposte"):
                st.image(_IMG["risposte"], use_container_width=True)

        st.markdown("---")
        st.markdown("#### Risposte del bambino")
        st.caption("Per ogni forma e domanda, inserisci il **numero (1-12)** indicato dal bambino.")

        risposte = {}
        for forma in FORME:
            st.markdown(f"**{forma}**")
            cols = st.columns(3)
            risposte[forma] = {}
            for i, (chiave, etich) in enumerate(COLONNE):
                with cols[i]:
                    risposte[forma][chiave] = st.selectbox(
                        etich, options=list(range(1, 13)),
                        key=f"getman_{forma}_{chiave}")

        if st.button("✅ Calcola punteggio", key="getman_calc", type="primary"):
            tot = 0
            dettaglio = []
            for forma in FORME:
                for chiave, etich in COLONNE:
                    ok = risposte[forma][chiave] == KEY[forma][chiave]
                    tot += 1 if ok else 0
                    dettaglio.append((forma, etich, risposte[forma][chiave],
                                      KEY[forma][chiave], ok))
            st.markdown(f"## Punteggio: {tot} / 12")
            st.markdown(f"**Livello equivalente:** {_equivalente(tot)}")

            with st.expander("Dettaglio risposte"):
                for forma, etich, dato, atteso, ok in dettaglio:
                    st.markdown(f"{'🟢' if ok else '🔴'} {forma} · {etich}: "
                                f"indicato **{dato}** (corretto {atteso})")

            st.session_state["getman_tot"] = tot

        # confronto con classe reale
        if "getman_tot" in st.session_state:
            st.markdown("---")
            classe = st.selectbox("Classe frequentata dal bambino (per confronto)",
                                  CLASSI, key="getman_classe")
            atteso = _CLASSE_ATTESA.get(classe, 0)
            tot = st.session_state["getman_tot"]
            if tot >= atteso:
                st.success(f"Punteggio {tot} ≥ atteso per {classe} ({atteso}): nella norma.")
            else:
                st.warning(f"Punteggio {tot} < atteso per {classe} ({atteso}): "
                           "sotto la norma di classe.")

            if conn is not None and paz_id and st.button("💾 Salva nella cartella", key="getman_save"):
                if _salva(conn, paz_id, tot, classe, atteso):
                    st.success("Risultato Getman salvato.")
                else:
                    st.warning("Salvataggio non riuscito.")

    with tab_cart:
        st.markdown("#### Scheda cartacea")
        st.caption("Stampa la scheda di registrazione: il clinico segna i numeri indicati, "
                   "poi li digita nel tab Interattivo.")
        html = _scheda_html(paziente)
        st.download_button("🖨️ Scarica scheda Getman (HTML da stampare)",
                           data=html, file_name="scheda_Getman.html",
                           mime="text/html", key="getman_dl")
        components.html(html, height=480, scrolling=True)


def _salva(conn, paz_id, tot, classe, atteso) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS getman_risultati (
                id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
                data TIMESTAMP DEFAULT NOW(),
                punteggio INT, classe TEXT, atteso INT
            );""")
        conn.commit()
        cur.execute("INSERT INTO getman_risultati (paziente_id, punteggio, classe, atteso) "
                    "VALUES (%s,%s,%s,%s)", (paz_id, tot, classe, atteso))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _scheda_html(paziente) -> str:
    nome = ""
    if isinstance(paziente, dict):
        nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    righe = ""
    for forma in FORME:
        righe += (f"<tr><td>{forma}</td><td>&nbsp;</td><td>&nbsp;</td>"
                  f"<td>&nbsp;</td><td>&nbsp;</td></tr>")
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Scheda Getman</title><style>
@page{{size:A4;margin:16mm}}
body{{font-family:Georgia,'Times New Roman',serif;color:#1a1a1a}}
h1{{font-size:20px;margin:0 0 2px}} .sub{{color:#555;font-size:12px;margin-bottom:14px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}
th,td{{border:1px solid #999;padding:8px 10px;font-size:13px;text-align:center}}
th{{background:#f0f0f0}} td:first-child{{text-align:left;font-weight:bold}}
.small{{font-size:11px;color:#666}}
</style></head><body>
<h1>Scheda — Test di Manipolazione Visiva di Getman</h1>
<div class="sub">Studio The Organism · 1 punto per risposta esatta (max 12)</div>
<table><tr><th style="width:40%">Paziente</th><th>Classe</th><th>Data</th></tr>
<tr><td>{nome or '&nbsp;'}</td><td>&nbsp;</td><td>&nbsp;</td></tr></table>
<table>
<tr><th style="width:34%">Forma</th><th>Punto di vista</th><th>Capovolta</th>
<th>Entrambe</th><th>Punti</th></tr>
{righe}
<tr><td>TOTALE</td><td colspan="3">&nbsp;</td><td>&nbsp;</td></tr>
</table>
<div class="small">Chiave (uso interno): Triangolo 2/8/11 · Semisfera 1/6/11 · T 4/8/10 · L 2/7/9.<br>
Norme classe → punteggio: K=4 · 1ª=5 · 2ª=6 · 3ª=7 · 4ª=8 · 5ª=9 · 1ªmedia=10 · 2ªmedia=11 · 3ªmedia=12.</div>
</body></html>"""
