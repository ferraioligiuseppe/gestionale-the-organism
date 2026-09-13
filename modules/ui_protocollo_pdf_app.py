# -*- coding: utf-8 -*-
"""Protocollo di valutazione — versione app HTML (import dal file preparato
con un altro assistente). Impaginazione A4 fedele al PDF, calcolatori con
indici automatici (PCC, %SS, ecc.), export/import JSON, stampa diretta.

Limiti da sapere:
- Il salvataggio "Salva"/"Riapri" della app usa il localStorage del BROWSER,
  non il database dei pazienti: è legato al dispositivo/browser usato in
  quel momento, non al paziente nel gestionale. Per conservarlo nel
  fascicolo del paziente, usa "Esporta" (scarica un file .json) e poi carica
  quel file in un secondo momento con "Importa" — anche da un altro
  dispositivo.
- Il bottone "Bozza di sintesi assistita" chiama l'API Anthropic
  DIRETTAMENTE dal browser con una chiave API incollata dall'utente: la
  chiave resta solo nella sessione del browser (si cancella chiudendo la
  scheda) e non passa dal gestionale. Se preferite non inserire chiavi API
  personali qui, usate invece "Genera relazione" nel modulo Screening o nel
  Protocollo di valutazione (tabelle), che usa l'AI già configurata nel
  gestionale.
"""
from __future__ import annotations
import os
import datetime
import streamlit as st
import streamlit.components.v1 as components

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "static_protocollo",
                          "PNEV_protocollo_app_MASTER.html")


def render_protocollo_pdf_app(conn=None, paz_id=None, paziente=None) -> None:
    st.header("📋 Protocollo di valutazione — app stampabile")
    st.caption("Versione a impaginazione A4 fedele al documento, con calcolatori automatici "
               "(PCC, %SS, indici) e stampa diretta.")
    st.warning("⚠️ Salvataggio: usa **Esporta** per scaricare i dati come file, e **Importa** per "
               "riaprirli — così restano legati al paziente indipendentemente dal browser usato. "
               "\"Salva\"/\"Riapri\" nella barra della app usano solo la memoria di questo browser.")

    _pdf_path = os.path.join(os.path.dirname(__file__), "..", "static_protocollo",
                              "Protocollo_valutazione_TheOrganism.pdf")
    try:
        with open(_pdf_path, "rb") as f:
            st.download_button("📄 Scarica il protocollo in PDF (bianco, da compilare a mano)",
                                data=f.read(), file_name="Protocollo_valutazione_TheOrganism.pdf",
                                mime="application/pdf")
    except Exception:
        pass

    try:
        with open(_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        st.error(f"File del protocollo non trovato: {e}")
        return

    # Selettore paziente dall'anagrafica del gestionale: precompila Cognome/Nome
    # e Data di nascita nell'HTML statico (che di per sé non ha accesso al DB).
    nome_precompilato = data_nascita_precompilata = ""
    if conn is not None:
        with st.expander("➕ Nuovo paziente (non ancora in anagrafica)"):
            cn1, cn2 = st.columns(2)
            nuovo_cognome = cn1.text_input("Cognome", key="pv_html_nuovo_cognome")
            nuovo_nome = cn2.text_input("Nome", key="pv_html_nuovo_nome")
            nuova_dn = st.date_input("Data di nascita", key="pv_html_nuova_dn",
                                      value=None, min_value=datetime.date(1930, 1, 1))
            if st.button("Crea e usa questo paziente", key="pv_html_crea_paziente"):
                if not nuovo_cognome or not nuovo_nome:
                    st.warning("Cognome e nome sono obbligatori.")
                else:
                    try:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO pazienti (cognome, nome, data_nascita) "
                                    "VALUES (%s, %s, %s) RETURNING id",
                                    (nuovo_cognome.strip(), nuovo_nome.strip(), nuova_dn))
                        nuovo_id = cur.fetchone()[0]
                        conn.commit()
                        st.session_state["_paziente_attivo_id"] = nuovo_id
                        st.success(f"Paziente creato (#{nuovo_id}) e impostato come attivo.")
                        st.rerun()
                    except Exception as e:
                        try: conn.rollback()
                        except Exception: pass
                        st.error(f"Errore creazione: {e}")
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti "
                        "ORDER BY cognome, nome LIMIT 3000")
            righe = cur.fetchall() or []
        except Exception as e:
            righe = []
            try: conn.rollback()
            except Exception: pass
            st.error(f"Impossibile leggere l'anagrafica: {e}")
        if righe:
            def _g(r, i, k):
                return r.get(k) if hasattr(r, "get") else r[i]
            opzioni = ["— nessuno (compilo a mano) —"] + [
                f"{_g(r,1,'cognome') or ''} {_g(r,2,'nome') or ''} — #{_g(r,0,'id')}" for r in righe
            ]
            scelta = st.selectbox("👤 Precompila da anagrafica", opzioni, key="pv_html_pick_paziente")
            if scelta != opzioni[0]:
                idx_sel = opzioni.index(scelta) - 1
                r = righe[idx_sel]
                cognome_sel = _g(r, 1, "cognome") or ""
                nome_sel = _g(r, 2, "nome") or ""
                dn_sel = _g(r, 3, "data_nascita")
                nome_precompilato = f"{cognome_sel} {nome_sel}".strip()
                data_nascita_precompilata = dn_sel.strftime("%d/%m/%Y") if hasattr(dn_sel, "strftime") else (str(dn_sel) if dn_sel else "")

    _precompila_js = ""
    if nome_precompilato:
        _safe_nome = nome_precompilato.replace("\\", "").replace("`", "'")
        _safe_dn = (data_nascita_precompilata or "").replace("\\", "").replace("`", "'")
        _precompila_js = f"""
<script>
(function(){{
  function fill(){{
    var f1 = document.querySelector('[data-k="f1"]');
    var f2 = document.querySelector('[data-k="f2"]');
    if (f1) {{ f1.value = `{_safe_nome}`;
      f1.dispatchEvent(new Event('input', {{bubbles:true}}));
      f1.dispatchEvent(new Event('change', {{bubbles:true}}));
      f1.dispatchEvent(new Event('blur', {{bubbles:true}})); }}
    if (f2) {{ f2.value = `{_safe_dn}`;
      f2.dispatchEvent(new Event('input', {{bubbles:true}}));
      f2.dispatchEvent(new Event('change', {{bubbles:true}}));
      f2.dispatchEvent(new Event('blur', {{bubbles:true}})); }}
  }}
  // Esegue subito, poi ripete più volte: alcune app ripristinano i campi da
  // localStorage dopo il caricamento, e dobbiamo vincere anche su quello.
  fill();
  window.addEventListener('load', fill);
  setTimeout(fill, 300);
  setTimeout(fill, 800);
  setTimeout(fill, 1500);

  // Bottone manuale nella topbar: garantisce il riempimento anche se i
  // tentativi automatici sono partiti troppo presto/tardi rispetto al
  // caricamento reale della pagina.
  var topbar2 = document.querySelector('.topbar');
  if (topbar2) {{
    var btn2 = document.createElement('button');
    btn2.type = 'button'; btn2.className = 'noprint';
    btn2.textContent = '📋 Inserisci dati anagrafica selezionati';
    btn2.style.cssText = 'background:#1D6B44;color:#fff;border:0;border-radius:4px;padding:6px 11px;font-size:12px;font-family:inherit;cursor:pointer;margin-left:6px';
    btn2.addEventListener('click', fill);
    topbar2.appendChild(btn2);
  }}
}})();
</script>
"""

    _second_monitor_js = """
<style>
#pnev_sm_btn{background:#1D6B44;color:#fff;border:0;border-radius:4px;padding:6px 11px;
font-size:12px;font-family:inherit;cursor:pointer;margin-left:6px}
#pnev_sm_hint{position:fixed;top:50px;right:16px;z-index:9999;background:#123a6b;color:#fff;
font-size:11px;font-family:sans-serif;padding:6px 10px;border-radius:6px;max-width:220px;display:none}
.pnev_sm_ico{cursor:pointer;margin-left:5px;font-size:.85em;opacity:.7;text-decoration:none;user-select:none}
.pnev_sm_ico:hover{opacity:1}
</style>
<div id="pnev_sm_hint" class="noprint">Seleziona un testo/stimolo nella pagina, poi clicca di nuovo il bottone "Secondo monitor".</div>
<script>
(function(){
  function openMonitor(text){
    var safe = (text||'').replace(/`/g,"'").replace(/<\\//g,'<\\\\/');
    var w = window.open('', 'finestra_screening_bambino');
    if (w){
      w.document.open();
      w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8">' +
        '<title>The Organism · Schermo paziente</title><style>' +
        'body{margin:0;background:#0f1512;color:#fff;display:flex;align-items:center;' +
        'justify-content:center;min-height:100vh;font-family:sans-serif;}' +
        '.c{font-size:4vw;text-align:center;padding:40px;letter-spacing:.08em;line-height:1.5;font-weight:600;}' +
        '</style></head><body><div class="c">' + safe + '</div></body></html>');
      w.document.close();
      w.focus();
    } else {
      alert('Il browser ha bloccato la finestra popup: consenti i popup per questo sito.');
    }
  }

  // Bottone dentro la barra in alto (sticky), sempre visibile: invia il testo selezionato
  var topbar = document.querySelector('.topbar');
  var hint = document.getElementById('pnev_sm_hint');
  if (topbar){
    var btn = document.createElement('button');
    btn.id = 'pnev_sm_btn'; btn.type = 'button'; btn.className = 'noprint';
    btn.textContent = '🖥️ Secondo monitor (testo selezionato)';
    btn.addEventListener('click', function(){
      var sel = window.getSelection ? window.getSelection().toString().trim() : '';
      if (!sel){ hint.style.display='block'; setTimeout(function(){hint.style.display='none';}, 3500); return; }
      openMonitor(sel);
    });
    topbar.appendChild(btn);
  }

  // Icona dedicata su ogni stimolo (.stim): un clic, senza dover selezionare nulla —
  // usata per liste di parole/non parole, bilancio fonetico, frasi, ecc.
  document.querySelectorAll('.stim').forEach(function(el){
    var ico = document.createElement('span');
    ico.className = 'pnev_sm_ico noprint';
    ico.title = 'Mostra questo stimolo sul secondo monitor';
    ico.textContent = '🖥️';
    ico.addEventListener('click', function(ev){
      ev.stopPropagation();
      openMonitor(el.textContent.trim());
    });
    el.appendChild(ico);
  });

  // 4.1c — le tavole IReST sono materiale protetto e non sono riprodotte in questo
  // documento (uso obbligatorio delle tavole originali dello studio). Offriamo un
  // testo di lettura ALTERNATIVO, originale, solo per quando le tavole non sono
  // disponibili — chiaramente etichettato come non-IReST.
  var TESTI_ALT = [
    "Ogni sabato Marta andava con il nonno a raccogliere le castagne nel bosco vicino casa. Camminavano piano, guardando tra le foglie secche, mentre il nonno le raccontava di quando lui era piccolo e faceva lo stesso percorso con suo padre. Alla fine tornavano a casa con il cesto pieno, pronti per arrostirle la sera davanti al fuoco.",
    "Da quando aveva iniziato ad allenarsi in piscina, Luca notava di riuscire a nuotare più a lungo senza fermarsi. L'allenatore gli aveva insegnato a respirare con calma, girando la testa di lato ad ogni bracciata, invece di alzarla in avanti come faceva prima. Con il tempo, quel piccolo cambiamento gli aveva fatto guadagnare molta più resistenza.",
    "Il giardino botanico della città ospitava piante arrivate da ogni parte del mondo, alcune delle quali erano lì da più di cento anni. I visitatori passeggiavano lungo i sentieri, leggendo le targhette che spiegavano da dove venisse ciascuna specie. Nella serra centrale, l'aria calda e umida faceva crescere piante che altrove non sarebbero sopravvissute."
  ];
  var h4s = document.querySelectorAll('h4');
  for (var i=0;i<h4s.length;i++){
    if (h4s[i].textContent.indexOf('4.1c') !== -1){
      var box = document.createElement('div');
      box.className = 'note noprint';
      box.style.marginTop = '4px';
      var idx = 0;
      var span = document.createElement('span');
      span.textContent = 'Testo alternativo (NON IReST, uso solo se le tavole originali non sono disponibili): ';
      var btn2 = document.createElement('button');
      btn2.type = 'button'; btn2.textContent = '🖥️ Mostra sul secondo monitor';
      btn2.style.cssText = 'background:#1D6B44;color:#fff;border:0;border-radius:4px;padding:4px 9px;font-size:11px;cursor:pointer;margin-left:6px';
      btn2.addEventListener('click', function(){
        openMonitor(TESTI_ALT[idx % TESTI_ALT.length]);
        idx++;
      });
      box.appendChild(span); box.appendChild(btn2);
      h4s[i].parentNode.insertBefore(box, h4s[i].nextSibling);
      break;
    }
  }
})();
</script>
"""
    _script_completo = _second_monitor_js + (_precompila_js or "")
    if "</body>" in html:
        html = html.replace("</body>", _script_completo + "</body>", 1)
    else:
        html += _script_completo

    components.html(html, height=1400, scrolling=True)
