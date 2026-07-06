# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/email_pnev_pubblico.py — MILESTONE 4

Invio email transazionali per il percorso pubblico MAPS-CLEAR via Brevo
(https://api.brevo.com/v3/smtp/email — piano gratuito 300 email/giorno).

Le credenziali arrivano dal chiamante (letti da st.secrets nell'app):
    api_key         chiave API Brevo (xkeysib-...)
    mittente_email  indirizzo verificato su Brevo (identico!)
    mittente_nome   nome visualizzato dal paziente

Email disponibili:
    invia_magic_link(...)     benvenuto + link personale (alla registrazione)
    invia_promemoria(...)     promemoria sessione giornaliera (per cron, futuro)
    invia_completamento(...)  complimenti a percorso completato + invito in studio

Nessuna dipendenza extra: usa requests (già nel requirements del gestionale).
"""

import requests

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
VERDE = "#1D6B44"


# ═══════════════════════════════════════════════════════════════
# TEMPLATE BASE (HTML compatibile con i client di posta)
# ═══════════════════════════════════════════════════════════════

def _template(titolo, corpo_html, cta_testo=None, cta_url=None):
    """Involucro grafico verde MAPS-CLEAR. corpo_html = paragrafi già in HTML."""
    bottone = ""
    if cta_testo and cta_url:
        bottone = f"""
        <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px auto">
          <tr><td style="border-radius:12px;background:{VERDE}">
            <a href="{cta_url}" target="_blank"
               style="display:inline-block;padding:14px 32px;font-family:Arial,sans-serif;
                      font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none">
              {cta_testo}
            </a>
          </td></tr>
        </table>"""
    return f"""<!DOCTYPE html>
<html lang="it">
<body style="margin:0;padding:0;background:#f2f5f3">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f5f3;padding:24px 0">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden">
        <tr><td style="background:{VERDE};padding:26px 32px;text-align:center">
          <div style="font-family:Arial,sans-serif;font-size:24px;font-weight:bold;color:#ffffff">
            🎧 MAPS-CLEAR
          </div>
          <div style="font-family:Arial,sans-serif;font-size:12px;color:#d7e8de;margin-top:4px">
            7 giorni per parlare chiaro · Studio The Organism
          </div>
        </td></tr>
        <tr><td style="padding:32px">
          <h1 style="font-family:Arial,sans-serif;font-size:20px;color:#1a1a1a;margin:0 0 16px">{titolo}</h1>
          <div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.65;color:#333333">
            {corpo_html}
          </div>
          {bottone}
        </td></tr>
        <tr><td style="padding:20px 32px;background:#f7faf8;border-top:1px solid #e3ece7">
          <div style="font-family:Arial,sans-serif;font-size:11px;line-height:1.6;color:#8a9a91">
            Studio The Organism · Dott. Giuseppe Ferraioli — Psicologo e Optometrista Comportamentale<br>
            Pagani (SA) · Piano di Sorrento (NA) · <a href="https://www.pnev.it" style="color:{VERDE}">pnev.it</a><br>
            Ricevi questa email perché ti sei iscritto al percorso gratuito MAPS-CLEAR.
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# INVIO
# ═══════════════════════════════════════════════════════════════

def _invia(api_key, mittente_email, mittente_nome,
           dest_email, dest_nome, oggetto, html, testo):
    """Chiamata all'API Brevo. Ritorna (ok: bool, dettaglio: str)."""
    try:
        r = requests.post(
            BREVO_URL,
            headers={
                "api-key": api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            json={
                "sender": {"email": mittente_email, "name": mittente_nome},
                "to": [{"email": dest_email, "name": dest_nome or dest_email}],
                "subject": oggetto,
                "htmlContent": html,
                "textContent": testo,
            },
            timeout=15,
        )
        if r.status_code in (200, 201, 202):
            return True, "inviata"
        return False, f"Brevo {r.status_code}: {r.text[:300]}"
    except requests.RequestException as e:
        return False, f"errore rete: {e}"


def invia_magic_link(api_key, mittente_email, mittente_nome,
                     dest_email, dest_nome, magic_url):
    """Email di benvenuto con il link personale. Ritorna (ok, dettaglio)."""
    titolo = f"Benvenuto/a nel percorso, {dest_nome}!"
    corpo = f"""
      <p>La tua iscrizione al percorso gratuito <b>MAPS-CLEAR — 7 giorni per parlare chiaro</b>
      è confermata. 🎉</p>
      <p>Questo è il tuo <b>link personale</b>: ti permette di rivedere i tuoi progressi
      da <b>qualsiasi dispositivo</b>, senza username né password. Conservalo:
      questa email è la tua chiave di accesso.</p>
      <p style="font-size:13px;color:#666">Suggerimento: aggiungi questa email ai preferiti
      o spostala in una cartella dedicata, così la ritrovi al volo ogni giorno.</p>
    """
    testo = (f"Benvenuto/a, {dest_nome}!\n\n"
             f"La tua iscrizione a MAPS-CLEAR è confermata.\n"
             f"Il tuo link personale (senza password):\n{magic_url}\n\n"
             f"Conserva questa email: è la tua chiave di accesso.\n\n"
             f"Studio The Organism · pnev.it")
    html = _template(titolo, corpo, "📊 I miei progressi", magic_url)
    return _invia(api_key, mittente_email, mittente_nome,
                  dest_email, dest_nome, "🎧 MAPS-CLEAR — il tuo link personale", html, testo)


def invia_promemoria(api_key, mittente_email, mittente_nome,
                     dest_email, dest_nome, giorno, magic_url):
    """Promemoria della sessione del giorno (da agganciare al cron in futuro)."""
    titolo = f"Giorno {giorno}: la tua sessione ti aspetta"
    corpo = f"""
      <p>Ciao {dest_nome}, oggi è il <b>giorno {giorno} di 7</b> del tuo percorso MAPS-CLEAR.</p>
      <p>Bastano <b>20 minuti</b>, con le tue cuffie, in un posto tranquillo.
      La costanza quotidiana è ciò che fa la differenza. 💪</p>
    """
    testo = (f"Ciao {dest_nome},\n\noggi è il giorno {giorno} di 7 del tuo percorso MAPS-CLEAR.\n"
             f"Bastano 20 minuti con le cuffie.\n\nI tuoi progressi: {magic_url}\n\n"
             f"Studio The Organism · pnev.it")
    html = _template(titolo, corpo, "▶ Vai alla sessione di oggi", magic_url)
    return _invia(api_key, mittente_email, mittente_nome,
                  dest_email, dest_nome, f"🎧 MAPS-CLEAR — Giorno {giorno}: la tua sessione", html, testo)


def invia_completamento(api_key, mittente_email, mittente_nome,
                        dest_email, dest_nome, magic_url):
    """Complimenti a percorso completato + invito a proseguire in studio."""
    titolo = "Hai completato i 7 giorni! 🏆"
    corpo = f"""
      <p>Complimenti {dest_nome}: hai portato a termine tutti i 7 giorni del percorso
      MAPS-CLEAR. Non era scontato, e l'hai fatto.</p>
      <p>Nel tuo report trovi l'andamento della tua fluenza giorno per giorno.</p>
      <p>Se il percorso ti è stato utile, il passo successivo è la <b>valutazione
      personalizzata in studio</b>: analizziamo la tua lateralità uditiva in modo
      approfondito e costruiamo un programma su misura.
      Rispondi a questa email o chiamaci per fissare un appuntamento.</p>
    """
    testo = (f"Complimenti {dest_nome}!\n\nHai completato i 7 giorni del percorso MAPS-CLEAR.\n"
             f"Il tuo report: {magic_url}\n\n"
             f"Per proseguire con una valutazione personalizzata in studio, "
             f"rispondi a questa email.\n\nStudio The Organism · pnev.it")
    html = _template(titolo, corpo, "🏆 Vedi il mio report", magic_url)
    return _invia(api_key, mittente_email, mittente_nome,
                  dest_email, dest_nome, "🏆 MAPS-CLEAR — percorso completato!", html, testo)
