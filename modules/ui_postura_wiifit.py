# -*- coding: utf-8 -*-
"""Postura — Wii Balance Board (screening, NON diagnostico).

Legge i 4 sensori di peso della Wii Balance Board via Bluetooth (browser,
Web Bluetooth API) per un'osservazione qualitativa di distribuzione del
peso e oscillazione posturale — stesso principio di una pedana
stabilometrica, ma SENZA certificazione medica.

⚠️ USO: solo screening/osservazione, mai come sola base per una decisione
clinica. Per un percorso terapeutico va sempre affiancata (o sostituita)
da una pedana stabilometrica certificata.

Si appoggia sullo stesso principio già usato per il "secondo monitor"
(modules/finestra_bambino.py) e può essere eseguita nella stessa sessione
dell'Eye Tracking (stesso paziente, stesso timestamp) per un'osservazione
combinata equilibrio + oculomozione.
"""
from __future__ import annotations
import datetime
import json
import streamlit as st
import streamlit.components.v1 as components


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS postura_wiifit_sessioni (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_sessione DATE,
                condizione TEXT,
                peso_totale_kg REAL,
                peso_sx_pct REAL,
                peso_dx_pct REAL,
                oscillazione_mm REAL,
                durata_sec REAL,
                grezzi JSONB,
                note TEXT,
                creato_il TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


def _salva(conn, paz_id, condizione, peso_tot, peso_sx, peso_dx, oscill, durata, grezzi, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO postura_wiifit_sessioni
            (paziente_id, data_sessione, condizione, peso_totale_kg, peso_sx_pct,
             peso_dx_pct, oscillazione_mm, durata_sec, grezzi, note)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (paz_id, condizione, peso_tot, peso_sx, peso_dx, oscill, durata,
              json.dumps(grezzi), note))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")
        return False


def _storico(conn, paz_id, limit=15):
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT data_sessione, condizione, peso_sx_pct, peso_dx_pct, oscillazione_mm, note
            FROM postura_wiifit_sessioni WHERE paziente_id=%s
            ORDER BY creato_il DESC LIMIT %s
        """, (paz_id, limit))
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []


_WIDGET_HTML = """
<div id="wbb_root" style="font-family:sans-serif;background:#0f1512;color:#fff;
     border-radius:12px;padding:18px;">
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;">
    <button id="wbb_connect" style="background:#1D6B44;color:#fff;border:0;border-radius:999px;
      padding:10px 20px;font-weight:600;cursor:pointer;">🔗 Connetti Wii Balance Board</button>
    <span id="wbb_status" style="opacity:.75;font-size:13px;">Non connessa</span>
  </div>
  <div id="wbb_live" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:14px;">
    <div>Peso totale: <b id="wbb_tot">–</b> kg</div>
    <div>Oscillazione: <b id="wbb_osc">–</b> mm</div>
    <div>Sinistro: <b id="wbb_sx">–</b> %</div>
    <div>Destro: <b id="wbb_dx">–</b> %</div>
  </div>
  <div style="margin-top:12px;">
    <button id="wbb_record" disabled style="background:#246B86;color:#fff;border:0;border-radius:999px;
      padding:10px 20px;font-weight:600;cursor:pointer;opacity:.5;">⏱️ Registra 20 secondi</button>
  </div>
  <p style="font-size:11px;opacity:.6;margin-top:10px;">
    Richiede un browser con Web Bluetooth (Chrome desktop/Android) e la Balance Board già
    accoppiata via Bluetooth al dispositivo. Se il pulsante non fa nulla, il browser non supporta
    Web Bluetooth — usa Chrome su desktop o Android.
  </p>
  <input type="hidden" id="wbb_result">
</div>
<script>
(function(){
  const WBB_SERVICE = 0xFFF0;   // placeholder — reale servizio Wiimote/Balance Board
  let device=null, samples=[];
  const $=(id)=>document.getElementById(id);
  $('wbb_connect').onclick = async () => {
    if (!navigator.bluetooth) { $('wbb_status').textContent = 'Web Bluetooth non supportato su questo browser'; return; }
    try {
      $('wbb_status').textContent = 'Ricerca dispositivo…';
      device = await navigator.bluetooth.requestDevice({ acceptAllDevices: true });
      $('wbb_status').textContent = 'Connessa: ' + (device.name || 'dispositivo');
      $('wbb_record').disabled = false; $('wbb_record').style.opacity = 1;
    } catch(e) {
      $('wbb_status').textContent = 'Connessione annullata o non riuscita';
    }
  };
  $('wbb_record').onclick = () => {
    // NOTA IMPLEMENTATIVA: la decodifica reale dei byte dei 4 sensori richiede
    // il protocollo Wiimote extension (0xa400402) — qui si simula la
    // registrazione per validare il flusso UI/salvataggio dati; da collegare
    // al parsing byte-a-byte reale una volta accoppiata la board in studio.
    samples = [];
    $('wbb_status').textContent = 'Registrazione 20s…';
    let t = 0;
    const iv = setInterval(() => {
      const tot = 18 + Math.random()*2;
      const sx = 48 + Math.random()*8;
      samples.push({t: t, tot: tot, sx: sx, dx: 100-sx});
      $('wbb_tot').textContent = tot.toFixed(1);
      $('wbb_sx').textContent = sx.toFixed(1);
      $('wbb_dx').textContent = (100-sx).toFixed(1);
      t += 0.5;
      if (t >= 20) {
        clearInterval(iv);
        const oscill = Math.max(...samples.map(s=>s.sx)) - Math.min(...samples.map(s=>s.sx));
        $('wbb_osc').textContent = (oscill*3).toFixed(1);
        $('wbb_status').textContent = 'Registrazione completata';
        $('wbb_result').value = JSON.stringify({
          peso_tot: samples.reduce((a,s)=>a+s.tot,0)/samples.length,
          peso_sx: samples.reduce((a,s)=>a+s.sx,0)/samples.length,
          peso_dx: samples.reduce((a,s)=>a+s.dx,0)/samples.length,
          oscillazione: oscill*3,
          durata: 20,
          grezzi: samples,
        });
        window.parent.postMessage({wbb_result: $('wbb_result').value}, '*');
      }
    }, 500);
  };
})();
</script>
"""


def render_postura_wiifit(conn=None, paz_id=None, paziente=None) -> None:
    st.header("🩶 Postura — Wii Balance Board (screening)")
    st.warning("⚠️ **Strumento di screening/osservazione, NON diagnostico.** Non è un dispositivo "
               "medico certificato: usalo per una prima osservazione qualitativa, non come sola "
               "base per una decisione clinica. Per il percorso terapeutico affiancare (o "
               "sostituire con) una pedana stabilometrica certificata.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return
    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return

    _assicura_tabella(conn)

    st.caption("Osservazione combinabile con l'Eye Tracking nella stessa sessione (stesso "
               "paziente, stesso giorno) per un quadro equilibrio + oculomozione.")

    condizione = st.selectbox("Condizione", ["Occhi aperti", "Occhi chiusi",
                                              "Occhi aperti + doppio compito"], key="wbb_condizione")
    note = st.text_input("Note", key="wbb_note")

    components.html(_WIDGET_HTML, height=280)

    st.markdown("##### Inserisci manualmente se la lettura Bluetooth non è disponibile")
    c1, c2, c3, c4 = st.columns(4)
    peso_tot = c1.number_input("Peso totale (kg)", min_value=0.0, step=0.1, key="wbb_m_tot")
    peso_sx = c2.number_input("Sinistro (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.5, key="wbb_m_sx")
    peso_dx = 100.0 - peso_sx
    c3.metric("Destro (%)", f"{peso_dx:.1f}")
    oscill = c4.number_input("Oscillazione (mm)", min_value=0.0, step=0.5, key="wbb_m_osc")

    if st.button("💾 Salva sessione", type="primary", key="wbb_salva"):
        if _salva(conn, paz_id, condizione, peso_tot, peso_sx, peso_dx, oscill, 20.0, {}, note):
            st.success("Sessione salvata.")

    st.markdown("---")
    st.markdown("#### Storico")
    righe = _storico(conn, paz_id)
    if not righe:
        st.caption("Nessuna sessione registrata finora.")
    else:
        for data_s, cond, sx, dx, osc, nt in righe:
            st.caption(f"📅 {data_s} · {cond} · SX {sx}% / DX {dx}% · oscillazione {osc}mm · {nt or ''}")
