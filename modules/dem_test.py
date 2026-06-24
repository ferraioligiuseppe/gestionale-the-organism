# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  DEM — Developmental Eye Movement test                               ║
║  Versione corretta con NORME ITALIANE per età (Facchin et al. 2011)  ║
║                                                                      ║
║  • Parte INTERATTIVA: inserisci tempi + errori → calcola AHT, ratio, ║
║    errori totali, confronto con la norma dell'età e TIPOLOGIA.       ║
║  • Parte CARTACEA: scheda PDF stampabile (norme dell'età incluse)    ║
║    per chi somministra/segna su carta e digita dopo.                 ║
║                                                                      ║
║  Metodo DEM:                                                          ║
║    VT  = tempo verticale (Test A + Test B)                           ║
║    HT  = tempo orizzontale (Test C)                                  ║
║    AHT = HT × 80 / (80 − omissioni + addizioni)   (tempo orizz. agg.)║
║    Ratio = AHT / VT                                                  ║
║    Errori totali = omissioni + addizioni + sostituzioni + trasposiz. ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os as _os
import datetime as _dt
import streamlit as st
import streamlit.components.v1 as components

# ── Tavole DEM ufficiali (sequenze numeriche reali) ───────────────────
PRETEST = [3, 7, 1, 9, 2, 6, 5, 4, 8, 2]
TEST_A_L = [3, 7, 5, 9, 8, 2, 5, 7, 4, 6, 1, 4, 7, 6, 3, 7, 9, 3, 9, 2]
TEST_A_R = [4, 5, 2, 1, 7, 5, 3, 7, 4, 8, 7, 4, 6, 5, 2, 9, 2, 3, 6, 4]
TEST_B_L = [6, 3, 2, 9, 1, 7, 4, 6, 5, 2, 5, 3, 7, 4, 8, 4, 5, 2, 1, 7]
TEST_B_R = [7, 9, 3, 9, 2, 1, 4, 7, 6, 3, 2, 5, 7, 4, 6, 3, 7, 5, 9, 8]
# Test C: stesse cifre di A (righe 1-8) e B (righe 9-16), in orizzontale,
# con spaziatura irregolare (saccadi di ampiezza variabile).
TEST_C = [
    [3, 7, 5, 9, 8], [2, 5, 7, 4, 6], [1, 4, 7, 6, 3], [7, 9, 3, 9, 2],
    [4, 5, 2, 1, 7], [5, 3, 7, 4, 8], [7, 4, 6, 5, 2], [9, 2, 3, 6, 4],
    [6, 3, 2, 9, 1], [7, 4, 6, 5, 2], [5, 3, 7, 4, 8], [4, 5, 2, 1, 7],
    [7, 9, 3, 9, 2], [1, 4, 7, 6, 3], [2, 5, 7, 4, 6], [3, 7, 5, 9, 8],
]
# pesi di spaziatura per le 5 posizioni orizzontali (gap variabili)
_C_GAPS = [[2, 5, 4, 3], [1, 4, 5, 2], [3, 2, 4, 5], [4, 5, 1, 3],
           [2, 4, 3, 5], [5, 2, 4, 1], [3, 5, 2, 4], [1, 3, 5, 2],
           [4, 2, 5, 3], [2, 5, 1, 4], [5, 3, 2, 4], [1, 4, 5, 3],
           [3, 2, 4, 5], [4, 5, 2, 1], [2, 3, 5, 4], [5, 1, 4, 2]]


def _timer_html(widget_id):
    return f"""<div class="timer-bar">
  <div id="timer_{widget_id}">0.0s</div>
  <button id="bs_{widget_id}" onclick="startT()">▶ Avvia</button>
  <button id="bx_{widget_id}" onclick="stopT()">⏹ Stop</button>
  <button id="be_{widget_id}" onclick="addE()">❌ Errore</button>
  <button id="br_{widget_id}" onclick="resetT()">↺ Azzera</button>
  <span style="font-size:15px">Errori: <b id="ec_{widget_id}">0</b></span>
</div>
<div class="stats" id="ss_{widget_id}"></div>
<script>
let s_{widget_id}=null,i_{widget_id}=null,e_{widget_id}=0,er_{widget_id}=0,r_{widget_id}=false;
function startT(){{ if(r_{widget_id})return; r_{widget_id}=true; s_{widget_id}=Date.now()-e_{widget_id}*1000;
  i_{widget_id}=setInterval(()=>{{e_{widget_id}=(Date.now()-s_{widget_id})/1000;
  document.getElementById('timer_{widget_id}').textContent=e_{widget_id}.toFixed(1)+'s';}},100); }}
function stopT(){{ if(!r_{widget_id})return; clearInterval(i_{widget_id}); r_{widget_id}=false;
  document.getElementById('ss_{widget_id}').innerHTML='<b>Tempo: '+e_{widget_id}.toFixed(2)+'s</b> · Errori: '+er_{widget_id}+' — copia qui sotto.'; }}
function addE(){{ er_{widget_id}++; document.getElementById('ec_{widget_id}').textContent=er_{widget_id}; }}
function resetT(){{ clearInterval(i_{widget_id}); r_{widget_id}=false; e_{widget_id}=0; er_{widget_id}=0;
  document.getElementById('timer_{widget_id}').textContent='0.0s';
  document.getElementById('ec_{widget_id}').textContent='0';
  document.getElementById('ss_{widget_id}').innerHTML=''; }}
</script>"""


_PLATE_CSS = """<style>
  body { font-family:'Times New Roman',Georgia,serif; background:#fff; margin:0; padding:14px; color:#111; }
  .timer-bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;
    font-family:-apple-system,Segoe UI,Roboto,sans-serif; }
  .timer-bar #timer_v,.timer-bar #timer_o { } 
  [id^=timer_] { font-size:30px; font-weight:bold; color:#0969da; min-width:88px; }
  .timer-bar button { padding:8px 14px; border:none; border-radius:6px; cursor:pointer; font-size:14px; font-weight:bold; color:#fff; }
  [id^=bs_]{background:#2ea44f}[id^=bx_]{background:#cf222e}[id^=be_]{background:#9a6700}[id^=br_]{background:#57606a}
  [id^=ec_]{font-size:20px;color:#9a6700}
  .stats{font-size:13px;color:#444;min-height:18px;margin-bottom:6px;font-family:-apple-system,sans-serif}
  .plate-title{text-align:center;font-weight:bold;font-size:20px;letter-spacing:3px;margin:6px 0 18px}
  .vcols{display:flex;justify-content:space-around;gap:40px}
  .vcol{display:flex;flex-direction:column;align-items:center}
  .vcol .d{font-size:34px;line-height:1.55;font-weight:600}
  .crow{display:flex;align-items:center;margin:10px 0}
  .crow .d{font-size:34px;font-weight:600}
  .pretest{display:flex;justify-content:center;gap:34px}
  .pretest .d{font-size:40px;font-weight:600}
  .present-bar{display:flex;gap:10px;justify-content:flex-end;margin-bottom:8px;
    font-family:-apple-system,Segoe UI,Roboto,sans-serif}
  .present-bar button{padding:7px 13px;border:none;border-radius:6px;cursor:pointer;
    font-size:13px;font-weight:bold;background:#0969da;color:#fff}
  .present-bar button.alt{background:#6e40c9}
</style>"""

_PRESENT_BAR = '''<div class="present-bar">
  <button onclick="goFs()">⛶ Tutto schermo</button>
  <button class="alt" onclick="present()">🖥️ Apri su 2° monitor</button>
</div>'''

_PRESENT_JS = '''<script>
function goFs(){ var el=document.documentElement;
  if(el.requestFullscreen){ el.requestFullscreen().catch(function(){ alert("Schermo intero non consentito qui: usa il 2° monitor."); }); }
}
async function present(){
  var html='<!DOCTYPE html>'+document.documentElement.outerHTML;
  var t=null;
  if('getScreenDetails' in window){ try{ var sd=await window.getScreenDetails();
    t=sd.screens.find(function(s){return !s.isPrimary;}); }catch(e){} }
  var f=t?('left='+t.availLeft+',top='+t.availTop+',width='+t.availWidth+',height='+t.availHeight):'width=1000,height=1100';
  var w=window.open('','dem_present',f);
  if(!w){ alert('Consenti le finestre popup per aprire la scheda a tutto schermo.'); return; }
  w.document.open(); w.document.write(html); w.document.close();
  if(t){ try{ w.moveTo(t.availLeft,t.availTop); w.resizeTo(t.availWidth,t.availHeight); }catch(e){} }
  setTimeout(function(){ try{ w.focus(); var el=w.document.documentElement; if(el.requestFullscreen) el.requestFullscreen(); }catch(e){} }, 400);
}
</script>'''


def _plate_pretest_html():
    ds = "".join(f'<span class="d">{n}</span>' for n in PRETEST)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_PLATE_CSS}</head><body>
{_PRESENT_BAR}
<div class="plate-title">PRETEST</div>
<div class="pretest">{ds}</div>{_PRESENT_JS}</body></html>"""


def _plate_vertical_html(widget_id, titolo, col_l, col_r, etichetta):
    cl = "".join(f'<span class="d">{n}</span>' for n in col_l)
    cr = "".join(f'<span class="d">{n}</span>' for n in col_r)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_PLATE_CSS}</head><body>
{_PRESENT_BAR}
{_timer_html(widget_id)}
<div class="plate-title">{etichetta}</div>
<div class="vcols"><div class="vcol">{cl}</div><div class="vcol">{cr}</div></div>
{_PRESENT_JS}</body></html>"""


def _plate_horizontal_html(widget_id):
    rows = ""
    for r, riga in enumerate(TEST_C):
        gaps = _C_GAPS[r]
        cells = f'<span class="d">{riga[0]}</span>'
        for k in range(1, 5):
            cells += f'<span style="display:inline-block;width:{gaps[k-1]*22}px"></span>'
            cells += f'<span class="d">{riga[k]}</span>'
        rows += f'<div class="crow">{cells}</div>'
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_PLATE_CSS}</head><body>
{_PRESENT_BAR}
{_timer_html(widget_id)}
<div class="plate-title">TEST C — ORIZZONTALE</div>
{rows}{_PRESENT_JS}</body></html>"""

# ── NORME ITALIANE (Facchin, Maffioletti, Carnevali 2011) ─────────────
# età(anni): (VT_media, VT_sd, AHT_media, AHT_sd, RATIO_media, RATIO_sd,
#             ERR_media, ERR_sd)
NORME = {
    6:  (63.11, 16.59, 98.26, 32.61, 1.58, 0.45, 15.22, 11.49),
    7:  (54.83, 9.20, 87.94, 28.18, 1.60, 0.41, 12.50, 12.91),
    8:  (46.76, 7.89, 57.73, 12.32, 1.24, 0.18, 4.61, 6.91),
    9:  (42.33, 8.20, 51.13, 13.30, 1.21, 0.19, 2.17, 4.10),
    10: (40.28, 7.43, 47.64, 10.11, 1.19, 0.17, 1.91, 2.68),
    11: (37.14, 5.42, 42.62, 7.61, 1.15, 0.13, 1.68, 2.34),
    12: (35.14, 5.87, 39.35, 8.11, 1.12, 0.10, 1.11, 1.17),
    13: (33.75, 6.53, 37.56, 7.23, 1.12, 0.12, 1.61, 2.15),
}
ETA_MIN, ETA_MAX = 6, 13

TIPOLOGIE = {
    1: ("Nella norma", "🟢",
        "Oculomotricità e automatismo di denominazione nei limiti."),
    2: ("Disfunzione oculomotoria", "🟠",
        "Tempo orizzontale e ratio elevati: difficoltà nei movimenti "
        "oculari saccadici durante la lettura."),
    3: ("Difficoltà nel riconoscimento/verbalizzazione dei numeri", "🟡",
        "Tempo verticale e orizzontale elevati ma ratio normale: "
        "rallentamento nell'automatismo di denominazione (verbale)."),
    4: ("Compresenza (oculomotoria + verbale)", "🔴",
        "Tempi e ratio elevati: compresenza di disfunzione oculomotoria "
        "e difficoltà di denominazione."),
}


def eta_da_nascita(data_nascita) -> int | None:
    """Età in anni interi a partire da una data (date/datetime/stringa)."""
    if not data_nascita:
        return None
    d = data_nascita
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                d = _dt.datetime.strptime(d[:10], fmt).date()
                break
            except Exception:
                continue
        if isinstance(d, str):
            return None
    if isinstance(d, _dt.datetime):
        d = d.date()
    oggi = _dt.date.today()
    try:
        return oggi.year - d.year - ((oggi.month, oggi.day) < (d.month, d.day))
    except Exception:
        return None


def _norma_eta(eta: int):
    eta = max(ETA_MIN, min(ETA_MAX, int(eta)))
    return NORME[eta]


def _stato(valore, media, sd, soglia=1.0):
    """Ritorna -1 (sotto), 0 (nella norma), +1 (sopra/elevato) via z-score."""
    if sd <= 0:
        return 0
    z = (valore - media) / sd
    if z > soglia:
        return 1
    if z < -soglia:
        return -1
    return 0


def calcola_dem(eta, vt, ht, omissioni, addizioni, sostituzioni, trasposizioni):
    """Calcola AHT, ratio, errori totali, stati e tipologia DEM.

    Ritorna un dict con tutti i valori derivati.
    """
    vt = float(vt or 0)
    ht = float(ht or 0)
    om = int(omissioni or 0)
    ad = int(addizioni or 0)
    so = int(sostituzioni or 0)
    tr = int(trasposizioni or 0)

    denom = 80 - om + ad
    aht = ht * 80.0 / denom if denom > 0 else ht
    ratio = aht / vt if vt > 0 else 0.0
    err_tot = om + ad + so + tr

    vt_m, vt_sd, aht_m, aht_sd, rat_m, rat_sd, err_m, err_sd = _norma_eta(eta)

    st_vt = _stato(vt, vt_m, vt_sd)
    st_aht = _stato(aht, aht_m, aht_sd)
    st_rat = _stato(ratio, rat_m, rat_sd)
    st_err = _stato(err_tot, err_m, err_sd)

    # ── Tipologia DEM (logica italiana) ──
    vt_alto = st_vt > 0
    aht_alto = st_aht > 0
    rat_alto = st_rat > 0
    if not aht_alto and not rat_alto and not vt_alto:
        tipo = 1
    elif rat_alto and not (vt_alto and not aht_alto):
        # ratio elevato → componente oculomotoria
        tipo = 4 if vt_alto else 2
    elif vt_alto and aht_alto and not rat_alto:
        tipo = 3
    else:
        # casi intermedi: se ratio alto → 2, altrimenti 3 se tempi alti
        tipo = 2 if rat_alto else (3 if (vt_alto or aht_alto) else 1)

    return {
        "eta": int(eta),
        "vt": round(vt, 1), "ht": round(ht, 1),
        "aht": round(aht, 1), "ratio": round(ratio, 2),
        "om": om, "ad": ad, "so": so, "tr": tr, "err_tot": err_tot,
        "st_vt": st_vt, "st_aht": st_aht, "st_rat": st_rat, "st_err": st_err,
        "norma": {"vt": (vt_m, vt_sd), "aht": (aht_m, aht_sd),
                  "ratio": (rat_m, rat_sd), "err": (err_m, err_sd)},
        "tipo": tipo,
    }


_BADGE = {-1: "🔵 sotto", 0: "🟢 norma", 1: "🔴 elevato"}


def _riga_confronto(label, valore, media, sd, stato, unita=""):
    col1, col2, col3 = st.columns([2, 1.4, 1.4])
    with col1:
        st.markdown(f"**{label}**")
    with col2:
        st.markdown(f"{valore}{unita}")
    with col3:
        st.markdown(f"norma {media:.1f}±{sd:.1f} · {_BADGE[stato]}")


# ══════════════════════════════════════════════════════════════════════
#  UI PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

def render_dem(conn=None, paz_id=None, paziente=None):
    st.header("🔢 DEM — Developmental Eye Movement")
    st.caption("Norme ufficiali DEM per età (Developmental Eye Movement Test).")

    # ── Età del paziente (automatica, correggibile) ──
    eta_auto = None
    nome_paz = ""
    if paziente:
        nome_paz = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip()
        eta_auto = eta_da_nascita(paziente.get("data_nascita"))
    if eta_auto is None and conn is not None and paz_id:
        try:
            cur = conn.cursor()
            cur.execute("SELECT cognome, nome, data_nascita FROM pazienti WHERE id=%s",
                        (paz_id,))
            r = cur.fetchone()
            if r:
                if isinstance(r, dict):
                    nome_paz = f"{r.get('cognome','')} {r.get('nome','')}".strip()
                    eta_auto = eta_da_nascita(r.get("data_nascita"))
                else:
                    nome_paz = f"{r[0]} {r[1]}".strip()
                    eta_auto = eta_da_nascita(r[2])
        except Exception:
            pass

    c0a, c0b = st.columns([2, 1])
    with c0a:
        if nome_paz:
            st.markdown(f"**Paziente:** {nome_paz}")
    with c0b:
        eta = st.number_input("Età (anni)", min_value=ETA_MIN, max_value=ETA_MAX,
                              value=int(eta_auto) if eta_auto and ETA_MIN <= eta_auto <= ETA_MAX else 8,
                              step=1, key="dem_eta",
                              help="Presa dall'anagrafica; correggibile. Norme valide 6–13 anni.")
    if eta_auto and not (ETA_MIN <= eta_auto <= ETA_MAX):
        st.warning(f"Età anagrafica {eta_auto} anni fuori dal range normativo (6–13): "
                   "uso il valore selezionato qui sopra.")

    tab_int, tab_cart, tab_norme = st.tabs(
        ["✍️ Interattivo", "🖨️ Cartaceo (stampa)", "📊 Tabella norme"])

    # ── TAB INTERATTIVO ──
    with tab_int:
        with st.expander("🎥 PNEV Capture — analisi movimenti (webcam/Tobii)", expanded=False):
            st.caption("Registra in background occhi (sguardo, saccadi) e volto/bocca "
                       "durante il test. Rileva il Tobii se presente, altrimenti webcam. "
                       "A fine prova scarichi dati e video per la ricerca.")
            attiva_cap = st.checkbox("Attiva analisi movimenti", key="dem_cap_on")
            if attiva_cap:
                try:
                    from .pnev_capture import render_capture
                    render_capture("DEM", paziente_nome=nome_paz, height=640)
                except Exception as _e:
                    st.warning(f"Cattura non disponibile: {_e}")

        with st.expander("🖥️ Somministra a schermo (tavole + cronometro)", expanded=True):
            st.caption("Le schede si presentano una alla volta. Sequenza: "
                       "**Pretest → Test A → Test B → Test C**. Per ogni scheda avvia "
                       "il cronometro mentre il paziente legge ad alta voce, premi "
                       "**❌ Errore** ad ogni errore, poi copia i tempi qui sotto.")
            sub_p, sub_a, sub_b, sub_c = st.tabs(
                ["① Pretest", "② Test A", "③ Test B", "④ Test C"])
            with sub_p:
                components.html(_plate_pretest_html(), height=180)
                st.caption("Prova di riscaldamento: non si cronometra.")
            with sub_a:
                components.html(_plate_vertical_html("a", "A", TEST_A_L, TEST_A_R,
                                "TEST A — VERTICALE"), height=900, scrolling=True)
            with sub_b:
                components.html(_plate_vertical_html("b", "B", TEST_B_L, TEST_B_R,
                                "TEST B — VERTICALE"), height=900, scrolling=True)
            with sub_c:
                components.html(_plate_horizontal_html("c"), height=900, scrolling=True)

        st.markdown("#### Tempi")
        ct1, ct2, ct3 = st.columns(3)
        with ct1:
            t_a = st.number_input("Tempo Test A (sec)", min_value=0.0, step=0.5,
                                  value=0.0, key="dem_ta")
        with ct2:
            t_b = st.number_input("Tempo Test B (sec)", min_value=0.0, step=0.5,
                                  value=0.0, key="dem_tb")
        with ct3:
            ht = st.number_input("Tempo ORIZZONTALE — Test C (sec)", min_value=0.0,
                                 step=0.5, value=0.0, key="dem_ht")
        vt = t_a + t_b
        st.caption(f"Tempo VERTICALE (A+B) = **{vt:.1f}s**")

        st.markdown("#### Errori (Test C orizzontale)")
        c3, c4, c5, c6 = st.columns(4)
        with c3:
            om = st.number_input("Omissioni", min_value=0, step=1, value=0, key="dem_om")
        with c4:
            ad = st.number_input("Addizioni", min_value=0, step=1, value=0, key="dem_ad")
        with c5:
            so = st.number_input("Sostituzioni", min_value=0, step=1, value=0, key="dem_so")
        with c6:
            tr = st.number_input("Trasposizioni", min_value=0, step=1, value=0, key="dem_tr")

        if vt > 0 and ht > 0:
            r = calcola_dem(eta, vt, ht, om, ad, so, tr)
            st.markdown("---")
            nome_t, ic, descr = TIPOLOGIE[r["tipo"]]
            st.markdown(f"## {ic} Tipo {r['tipo']} — {nome_t}")
            st.caption(descr)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tempo verticale (VT)", f"{r['vt']}s")
            m2.metric("Tempo orizz. aggiustato (AHT)", f"{r['aht']}s")
            m3.metric("Ratio (AHT/VT)", f"{r['ratio']}")
            m4.metric("Errori totali", f"{r['err_tot']}")

            st.markdown("##### Confronto con la norma dell'età")
            nm = r["norma"]
            _riga_confronto("Tempo verticale (VT)", r["vt"], *nm["vt"], r["st_vt"], "s")
            _riga_confronto("Tempo orizz. agg. (AHT)", r["aht"], *nm["aht"], r["st_aht"], "s")
            _riga_confronto("Ratio (AHT/VT)", r["ratio"], *nm["ratio"], r["st_rat"])
            _riga_confronto("Errori totali", r["err_tot"], *nm["err"], r["st_err"])

            st.caption(f"AHT = HT × 80 / (80 − omissioni + addizioni) = "
                       f"{ht:.1f} × 80 / {80 - om + ad}")

            if conn is not None and paz_id:
                if st.button("💾 Salva risultato DEM nella cartella", key="dem_salva"):
                    ok = _salva_dem(conn, paz_id, r)
                    if ok:
                        st.success("Risultato DEM salvato.")
                    else:
                        st.warning("Salvataggio non riuscito (controlla la tabella).")
        else:
            st.info("Inserisci almeno il **tempo verticale** e il **tempo orizzontale** "
                    "per ottenere tipologia e confronto con la norma.")

    # ── TAB CARTACEO ──
    with tab_cart:
        st.markdown("#### Scheda cartacea")
        st.caption("Genera una scheda da stampare: il clinico segna tempi ed errori "
                   "a mano durante la somministrazione, poi li digita nel tab Interattivo.")
        html = _scheda_cartacea_html(nome_paz, eta)
        st.download_button("🖨️ Scarica scheda DEM (HTML da stampare)",
                           data=html, file_name=f"scheda_DEM_{(nome_paz or 'paziente').replace(' ','_')}.html",
                           mime="text/html", key="dem_dl_cart")
        with st.expander("Anteprima scheda"):
            components.html(html, height=560, scrolling=True)

    # ── TAB NORME ──
    with tab_norme:
        st.markdown("#### Valori normativi DEM (media ± DS)")
        import pandas as pd
        righe = []
        for e in range(ETA_MIN, ETA_MAX + 1):
            vt_m, vt_sd, aht_m, aht_sd, rat_m, rat_sd, err_m, err_sd = NORME[e]
            righe.append({
                "Età": f"{e} anni",
                "VT (s)": f"{vt_m:.1f} ± {vt_sd:.1f}",
                "AHT (s)": f"{aht_m:.1f} ± {aht_sd:.1f}",
                "Ratio": f"{rat_m:.2f} ± {rat_sd:.2f}",
                "Errori": f"{err_m:.1f} ± {err_sd:.1f}",
            })
        st.dataframe(pd.DataFrame(righe), hide_index=True, use_container_width=True)
        st.caption("Fonte: tabella normativa ufficiale DEM "
                   "(Developmental Eye Movement Test).")


def _salva_dem(conn, paz_id, r) -> bool:
    """Salva il risultato DEM. Crea la tabella se non esiste (idempotente)."""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dem_risultati (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data TIMESTAMP DEFAULT NOW(),
                eta INT, vt REAL, ht REAL, aht REAL, ratio REAL,
                omissioni INT, addizioni INT, sostituzioni INT, trasposizioni INT,
                errori_totali INT, tipo INT
            );
        """)
        conn.commit()
        cur.execute("""
            INSERT INTO dem_risultati
            (paziente_id, eta, vt, ht, aht, ratio, omissioni, addizioni,
             sostituzioni, trasposizioni, errori_totali, tipo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (paz_id, r["eta"], r["vt"], r["ht"], r["aht"], r["ratio"],
              r["om"], r["ad"], r["so"], r["tr"], r["err_tot"], r["tipo"]))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _scheda_cartacea_html(nome_paz, eta) -> str:
    vt_m, vt_sd, aht_m, aht_sd, rat_m, rat_sd, err_m, err_sd = _norma_eta(eta)
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Scheda DEM</title>
<style>
@page {{ size: A4; margin: 16mm; }}
body {{ font-family: Georgia, 'Times New Roman', serif; color:#1a1a1a; }}
h1 {{ font-size:20px; margin:0 0 2px; }}
.sub {{ color:#555; font-size:12px; margin-bottom:14px; }}
table {{ border-collapse:collapse; width:100%; margin:10px 0; }}
th,td {{ border:1px solid #999; padding:7px 9px; font-size:13px; text-align:left; }}
th {{ background:#f0f0f0; }}
.box {{ border:1px solid #999; padding:10px 12px; margin:10px 0; }}
.fill {{ display:inline-block; border-bottom:1px solid #333; min-width:90px; }}
.small {{ font-size:11px; color:#666; }}
</style></head><body>
<h1>Scheda DEM — Developmental Eye Movement</h1>
<div class="sub">Studio The Organism · norme ufficiali DEM</div>

<table>
<tr><th style="width:50%">Paziente</th><th>Età</th><th>Data</th></tr>
<tr><td>{nome_paz or '&nbsp;'}</td><td>{eta} anni</td><td>&nbsp;</td></tr>
</table>

<div class="box">
<b>Tempi</b><br><br>
Tempo VERTICALE (Test A + B): <span class="fill">&nbsp;</span> sec<br><br>
Tempo ORIZZONTALE (Test C): <span class="fill">&nbsp;</span> sec
</div>

<div class="box">
<b>Errori (Test C)</b><br><br>
Omissioni: <span class="fill">&nbsp;</span>&nbsp;&nbsp;
Addizioni: <span class="fill">&nbsp;</span>&nbsp;&nbsp;
Sostituzioni: <span class="fill">&nbsp;</span>&nbsp;&nbsp;
Trasposizioni: <span class="fill">&nbsp;</span>
</div>

<table>
<tr><th>Parametro</th><th>Norma per {eta} anni (media ± DS)</th><th>Valore rilevato</th></tr>
<tr><td>Tempo verticale (VT)</td><td>{vt_m:.1f} ± {vt_sd:.1f} s</td><td>&nbsp;</td></tr>
<tr><td>Tempo orizzontale aggiustato (AHT)</td><td>{aht_m:.1f} ± {aht_sd:.1f} s</td><td>&nbsp;</td></tr>
<tr><td>Ratio (AHT / VT)</td><td>{rat_m:.2f} ± {rat_sd:.2f}</td><td>&nbsp;</td></tr>
<tr><td>Errori totali</td><td>{err_m:.1f} ± {err_sd:.1f}</td><td>&nbsp;</td></tr>
</table>

<div class="small">
AHT = Tempo orizzontale × 80 / (80 − omissioni + addizioni). &nbsp;
Ratio elevato → componente oculomotoria; tempi elevati con ratio normale → componente verbale (denominazione).
</div>

<p style="margin-top:24px">Tipologia: &nbsp; □ 1 Norma &nbsp; □ 2 Disfunzione oculomotoria &nbsp;
□ 3 Difficoltà verbale numeri &nbsp; □ 4 Compresenza</p>
<p>Note: ______________________________________________________________</p>
</body></html>"""
