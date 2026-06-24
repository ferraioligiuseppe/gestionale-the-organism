# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  GROFFMAN — Visual Tracing Test (Sidney Groffman, 1969)              ║
║  Si segue ogni linea (A-E) fino al numero, SOLO con gli occhi.       ║
║  Si cronometra ogni lettera. Numero giusto → punti in base al tempo; ║
║  numero sbagliato → 0. Totale confrontato con le norme per età.      ║
║  Interattivo (mostra tavola + cronometro + calcolo) + cartaceo.      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import streamlit.components.v1 as components

try:
    from .groffman_data import FORMS as _FORMS
except Exception:
    _FORMS = {}

LETTERE = ["A", "B", "C", "D", "E"]
KEY = {"A": 3, "B": 4, "C": 1, "D": 5, "E": 2}  # numero corretto per lettera

# Tavola 2: secondi -> punti
def punti_da_tempo(sec: float) -> int:
    s = float(sec or 0)
    if s <= 0:
        return 0
    if s < 16: return 10
    if s <= 20: return 9
    if s <= 25: return 8
    if s <= 30: return 7
    if s <= 35: return 6
    if s <= 40: return 5
    if s <= 45: return 4
    if s <= 50: return 3
    if s <= 60: return 2
    return 1

# Tavola 1: età -> (media, ds)
NORME = {7: (10, 3.5), 8: (17, 3.0), 9: (22, 2.0), 10: (26, 2.5),
         11: (28, 3.0), 12: (32, 4.0)}

OSSERVAZIONI = [
    "Tentativi di usare il dito", "Movimenti eccessivi della testa",
    "Distanza dal foglio inadeguata", "Insolita postura della testa",
    "Insolita postura del corpo", "Insolita espressione facciale",
    "Insoliti commenti verbali", "Insoliti movimenti del corpo", "Altro",
]


def _eta(data_nascita):
    import datetime as dt
    if not data_nascita:
        return None
    d = data_nascita
    if isinstance(d, str):
        for f in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                d = dt.datetime.strptime(d[:10], f).date(); break
            except Exception:
                continue
        if isinstance(d, str):
            return None
    if isinstance(d, dt.datetime):
        d = d.date()
    o = dt.date.today()
    return o.year - d.year - ((o.month, o.day) < (d.month, d.day))


def render_groffman(conn=None, paz_id=None, paziente=None):
    st.header("👁️ Groffman — Visual Tracing Test")
    st.caption("Segui ogni linea (A→numero) SOLO con gli occhi, niente dito. "
               "Cronometra ogni lettera.")

    eta = None
    if isinstance(paziente, dict):
        eta = _eta(paziente.get("Data_Nascita"))

    tab_int, tab_cart = st.tabs(["✍️ Interattivo", "🖨️ Cartaceo (stampa)"])

    with tab_int:
        forma = st.radio("Tavola", ["A", "B"], horizontal=True, key="grof_forma")
        key_img = "form_a" if forma == "A" else "form_b"
        if _FORMS.get(key_img):
            st.image(_FORMS[key_img], use_container_width=True)

        st.markdown("#### Registrazione (per ogni lettera: numero raggiunto + secondi)")
        tot = 0
        righe = []
        for L in LETTERE:
            c1, c2, c3 = st.columns([1, 2, 2])
            with c1:
                st.markdown(f"**{L}**")
            with c2:
                num = st.selectbox(f"Numero raggiunto ({L})", [0, 1, 2, 3, 4, 5],
                                   key=f"grof_num_{L}",
                                   help="0 = non arrivato / non valutato")
            with c3:
                sec = st.number_input(f"Secondi ({L})", min_value=0.0, step=1.0,
                                      value=0.0, key=f"grof_sec_{L}")
            corretto = (num == KEY[L])
            pti = punti_da_tempo(sec) if corretto else 0
            tot += pti
            righe.append((L, num, KEY[L], sec, corretto, pti))

        st.markdown("#### Osservazioni durante il test")
        oss = {}
        cols = st.columns(3)
        for i, o in enumerate(OSSERVAZIONI):
            with cols[i % 3]:
                oss[o] = st.checkbox(o, key=f"grof_oss_{i}")

        if st.button("✅ Calcola punteggio", key="grof_calc", type="primary"):
            st.markdown(f"## Totale punti: {tot}")
            with st.expander("Dettaglio per lettera"):
                for L, num, atteso, sec, ok, pti in righe:
                    st.markdown(f"{'🟢' if ok else '🔴'} {L}: numero {num} "
                                f"(corretto {atteso}) · {sec:.0f}s → **{pti} punti**")
            if eta:
                e = max(7, min(12, eta))
                media, ds = NORME[e]
                z = (tot - media) / ds if ds else 0
                if z >= -1:
                    st.success(f"Età {eta}: atteso {media}±{ds}. Punteggio {tot} → nella norma.")
                else:
                    st.warning(f"Età {eta}: atteso {media}±{ds}. Punteggio {tot} → sotto la norma.")
            else:
                st.info("Età non disponibile dall'anagrafica: confronta a mano con le norme "
                        "(7:10 · 8:17 · 9:22 · 10:26 · 11:28 · 12:32).")
            st.session_state["grof_tot"] = tot

            if conn is not None and paz_id:
                if st.button("💾 Salva nella cartella", key="grof_save"):
                    if _salva(conn, paz_id, forma, tot, eta, oss):
                        st.success("Risultato Groffman salvato.")
                    else:
                        st.warning("Salvataggio non riuscito.")

    with tab_cart:
        st.caption("Tabella di registrazione da stampare.")
        html = _scheda_html(paziente)
        st.download_button("🖨️ Scarica scheda Groffman (HTML)", data=html,
                           file_name="scheda_Groffman.html", mime="text/html",
                           key="grof_dl")
        components.html(html, height=480, scrolling=True)


def _salva(conn, paz_id, forma, tot, eta, oss):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS groffman_risultati(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT, data TIMESTAMP DEFAULT NOW(),
            forma TEXT, punteggio INT, eta INT, osservazioni TEXT);""")
        conn.commit()
        note = "; ".join(k for k, v in oss.items() if v)
        cur.execute("INSERT INTO groffman_risultati(paziente_id,forma,punteggio,eta,osservazioni)"
                    " VALUES(%s,%s,%s,%s,%s)", (paz_id, forma, tot, eta or 0, note))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _scheda_html(paziente):
    nome = ""
    if isinstance(paziente, dict):
        nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    righe = "".join(f"<tr><td>{L}</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
                    for L in LETTERE)
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Scheda Groffman</title><style>
@page{{size:A4;margin:16mm}} body{{font-family:Georgia,serif;color:#1a1a1a}}
h1{{font-size:19px;margin:0 0 2px}} .sub{{color:#555;font-size:12px;margin-bottom:12px}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}
th,td{{border:1px solid #999;padding:7px 9px;font-size:13px;text-align:center}}
th{{background:#f0f0f0}} td:first-child{{font-weight:bold}}
.small{{font-size:11px;color:#666}} .two{{display:flex;gap:18px}}
</style></head><body>
<h1>Visual Tracing Test — Tabella di Registrazione (Groffman)</h1>
<div class="sub">Studio The Organism · seguire la linea solo con gli occhi</div>
<table><tr><th>Nome</th><th>Età</th><th>Tracciato (A/B)</th><th>Data</th></tr>
<tr><td>{nome or '&nbsp;'}</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr></table>
<div class="two">
<table style="flex:1"><tr><th>Lettera</th><th>Numero raggiunto</th><th>Secondi</th><th>Punti</th></tr>
{righe}<tr><td colspan="3">TOTALE</td><td>&nbsp;</td></tr></table>
<table style="width:230px"><tr><th>Secondi</th><th>Punti</th></tr>
<tr><td>&lt;16</td><td>10</td></tr><tr><td>16-20</td><td>9</td></tr>
<tr><td>21-25</td><td>8</td></tr><tr><td>26-30</td><td>7</td></tr>
<tr><td>31-35</td><td>6</td></tr><tr><td>36-40</td><td>5</td></tr>
<tr><td>41-45</td><td>4</td></tr><tr><td>46-50</td><td>3</td></tr>
<tr><td>51-60</td><td>2</td></tr><tr><td>&gt;60</td><td>1</td></tr></table>
</div>
<div class="small">Risposte corrette: A-3 · B-4 · C-1 · D-5 · E-2 (numero sbagliato = 0 punti).<br>
Norme per età (media): 7=10 · 8=17 · 9=22 · 10=26 · 11=28 · 12=32.</div>
<p class="small">Osservazioni: dito · movimenti testa · distanza · postura testa/corpo ·
espressione · commenti verbali · movimenti corpo · altro.</p>
</body></html>"""
