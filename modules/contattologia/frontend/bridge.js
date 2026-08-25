/*! Ponte fra il Progetto multicurva RGP e Streamlit.
    Progettato da Dott. Giuseppe Ferraioli — www.pnev.it
    © 2026 Giuseppe Ferraioli. Tutti i diritti riservati.

    Protocollo dei componenti Streamlit, implementato a mano: nessuna
    dipendenza npm, nessun build step. Il componente:
      · dichiara di essere pronto            → streamlit:componentReady
      · comunica quanto è alto               → streamlit:setFrameHeight
      · restituisce un valore SOLO su azione → streamlit:setComponentValue
    L'ultimo punto è quello che conta: setComponentValue fa rieseguire lo
    script Streamlit, quindi non va chiamato a ogni ricalcolo del modulo
    ma solo quando l'utente salva o genera un ordine.                     */
(function () {
  "use strict";

  var PRONTO = false;
  var ultimaAltezza = 0;

  function verso(tipo, extra) {
    var msg = { isStreamlitMessage: true, type: tipo };
    for (var k in extra) msg[k] = extra[k];
    window.parent.postMessage(msg, "*");
  }

  function pronto() {
    if (PRONTO) return;
    PRONTO = true;
    verso("streamlit:componentReady", { apiVersion: 1 });
  }

  var _timerAltezza = null;
  function altezza(h) {
    clearTimeout(_timerAltezza);
    _timerAltezza = setTimeout(function () {
      var v = h;
      if (!v) {
        var d = document.documentElement, b = document.body;
        v = Math.max(d.scrollHeight, d.offsetHeight, b ? b.scrollHeight : 0);
      }
      v = Math.ceil(v) + 8;
      if (Math.abs(v - ultimaAltezza) < 24) return;   /* evita oscillazioni/ping continuo */
      ultimaAltezza = v;
      verso("streamlit:setFrameHeight", { height: v });
    }, 250);
  }

  function restituisci(valore) {
    verso("streamlit:setComponentValue", { value: valore, dataType: "json" });
  }

  /* ---- dal modulo verso Streamlit -------------------------------------- */
  var contatore = 0;
  window.addEventListener("rgp", function (e) {
    var d = e.detail || {};
    if (d.type === "rgp:change") { altezza(); return; }   /* mai un valore: riavvierebbe lo script */
    if (d.type === "rgp:save" || d.type === "rgp:order") {
      contatore += 1;
      restituisci({
        type: d.type,
        stamp: String(contatore) + "-" + (d.record && d.record.id ? d.record.id : ""),
        record: d.record || null,
        filename: d.filename || null,
        pdfBase64: d.pdfBase64 || null,
        payload: d.payload || null
      });
    }
  });

  /* ---- da Streamlit verso il modulo ------------------------------------ */
  var ultimoRecordId = null;
  window.addEventListener("message", function (e) {
    var d = e.data || {};
    if (d.type !== "streamlit:render") return;
    var args = d.args || {};

    if (args.altezza) altezza(args.altezza);

    /* tema: il modulo ha già il suo interruttore, qui si allinea a Streamlit */
    if (d.theme && d.theme.base) {
      try {
        document.documentElement.setAttribute(
          "data-theme", d.theme.base === "dark" ? "dark" : "light");
      } catch (err) { /* il modulo resta sul tema di sistema */ }
    }

    /* riapertura di un progetto letto da PostgreSQL */
    var r = args.record;
    if (r && r.id && r.id !== ultimoRecordId && window.RGP && window.RGP.loadRecord) {
      ultimoRecordId = r.id;
      try { window.RGP.loadRecord(r); } catch (err) { console.error("riapertura fallita", err); }
    }
    setTimeout(altezza, 60);
  });

  /* ---- avvio ----------------------------------------------------------- */
  function avvia() {
    pronto();
    altezza();
    setTimeout(altezza, 300);
    setTimeout(altezza, 1200);
    if (window.ResizeObserver) {
      /* si osserva solo per catturare cambi di layout non coperti dall'evento
         rgp:change (es. font caricati in ritardo); niente osservazione
         continua sul body, che rifà i calcoli ad ogni interazione (hover,
         digitazione) ed è la causa dello sfarfallio durante lo scroll. */
      setInterval(altezza, 2000);
    } else {
      setInterval(altezza, 2000);
    }
  }
  if (document.readyState === "complete" || document.readyState === "interactive") avvia();
  else document.addEventListener("DOMContentLoaded", avvia);
})();
