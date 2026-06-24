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
import base64 as _b64
import streamlit.components.v1 as components

try:
    from .getman_data import IMAGES as _IMG
except Exception:
    _IMG = {}
try:
    from .getman_data import FIGURE as _FIG
except Exception:
    _FIG = {}

# Domande Getman (nell'ordine della somministrazione)
DOMANDE = [
    "Come ti apparirebbe questa figura se tu fossi seduto al mio posto?",
    "Come vedresti la figura se fosse capovolta?",
    "Come la vedresti se la osservassi da dietro lo schermo e fosse capovolta?",
]
# Forma -> chiave immagine FIGURE
_FIG_KEY = {"Triangolo": "fig_triangolo", "Semisfera": "fig_semisfera",
            "T": "fig_t", "L": "fig_l"}


def _presentazione_html():
    """Sequenza guidata: figura grande + domanda + timer 10s, avanza da sola."""
    import json as _json
    slides = []
    for forma in ["Triangolo", "Semisfera", "T", "L"]:
        img = _FIG.get(_FIG_KEY[forma])
        uri = ("data:image/png;base64," + _b64.b64encode(img).decode()) if img else ""
        for qi, dom in enumerate(DOMANDE, 1):
            slides.append({"img": uri, "label": f"{forma} — Domanda {qi}", "q": dom})
    data = _json.dumps(slides)
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#fff;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#111}
  .top{display:flex;align-items:center;gap:14px;padding:8px 12px;background:#f4f6f8;flex-wrap:wrap}
  button{padding:8px 16px;border:none;border-radius:7px;cursor:pointer;font-size:14px;font-weight:bold;color:#fff}
  #prev{background:#57606a}#next{background:#0969da}#auto{background:#6e40c9}#fs{background:#1f8a5b}
  #tmr{font-size:26px;font-weight:bold;color:#cf222e;min-width:54px}
  .lab{font-weight:bold;font-size:15px}
  .stage{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:440px;padding:16px}
  .stage img{max-width:60%;max-height:380px}
  .q{font-size:20px;font-weight:bold;text-align:center;margin-top:18px;max-width:760px}
  .prog{font-size:12px;color:#8b949e}
</style></head><body>
<div class="top">
  <button id="prev">◀</button>
  <button id="next">▶ Avanti</button>
  <button id="auto">⏱ Auto 10s</button>
  <button id="fs">⛶ Schermo intero</button>
  <span id="tmr">10</span>
  <span class="lab" id="lab"></span>
  <span class="prog" id="prog"></span>
</div>
<div class="stage"><img id="fig" src=""><div class="q" id="q"></div></div>
<script>
const S=""" + data + """;
let i=0,auto=false,t=10,iv=null;
function render(){const s=S[i];document.getElementById('fig').src=s.img;
 document.getElementById('q').textContent=s.q;document.getElementById('lab').textContent=s.label;
 document.getElementById('prog').textContent=(i+1)+' / '+S.length;}
function go(d){i=Math.max(0,Math.min(S.length-1,i+d));t=10;document.getElementById('tmr').textContent=t;render();}
document.getElementById('next').onclick=()=>go(1);
document.getElementById('prev').onclick=()=>go(-1);
document.getElementById('fs').onclick=()=>{const e=document.documentElement;if(e.requestFullscreen)e.requestFullscreen();};
document.getElementById('auto').onclick=function(){auto=!auto;this.style.opacity=auto?1:.5;
 if(iv)clearInterval(iv);
 if(auto){iv=setInterval(()=>{t--;document.getElementById('tmr').textContent=t;if(t<=0){if(i<S.length-1)go(1);else{auto=false;clearInterval(iv);}}},1000);}};
render();
</script></body></html>"""

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
        with st.expander("▶️ Presentazione guidata (mostra al paziente)", expanded=True):
            st.caption("Figura a schermo + domanda + timer 10s. Usa ⏱ Auto per "
                       "l'avanzamento automatico e ⛶ per lo schermo intero. "
                       "Da somministrare per vicino (40 cm).")
            components.html(_presentazione_html(), height=560, scrolling=False)

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
