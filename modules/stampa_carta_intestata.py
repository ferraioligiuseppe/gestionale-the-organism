# -*- coding: utf-8 -*-
"""Anteprima e stampa su carta intestata per le app HTML statiche.

Il problema che risolve
-----------------------
Le app di screening (`static_protocollo/*.html`) sono documenti autonomi che
stampano con `window.print()`. Due conseguenze:

1. Stampava TUTTA l'app — ogni sezione, ogni prova, ogni tabella di lavoro —
   anche quando all'operatore serviva solo la relazione per la famiglia.
2. La relazione vive in un `<textarea>`. I browser stampano di un textarea
   solo la porzione visibile: il testo veniva tagliato a metà.
3. Nessuna carta intestata: l'app sta in un iframe e non ha accesso al
   database dello studio.

Qui si costruisce un'anteprima vera: un foglio A4 a schermo, con la carta
intestata dello studio come sfondo, il testo della relazione impaginato nello
spazio libero fra intestazione e piè di pagina, e la paginazione calcolata
misurando il testo — non indovinata. La stampa riproduce esattamente quel
foglio e nient'altro.

La carta intestata arriva dal database (la stessa di PDF e Word: una sola
fonte) e viene iniettata nell'iframe come data URI, così l'app resta
autonoma e funziona anche a Internet spento.
"""
from __future__ import annotations

import base64

# Geometria della carta intestata, identica a quella usata per il Word in
# relazione_docx.py: se un giorno la carta cambia proporzioni, questi due
# numeri vanno cambiati in entrambi i file.
FASCIA_ALTA = 0.18      # 18% dall'alto: loghi, nome, titolo
FASCIA_BASSA = 0.14     # 14% dal basso: filetto, indirizzo, contatti

# A4 in millimetri, e i margini del testo ricavati dalle due fasce con un po'
# di respiro perché il testo non tocchi la grafica.
MM_ALTEZZA = 297.0
MM_LARGHEZZA = 210.0
MM_ARIA = 5.0
MM_LATERALE = 20.0


def _carta_data_uri() -> tuple[str, str]:
    """(data URI della carta intestata, motivo dell'assenza).

    Il motivo non è decorativo: senza, quando la carta manca l'operatore
    stampa un foglio bianco e non sa perché. È lo stesso errore che teneva
    la carta intestata fuori dai Word per settimane.
    """
    try:
        from .pdf_templates import _carta_intestata_bytes
    except Exception as e:
        return "", f"modulo pdf_templates non disponibile: {e}"
    try:
        dati = _carta_intestata_bytes()
    except Exception as e:
        return "", f"lettura della configurazione non riuscita: {e}"
    if not dati:
        return "", ("nessuna carta intestata salvata per questo studio — "
                    "si carica da «Intestazione dello studio» → «Carta intestata»")
    testa = dati[:12]
    if testa.startswith(b"\x89PNG"):
        mime = "image/png"
    elif testa.startswith(b"\xff\xd8"):
        mime = "image/jpeg"
    elif testa.startswith(b"GIF8"):
        mime = "image/gif"
    elif testa[:4] == b"RIFF" and dati[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        return "", (f"formato dell'immagine non riconosciuto ({len(dati)} byte): "
                    "servono PNG, JPEG, GIF o WebP")
    return f"data:{mime};base64,{base64.b64encode(dati).decode()}", ""


def script_stampa_carta() -> str:
    """Il blocco <style> + <script> da iniettare prima di </body>."""
    uri, motivo = _carta_data_uri()

    sopra = MM_ALTEZZA * FASCIA_ALTA + MM_ARIA
    sotto = MM_ALTEZZA * FASCIA_BASSA + MM_ARIA
    utile = MM_ALTEZZA - sopra - sotto

    return (_MODELLO
            .replace("__URI__", uri)
            .replace("__MOTIVO__", motivo.replace("'", "\u2019"))
            .replace("__SOPRA__", f"{sopra:.1f}")
            .replace("__SOTTO__", f"{sotto:.1f}")
            .replace("__UTILE__", f"{utile:.1f}")
            .replace("__LATERALE__", f"{MM_LATERALE:.1f}")
            .replace("__LARGH__", f"{MM_LARGHEZZA:.1f}")
            .replace("__ALTEZ__", f"{MM_ALTEZZA:.1f}"))


def inietta(html: str) -> str:
    """Aggiunge il blocco all'HTML dell'app, prima di </body>."""
    blocco = script_stampa_carta()
    if "</body>" in html:
        return html.replace("</body>", blocco + "</body>", 1)
    return html + blocco


_MODELLO = r"""
<style id="pnev_ci_style">
#pnev_ci_ovl{position:fixed;inset:0;z-index:99999;background:#3B4440;
  overflow:auto;display:none;padding:26px 0 60px}
#pnev_ci_ovl.on{display:block}
#pnev_ci_bar{position:sticky;top:0;z-index:2;display:flex;flex-wrap:wrap;gap:8px;
  align-items:center;justify-content:center;padding:10px 14px;margin:-26px 0 22px;
  background:#2B332F;box-shadow:0 2px 10px rgba(0,0,0,.3)}
#pnev_ci_bar button{border:0;border-radius:5px;padding:8px 15px;cursor:pointer;
  font:600 13px/1 inherit;color:#fff;background:#1D6B44}
#pnev_ci_bar button.sec{background:#5A6660}
#pnev_ci_bar span{color:#C8D2CC;font:400 12px/1.4 inherit}
.pnev_ci_foglio{width:__LARGH__mm;min-height:__ALTEZ__mm;margin:0 auto 22px;
  background:#fff center/100% 100% no-repeat;position:relative;
  box-shadow:0 5px 22px rgba(0,0,0,.35)}
.pnev_ci_corpo{position:absolute;left:__LATERALE__mm;right:__LATERALE__mm;
  top:__SOPRA__mm;height:__UTILE__mm;overflow:hidden;
  font:400 10.8pt/1.58 Georgia,"Times New Roman",serif;color:#1A1A1A;
  text-align:justify;text-wrap:pretty}
.pnev_ci_corpo p{margin:0 0 7pt}
.pnev_ci_corpo h3{margin:11pt 0 5pt;font:600 11.6pt/1.35 Georgia,serif;
  color:#155235;text-align:left}
.pnev_ci_corpo li{margin:0 0 5pt;list-style:none;padding-left:13pt;
  text-indent:-13pt;text-align:left}
.pnev_ci_corpo .rif{font-size:9.3pt;line-height:1.45;color:#3E4A43;text-align:left}
.pnev_ci_corpo .firma{margin-top:14pt;font-size:10.4pt;text-align:left}
.pnev_ci_np{position:absolute;right:__LATERALE__mm;bottom:calc(__SOTTO__mm - 4mm);
  font:400 8.6pt/1 Georgia,serif;color:#6E7A73}
.pnev_ci_manca{max-width:520px;margin:40px auto;background:#fff;border-radius:8px;
  padding:22px 26px;font:400 14px/1.6 inherit;color:#1A1A1A}
.pnev_ci_manca b{color:#A63528}
@media print{
  body.pnev_ci_stampa>*{display:none!important}
  body.pnev_ci_stampa #pnev_ci_ovl{display:block!important;position:static;
    background:#fff;padding:0;overflow:visible}
  body.pnev_ci_stampa #pnev_ci_bar{display:none!important}
  body.pnev_ci_stampa .pnev_ci_foglio{box-shadow:none;margin:0;
    break-after:page;page-break-after:always}
  body.pnev_ci_stampa .pnev_ci_foglio:last-child{break-after:auto;page-break-after:auto}
}
</style>
<div id="pnev_ci_ovl" class="noprint"></div>
<script>
(function(){
  var URI = "__URI__", MOTIVO = "__MOTIVO__";
  var ovl = document.getElementById('pnev_ci_ovl');

  /* Il testo della relazione: quello corretto a mano dall'operatore se c'è,
     altrimenti quello generato dagli esiti. Non viene riscritto: solo
     riconosciuto nella sua struttura e impaginato. */
  function testo(){
    var ta = document.getElementById('rel');
    if (ta && ta.value.trim()) return ta.value;
    try { if (window.V && window.V.reltxt) return window.V.reltxt; } catch(e){}
    try { if (typeof window.relTesto === 'function') return window.relTesto(); } catch(e){}
    return '';
  }

  function esc(t){ return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* Da testo semplice a blocchi tipografici. Le righe le ha scritte lo
     studio: qui si decide soltanto come si compongono sul foglio. */
  function blocchi(txt){
    var out = [], righe = txt.replace(/\r/g,'').split('\n'), acc = [], inRif = false;

    function chiudi(){
      if (!acc.length) return;
      var t = acc.join(' ').trim();
      if (t) out.push({t:'p', h:'<p'+(inRif?' class="rif"':'')+'>'+esc(t)+'</p>'});
      acc = [];
    }
    for (var i=0;i<righe.length;i++){
      var r = righe[i], s = r.trim();
      if (!s){ chiudi(); continue; }

      if (/^(Riferimenti|Bibliografia)$/i.test(s)){
        chiudi(); inRif = true;
        out.push({t:'h', h:'<h3>'+esc(s)+'</h3>'});
        continue;
      }
      /* elenco: trattino lungo o punto medio */
      if (/^[—·-]\s+/.test(s)){
        chiudi();
        out.push({t:'li', h:'<li'+(inRif?' class="rif"':'')+'>'+esc(s)+'</li>'});
        continue;
      }
      /* firma e data: righe con una fila di underscore */
      if (/_{4,}/.test(s)){
        chiudi();
        out.push({t:'firma', h:'<p class="firma">'+esc(s)+'</p>'});
        continue;
      }
      /* titolo di paragrafo: riga breve, isolata, senza punto finale */
      var soloPrima = (i===0) || !righe[i-1].trim();
      var soloDopo  = (i===righe.length-1) || !righe[i+1].trim();
      if (!inRif && soloPrima && soloDopo && s.length<=64 && !/[.;:,!?]$/.test(s)
          && /^[A-ZÀ-Ù]/.test(s)){
        chiudi();
        out.push({t:'h', h:'<h3>'+esc(s)+'</h3>'});
        continue;
      }
      acc.push(s);
    }
    chiudi();
    return out;
  }

  /* Impaginazione per misura: si aggiunge un blocco, si guarda se il corpo
     è debordato, e in quel caso si apre un foglio nuovo. Nessuna stima di
     righe per pagina: è il browser a dire quando non ci sta più. */
  function componi(txt){
    ovl.innerHTML = '';
    var bar = document.createElement('div');
    bar.id = 'pnev_ci_bar';
    ovl.appendChild(bar);

    if (!URI){
      var av = document.createElement('div');
      av.className = 'pnev_ci_manca';
      av.innerHTML = '<b>Carta intestata non disponibile.</b><br><br>' + esc(MOTIVO) +
        '.<br><br>L\u2019anteprima si apre comunque su foglio bianco, ' +
        'cos\u00EC puoi controllare il testo e l\u2019impaginazione: ' +
        'mancher\u00E0 soltanto la grafica.';
      ovl.appendChild(av);
    }

    var bl = blocchi(txt), fogli = [], f = null, corpo = null, ul = null;

    function nuovoFoglio(){
      f = document.createElement('div');
      f.className = 'pnev_ci_foglio';
      if (URI) f.style.backgroundImage = 'url("'+URI+'")';
      corpo = document.createElement('div');
      corpo.className = 'pnev_ci_corpo';
      f.appendChild(corpo);
      ovl.appendChild(f);
      fogli.push(f);
      ul = null;
      return corpo;
    }
    nuovoFoglio();

    function deborda(){ return corpo.scrollHeight > corpo.clientHeight + 1; }

    for (var i=0;i<bl.length;i++){
      var b = bl[i];
      var host = corpo, wrap = null;
      if (b.t === 'li'){
        if (!ul){ ul = document.createElement('ul');
                  ul.style.cssText='margin:0 0 7pt;padding:0';
                  corpo.appendChild(ul); }
        host = ul;
      } else { ul = null; }

      wrap = document.createElement('div');
      wrap.style.display = 'contents';
      wrap.innerHTML = b.h;
      host.appendChild(wrap);

      if (deborda()){
        host.removeChild(wrap);
        /* un titolo non resta solo in fondo: passa alla pagina dopo col suo testo */
        nuovoFoglio();
        if (b.t === 'li'){ ul = document.createElement('ul');
                           ul.style.cssText='margin:0 0 7pt;padding:0';
                           corpo.appendChild(ul); host = ul; }
        else host = corpo;
        host.appendChild(wrap);
      }
    }

    fogli.forEach(function(el, n){
      var np = document.createElement('div');
      np.className = 'pnev_ci_np';
      np.textContent = (n+1) + ' / ' + fogli.length;
      el.appendChild(np);
    });

    bar.innerHTML = '';
    var bStampa = document.createElement('button');
    bStampa.textContent = '\u2399 Stampa';
    bStampa.onclick = function(){
      document.body.classList.add('pnev_ci_stampa');
      window.print();
      setTimeout(function(){ document.body.classList.remove('pnev_ci_stampa'); }, 400);
    };
    var bChiudi = document.createElement('button');
    bChiudi.className = 'sec';
    bChiudi.textContent = 'Torna alla scheda';
    bChiudi.onclick = chiudi;
    var info = document.createElement('span');
    info.textContent = fogli.length + (fogli.length===1 ? ' pagina' : ' pagine')
                     + ' \u00B7 A4' + (URI ? ' \u00B7 carta intestata dello studio' : '');
    bar.appendChild(bStampa); bar.appendChild(bChiudi); bar.appendChild(info);
  }

  function apri(){
    var t = testo();
    if (!t.trim()){
      alert('La relazione \u00E8 ancora vuota: apri la sezione \u00ABRelazione per la famiglia\u00BB '
          + 'e genera il testo dagli esiti, poi torna qui.');
      return;
    }
    /* L'impaginazione si fa MISURANDO il testo, e un elemento in display:none
       misura zero: composta da nascosta, la relazione finiva tutta su una
       pagina sola. Quindi prima si apre, poi si compone — invisibile solo il
       tempo di farlo, per non mostrare il testo che si riorganizza. */
    ovl.classList.add('on');
    ovl.style.visibility = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    componi(t);
    ovl.style.visibility = '';
    ovl.scrollTop = 0;
  }
  function chiudi(){
    ovl.classList.remove('on');
    ovl.style.visibility = '';
    document.documentElement.style.overflow = '';
  }
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && ovl.classList.contains('on')) chiudi();
  });
  window.pnevAnteprimaCarta = apri;

  /* Il bottone va accanto a quelli della relazione, dove l'operatore lo
     cerca. La sezione viene ridisegnata da draw() a ogni modifica, quindi
     si ricontrolla invece di montarlo una volta sola. */
  function monta(){
    var ta = document.getElementById('rel');
    if (!ta) return;
    var zona = ta.parentNode.querySelector('.noprint');
    if (!zona || zona.querySelector('.pnev_ci_btn')) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'act pnev_ci_btn';
    b.textContent = '\u2399 Anteprima su carta intestata';
    b.style.cssText = 'background:#1D6B44;color:#fff;border:0;border-radius:5px;'
                    + 'padding:6px 12px;font:inherit;font-size:12.5px;cursor:pointer';
    b.onclick = apri;
    zona.insertBefore(b, zona.firstChild);

    /* La vecchia «Stampa» mandava in stampa l'intera app, comprese tutte le
       prove, e tagliava il testo del textarea. Resta, ma dice cosa fa. */
    Array.prototype.forEach.call(zona.querySelectorAll('button'), function(x){
      if (x !== b && /^\s*Stampa\s*$/.test(x.textContent)){
        x.textContent = 'Stampa la scheda intera';
        x.title = 'Stampa tutta la scheda di lavoro. Per la relazione sola, '
                + 'su carta intestata, usa l\u2019anteprima.';
      }
    });
  }
  monta();
  setInterval(monta, 900);
})();
</script>
"""
