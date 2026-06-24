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

import datetime as _dt
import random as _random
import streamlit as st
import streamlit.components.v1 as components

# ── Tavole DEM (numeri) ───────────────────────────────────────────────
_random.seed(42)
_DEM_GRIGLIA_A = [[str(_random.randint(1, 9)) for _ in range(5)] for _ in range(16)]
_DEM_GRIGLIA_C = [
    ["3", "8", "6", "1", "5", "4", "2", "9", "7", "6"],
    ["1", "5", "9", "2", "8", "3", "7", "4", "6", "5"],
    ["6", "3", "8", "5", "2", "9", "4", "7", "3", "7"],
    ["5", "7", "2", "6", "4", "1", "8", "3", "2", "1"],
    ["8", "4", "1", "3", "9", "7", "2", "5", "8", "9"],
    ["2", "9", "5", "7", "6", "4", "1", "6", "4", "2"],
    ["3", "6", "4", "1", "5", "2", "9", "1", "7", "6"],
    ["1", "8", "7", "2", "3", "6", "5", "4", "8", "3"],
    ["9", "2", "3", "8", "4", "7", "3", "6", "1", "5"],
    ["7", "5", "6", "4", "1", "3", "8", "2", "9", "4"],
    ["4", "1", "9", "6", "7", "5", "2", "7", "3", "8"],
    ["6", "3", "2", "5", "8", "4", "1", "9", "5", "2"],
    ["5", "7", "8", "3", "2", "1", "6", "5", "4", "7"],
]


def _build_dem_html(widget_id, griglia, titolo, layout="horizontal"):
    """Tavola DEM a schermo con cronometro e click-per-errore."""
    righe_html = ""
    for r, riga in enumerate(griglia):
        celle = "".join(
            f'<span class="dem-cell" onclick="markCell(this)">{num}</span>'
            for num in riga)
        righe_html += f'<div class="dem-row">{celle}</div>\n'
    gap_row = "20px" if layout == "horizontal" else "4px"
    vert_grid = ".dem-grid{display:flex;flex-direction:row;gap:20px}" if layout == "vertical" else ""
    vert_row = ".dem-row{flex-direction:column;gap:2px}" if layout == "vertical" else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body {{ font-family:'Courier New',monospace; background:#f6f8fa; margin:0; padding:12px; }}
  h3 {{ font-size:14px; color:#0d1117; margin-bottom:8px; }}
  .timer-bar {{ display:flex; align-items:center; gap:12px; margin-bottom:10px; }}
  #timer_{widget_id} {{ font-size:28px; font-weight:bold; color:#0969da; min-width:80px; }}
  button {{ padding:6px 14px; border:none; border-radius:6px; cursor:pointer; font-size:13px; font-weight:bold; }}
  #btn_start_{widget_id} {{ background:#2ea44f; color:#fff; }}
  #btn_stop_{widget_id} {{ background:#cf222e; color:#fff; }}
  #btn_reset_{widget_id} {{ background:#57606a; color:#fff; }}
  #err_count_{widget_id} {{ font-size:20px; font-weight:bold; color:#9a6700; }}
  .dem-row {{ display:flex; gap:{gap_row}; margin-bottom:{"4px" if layout=="horizontal" else "0"}; }}
  {vert_grid} {vert_row}
  .dem-cell {{ font-size:22px; cursor:pointer; padding:2px 6px; border-radius:4px; user-select:none; min-width:24px; text-align:center; color:#0d1117; }}
  .dem-cell:hover {{ background:#ddf4ff; }}
  .dem-cell.marked {{ background:#ffebe9; color:#cf222e; text-decoration:line-through; font-weight:bold; }}
  .stats {{ margin-top:10px; font-size:13px; color:#444; }}
</style></head><body>
<h3>🔢 {titolo}</h3>
<div class="timer-bar">
  <div id="timer_{widget_id}">0.0s</div>
  <button id="btn_start_{widget_id}" onclick="startTimer()">▶ Avvia</button>
  <button id="btn_stop_{widget_id}" onclick="stopTimer()">⏹ Stop</button>
  <button id="btn_reset_{widget_id}" onclick="resetTimer()">↺ Azzera</button>
  <span>Errori: <span id="err_count_{widget_id}">0</span></span>
</div>
<div class="dem-grid">{righe_html}</div>
<div class="stats" id="stats_{widget_id}"></div>
<script>
let st_{widget_id}=null,iv_{widget_id}=null,el_{widget_id}=0,er_{widget_id}=0,run_{widget_id}=false;
function startTimer(){{ if(run_{widget_id})return; run_{widget_id}=true; st_{widget_id}=Date.now()-el_{widget_id}*1000;
  iv_{widget_id}=setInterval(()=>{{el_{widget_id}=(Date.now()-st_{widget_id})/1000;
  document.getElementById('timer_{widget_id}').textContent=el_{widget_id}.toFixed(1)+'s';}},100); }}
function stopTimer(){{ if(!run_{widget_id})return; clearInterval(iv_{widget_id}); run_{widget_id}=false;
  document.getElementById('stats_{widget_id}').innerHTML='<b>Tempo: '+el_{widget_id}.toFixed(2)+'s</b> · Errori: '+er_{widget_id}+' — copia questi valori qui sotto.'; }}
function resetTimer(){{ clearInterval(iv_{widget_id}); run_{widget_id}=false; el_{widget_id}=0; er_{widget_id}=0;
  document.getElementById('timer_{widget_id}').textContent='0.0s';
  document.getElementById('err_count_{widget_id}').textContent='0';
  document.getElementById('stats_{widget_id}').innerHTML='';
  document.querySelectorAll('.dem-cell.marked').forEach(c=>c.classList.remove('marked')); }}
function markCell(el){{ el.classList.toggle('marked');
  er_{widget_id}+= el.classList.contains('marked')?1:-1; if(er_{widget_id}<0)er_{widget_id}=0;
  document.getElementById('err_count_{widget_id}').textContent=er_{widget_id}; }}
</script></body></html>"""

# ── NORME ITALIANE (Facchin, Maffioletti, Carnevali 2011) ─────────────
# età(anni): (VT_media, VT_sd, AHT_media, AHT_sd, RATIO_media, RATIO_sd,
#             ERR_media, ERR_sd)
NORME = {
    6:  (72.29, 20.99, 108.12, 30.49, 1.53, 0.29, 14.9, 8.3),
    7:  (52.74, 10.17, 75.01, 19.33, 1.43, 0.25, 7.9, 7.6),
    8:  (45.77, 9.68, 59.91, 14.87, 1.31, 0.20, 4.0, 4.6),
    9:  (41.98, 7.89, 52.04, 12.78, 1.24, 0.18, 2.6, 3.8),
    10: (38.13, 6.35, 44.72, 8.08, 1.18, 0.12, 2.0, 2.6),
    11: (35.06, 6.41, 39.49, 8.44, 1.13, 0.12, 1.7, 2.0),
    12: (31.55, 5.74, 35.34, 6.47, 1.12, 0.09, 1.1, 1.8),
    13: (29.71, 4.58, 33.16, 6.00, 1.12, 0.12, 1.2, 1.9),
    14: (29.01, 4.91, 32.33, 5.29, 1.12, 0.07, 0.6, 0.9),
}
ETA_MIN, ETA_MAX = 6, 14

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
    st.caption("Norme italiane per età (Facchin, Maffioletti, Carnevali 2011).")

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
                              help="Presa dall'anagrafica; correggibile. Norme valide 6–14 anni.")
    if eta_auto and not (ETA_MIN <= eta_auto <= ETA_MAX):
        st.warning(f"Età anagrafica {eta_auto} anni fuori dal range normativo (6–14): "
                   "uso il valore selezionato qui sopra.")

    tab_int, tab_cart, tab_norme = st.tabs(
        ["✍️ Interattivo", "🖨️ Cartaceo (stampa)", "📊 Tabella norme"])

    # ── TAB INTERATTIVO ──
    with tab_int:
        with st.expander("🖥️ Somministra a schermo (tavole + cronometro)", expanded=False):
            st.caption("Mostra la tavola al paziente, avvia il cronometro mentre legge, "
                       "clicca i numeri sbagliati per contare gli errori, poi copia "
                       "Tempo ed Errori nei campi qui sotto.")
            sub_v, sub_o = st.tabs(["⬇️ Verticale (A+B)", "➡️ Orizzontale (C)"])
            with sub_v:
                components.html(_build_dem_html("demv", _DEM_GRIGLIA_A,
                                "Tavola verticale (Test A + B)", "vertical"),
                                height=560, scrolling=True)
            with sub_o:
                components.html(_build_dem_html("demo", _DEM_GRIGLIA_C,
                                "Tavola orizzontale (Test C)", "horizontal"),
                                height=560, scrolling=True)

        st.markdown("#### Tempi")
        c1, c2 = st.columns(2)
        with c1:
            vt = st.number_input("Tempo VERTICALE — Test A+B (sec)", min_value=0.0,
                                 step=0.5, value=0.0, key="dem_vt")
        with c2:
            ht = st.number_input("Tempo ORIZZONTALE — Test C (sec)", min_value=0.0,
                                 step=0.5, value=0.0, key="dem_ht")

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
        st.markdown("#### Valori normativi italiani (media ± DS)")
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
        st.caption("Fonte: Facchin A., Maffioletti S., Carnevali T. (2011) — "
                   "validità del DEM nella popolazione italiana.")


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
<div class="sub">Studio The Organism · norme italiane (Facchin et al. 2011)</div>

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
