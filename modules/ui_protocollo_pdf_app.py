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
import json
import datetime
import streamlit as st
import streamlit.components.v1 as components

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static_protocollo")
_HTML_PATH = os.path.join(_STATIC_DIR, "PNEV_protocollo_app_MASTER.html")


def render_protocollo_pdf_app(conn=None, paz_id=None, paziente=None,
                               html_file="PNEV_protocollo_app_MASTER.html",
                               pdf_file="Protocollo_valutazione_TheOrganism.pdf",
                               titolo="📋 Protocollo di valutazione — app stampabile",
                               sottotitolo=("Versione a impaginazione A4 fedele al documento, con "
                                            "calcolatori automatici (PCC, %SS, indici) e stampa diretta."),
                               kp="pv") -> None:
    """kp = prefisso delle chiavi widget: serve per poter montare più varianti
    (protocollo completo, screening breve) senza collisioni di key."""
    st.header(titolo)
    st.caption(sottotitolo)
    st.warning("⚠️ Salvataggio: usa **Esporta** per scaricare i dati come file, e **Importa** per "
               "riaprirli — così restano legati al paziente indipendentemente dal browser usato. "
               "\"Salva\"/\"Riapri\" nella barra della app usano solo la memoria di questo browser.")

    # Scheda bianca e manuale d'uso, se presenti in static_protocollo/.
    # Prima un PDF mancante veniva ignorato in silenzio: il bottone
    # semplicemente non c'era e nessuno sapeva perche'. Ora lo si dice.
    _col_pdf, _col_man = st.columns(2)
    _pdf_path = os.path.join(_STATIC_DIR, pdf_file)
    # Salvando in PDF il browser a volte aggiunge un secondo ".pdf" al nome:
    # si accetta anche quello, invece di far sparire il bottone.
    if not os.path.exists(_pdf_path) and os.path.exists(_pdf_path + ".pdf"):
        _pdf_path = _pdf_path + ".pdf"
    with _col_pdf:
        if os.path.exists(_pdf_path):
            with open(_pdf_path, "rb") as f:
                st.download_button("📄 Scheda in PDF (bianca, da compilare a mano)",
                                    data=f.read(), file_name=pdf_file,
                                    mime="application/pdf", key=f"{kp}_dl_pdf",
                                    use_container_width=True)
        else:
            st.caption(f"📄 Scheda in PDF non ancora caricata: manca "
                       f"`static_protocollo/{pdf_file}`.")
    _man_file = "Manuale_Screening_TheOrganism.pdf"
    _man_path = os.path.join(_STATIC_DIR, _man_file)
    if not os.path.exists(_man_path) and os.path.exists(_man_path + ".pdf"):
        _man_path = _man_path + ".pdf"
    with _col_man:
        if os.path.exists(_man_path):
            with open(_man_path, "rb") as f:
                st.download_button("📘 Manuale d'uso (breve e completo)",
                                    data=f.read(), file_name=_man_file,
                                    mime="application/pdf", key=f"{kp}_dl_manuale",
                                    use_container_width=True)
        else:
            st.caption(f"📘 Manuale non ancora caricato: manca "
                       f"`static_protocollo/{_man_file}`.")

    try:
        with open(os.path.join(_STATIC_DIR, html_file), "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        st.error(f"File del protocollo non trovato: {e}")
        return

    # Selettore paziente dall'anagrafica del gestionale: precompila Cognome/Nome
    # e Data di nascita nell'HTML statico (che di per sé non ha accesso al DB).
    nome_precompilato = data_nascita_precompilata = eta_precompilata = ""
    if conn is not None:
        with st.expander("➕ Nuovo paziente (non ancora in anagrafica)"):
            cn1, cn2 = st.columns(2)
            nuovo_cognome = cn1.text_input("Cognome", key=f"{kp}_html_nuovo_cognome")
            nuovo_nome = cn2.text_input("Nome", key=f"{kp}_html_nuovo_nome")
            nuova_dn = st.date_input("Data di nascita", key=f"{kp}_html_nuova_dn",
                                      value=None, min_value=datetime.date(1930, 1, 1))
            if st.button("Crea e usa questo paziente", key=f"{kp}_html_crea_paziente"):
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
            scelta = st.selectbox("👤 Precompila da anagrafica", opzioni, key=f"{kp}_html_pick_paziente")
            if scelta != opzioni[0]:
                idx_sel = opzioni.index(scelta) - 1
                r = righe[idx_sel]
                cognome_sel = _g(r, 1, "cognome") or ""
                nome_sel = _g(r, 2, "nome") or ""
                dn_sel = _g(r, 3, "data_nascita")
                nome_precompilato = f"{cognome_sel} {nome_sel}".strip()
                data_nascita_precompilata = dn_sel.strftime("%d/%m/%Y") if hasattr(dn_sel, "strftime") else (str(dn_sel) if dn_sel else "")
                try:
                    _dn = dn_sel
                    if isinstance(_dn, str):
                        _dn = datetime.date.fromisoformat(_dn[:10])
                    if hasattr(_dn, "year"):
                        _oggi = datetime.date.today()
                        _anni = _oggi.year - _dn.year - ((_oggi.month, _oggi.day) < (_dn.month, _dn.day))
                        _mesi = (_oggi.month - _dn.month) % 12
                        eta_precompilata = f"{_anni};{_mesi:02d}"
                except Exception:
                    pass

    _precompila_js = ""
    if nome_precompilato:
        _safe_eta = (eta_precompilata or "").replace("\\", "").replace("`", "'")
        _safe_nome = nome_precompilato.replace("\\", "").replace("`", "'")
        _safe_dn = (data_nascita_precompilata or "").replace("\\", "").replace("`", "'")
        _precompila_js = f"""
<script>
(function(){{
  var NOME = `{_safe_nome}`, DN = `{_safe_dn}`, ETA = `{_safe_eta}`;

  function fill(){{
    var fatto = false;

    // Struttura A — protocollo completo: campi con attributo data-k
    var f1 = document.querySelector('[data-k="f1"]');
    var f2 = document.querySelector('[data-k="f2"]');
    if (f1 || f2) {{
      [[f1, NOME], [f2, DN]].forEach(function(p){{
        if (!p[0]) return;
        p[0].value = p[1];
        ['input','change','blur'].forEach(function(ev){{
          p[0].dispatchEvent(new Event(ev, {{bubbles:true}}));
        }});
      }});
      fatto = true;
    }}

    // Struttura B — screening breve: valori nell'oggetto V, campi ridisegnati
    // da draw(). Scriviamo in V e forziamo il redisegno.
    if (!fatto && typeof window.V === 'object' && window.V !== null) {{
      window.V.nome = NOME;
      if (ETA) window.V.eta = ETA;
      if (!window.V.data) {{
        var oggi = new Date();
        window.V.data = oggi.getFullYear() + '-' +
          String(oggi.getMonth()+1).padStart(2,'0') + '-' +
          String(oggi.getDate()).padStart(2,'0');
      }}
      try {{ if (typeof window.sl === 'function') window.sl(); }} catch(e){{}}
      try {{ if (typeof window.draw === 'function') window.draw(); }} catch(e){{}}
      try {{ if (typeof window.prog === 'function') window.prog(); }} catch(e){{}}
      fatto = true;
    }}
    return fatto;
  }}

  // Esegue subito, poi ripete: alcune app ripristinano i campi da
  // localStorage dopo il caricamento, e dobbiamo vincere anche su quello.
  fill();
  window.addEventListener('load', fill);
  setTimeout(fill, 300);
  setTimeout(fill, 800);
  setTimeout(fill, 1500);

  // Bottone manuale: cercato in .topbar (protocollo completo) o in
  // header/.bar (screening breve), così c'è sempre un modo esplicito.
  function montaBottone(){{
    var host = document.querySelector('.topbar') || document.querySelector('header')
               || document.querySelector('.bar');
    if (!host || host.querySelector('.pnev-fill-btn')) return;
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'noprint pnev-fill-btn';
    b.textContent = '📋 Inserisci dati anagrafica';
    b.style.cssText = 'background:#1D6B44;color:#fff;border:0;border-radius:5px;padding:6px 11px;font-size:12.5px;font-family:inherit;cursor:pointer;margin-left:8px';
    b.addEventListener('click', function(){{
      if (!fill()) alert('Campi anagrafici non trovati in questa scheda.');
    }});
    host.appendChild(b);
  }}
  montaBottone();
  setTimeout(montaBottone, 600);
  setTimeout(montaBottone, 1600);
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
  var topbar = document.querySelector('.topbar') || document.querySelector('header')
               || document.querySelector('.bar');
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

    _salva_db_js = """
<script>
(function(){
  var topbar3 = document.querySelector('.topbar') || document.querySelector('header')
                || document.querySelector('.bar');
  if (!topbar3) return;
  var btn3 = document.createElement('button');
  btn3.type = 'button'; btn3.className = 'noprint';
  btn3.textContent = '📤 Prepara dati per il salvataggio';
  btn3.style.cssText = 'background:#123a6b;color:#fff;border:0;border-radius:4px;padding:6px 11px;font-size:12px;font-family:inherit;cursor:pointer;margin-left:6px';
  btn3.addEventListener('click', function(){
    try {
      var payload = JSON.stringify({V: window.V || {}, C: window.C || {}});
      var box = document.createElement('textarea');
      box.value = payload;
      box.style.cssText = 'position:fixed;top:60px;left:16px;right:16px;z-index:9999;height:120px;font-size:11px;';
      box.readOnly = true;
      document.body.appendChild(box);
      box.select();
      try { document.execCommand('copy'); } catch(e){}
      alert('Dati pronti e copiati (se il browser lo consente). Se non si sono copiati da soli, seleziona il testo nel riquadro apparso e copialo manualmente, poi incollalo nel gestionale qui sotto.');
      setTimeout(function(){ box.remove(); }, 15000);
    } catch(e){ alert('Errore preparazione dati: ' + e.message); }
  });
  topbar3.appendChild(btn3);
})();
</script>
"""
    # Anteprima e stampa della relazione su carta intestata.
    # La app stampava con window.print(), cioe' TUTTA la scheda di lavoro —
    # ogni prova, ogni tabella — anche quando all'operatore serviva solo la
    # relazione per la famiglia; e la relazione vive in un <textarea>, di cui
    # i browser stampano solo la parte visibile, tagliando il resto. La carta
    # intestata poi non c'era affatto: la app sta in un iframe e non vede il
    # database. Il modulo qui sotto aggiunge un foglio A4 a schermo, con la
    # carta intestata dello studio, il testo impaginato misurandolo, e una
    # stampa che riproduce quel foglio e nient'altro.
    _carta_js = ""
    try:
        from .stampa_carta_intestata import script_stampa_carta
        _carta_js = script_stampa_carta()
    except Exception as e:
        st.caption(f"Anteprima su carta intestata non disponibile: {e}")

    _script_completo = _second_monitor_js + (_precompila_js or "") + _salva_db_js + _carta_js
    if "</body>" in html:
        html = html.replace("</body>", _script_completo + "</body>", 1)
    else:
        html += _script_completo

    components.html(html, height=1400, scrolling=True)

    st.markdown("---")
    st.markdown("#### 💾 Salva questo screening nel gestionale")
    st.caption("Registra i dati compilati collegati a un'anagrafica leggera (nome, data di nascita, "
               "contatto) — se il bambino diventerà paziente dello studio, potrai agganciare questo "
               "screening al suo fascicolo senza reinserire nulla.")
    dati_json_incollati = st.text_area(
        "1) Clicca '📤 Prepara dati per il salvataggio' nella barra della app qui sopra, poi copia "
        "il testo che appare e incollalo qui:", key=f"{kp}_html_dati_export", height=90)
    c_s1, c_s2 = st.columns(2)
    contatto_screening = c_s1.text_input("Telefono/email di contatto (facoltativo)", key=f"{kp}_html_contatto")
    if c_s2.button("💾 Salva nel gestionale", key=f"{kp}_html_salva_db", type="primary"):
        if not dati_json_incollati.strip():
            st.warning("Incolla prima i dati esportati dalla barra della app.")
        elif conn is None:
            st.error("Connessione al database non disponibile.")
        else:
            try:
                payload = json.loads(dati_json_incollati)
            except Exception:
                st.error("Il testo incollato non è un JSON valido — copialo di nuovo dal bottone 'Prepara dati'.")
                payload = None
            if payload is not None:
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS screening_esterni (
                            id BIGSERIAL PRIMARY KEY,
                            paziente_id BIGINT NULL,
                            nome_cognome TEXT, data_nascita TEXT, contatto TEXT,
                            dati JSONB, creato_il TIMESTAMPTZ DEFAULT now()
                        )
                    """)
                    valori = payload.get("V", {})
                    nome_reg = valori.get("f1", "") or nome_precompilato
                    dn_reg = valori.get("f2", "") or data_nascita_precompilata
                    cur.execute("""
                        INSERT INTO screening_esterni (paziente_id, nome_cognome, data_nascita, contatto, dati)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (paz_id if paz_id else None, nome_reg, dn_reg, contatto_screening,
                          json.dumps(payload)))
                    conn.commit()
                    st.success(f"Screening salvato per **{nome_reg or 'senza nome'}**"
                               + (f" — agganciato al paziente #{paz_id}." if paz_id else
                                  " — non ancora agganciato a un paziente: se diventerà paziente, "
                                  "potrai collegarlo in seguito da Pazienti → Screening in attesa."))
                except Exception as e:
                    try: conn.rollback()
                    except Exception: pass
                    st.error(f"Errore salvataggio: {e}")

    st.markdown("---")
    try:
        from .ui_relazione_screening import render_relazione
        dati_per_relazione = {}
        if dati_json_incollati.strip():
            try:
                dati_per_relazione = json.loads(dati_json_incollati)
            except Exception:
                pass
        if not dati_per_relazione:
            st.caption("Per una relazione ricca di dettagli, incolla prima i dati esportati qui sopra: "
                       "l'AI li usa per scrivere le sezioni descrittive.")
        render_relazione(conn, paz_id, dati_valutazione=dati_per_relazione,
                         fonte=html_file, kp=f"{kp}_rel")
    except Exception as e:
        st.warning(f"Relazione funzionale non disponibile: {e}")
