#!/usr/bin/env node
/*
 * scripts/offusca_giochi.mjs — prepara i giochi PNEV per la pubblicazione
 *
 * Prende la cartella dei giochi IN CHIARO (master su Dropbox: «PNEV giochi/1 - non offuscati (master)»)
 * e scrive la versione da pubblicare:
 *   - offusca il JavaScript (script dentro le pagine e file .js);
 *   - BLOCCO DEL DOMINIO: il codice funziona solo su giochi.pnev.it, pnev.it e sul server del gestionale;
 *     una copia aperta altrove viene rimandata a www.pnev.it;
 *   - aggiunge l'avviso di copyright in testa a ogni pagina;
 *   - i file già offuscati vengono copiati così come sono (niente doppio offuscamento).
 *
 * Uso:  npm install javascript-obfuscator@4
 *       node scripts/offusca_giochi.mjs <cartella_in_chiaro> <cartella_uscita>
 *
 * I file in chiaro NON vanno mai messi nel repository (è pubblico): si tengono solo su Dropbox.
 */
import fs from 'node:fs';
import path from 'node:path';
import JavaScriptObfuscator from 'javascript-obfuscator';

const [, , IN, OUT] = process.argv;
if (!IN || !OUT) { console.error('Uso: node offusca_giochi.mjs <in_chiaro> <uscita>'); process.exit(1); }

const DOMINI = (process.env.PNEV_DOMINI ||
  'giochi.pnev.it,.pnev.it,pnev.it,.theorganism.it,giochi.91-134-106-98.sslip.io,.91-134-106-98.sslip.io')
  .split(',').map(s => s.trim()).filter(Boolean);

const COPYRIGHT = '© 2026 Giuseppe Ferraioli — Metodo PNEV · www.pnev.it — tutti i diritti riservati. ' +
  'Riproduzione, copia e uso fuori da pnev.it non autorizzati.';

const OPZIONI = {
  compact: true,
  domainLock: DOMINI,
  domainLockRedirectUrl: 'https://www.pnev.it',
  stringArray: true,
  stringArrayEncoding: ['base64'],
  stringArrayThreshold: 0.75,
  identifierNamesGenerator: 'hexadecimal',
  renameGlobals: false,          // le pagine chiamano funzioni globali dagli attributi onclick
  selfDefending: false,          // più sicuro per la compatibilità con Safari/iPad
  controlFlowFlattening: false,  // giochi in tempo reale: niente rallentamenti
  deadCodeInjection: false,
  transformObjectKeys: false,
};

const giaOffuscato = s => (s.match(/_0x[0-9a-f]{4,}/g) || []).length > 200;
const offusca = js => JavaScriptObfuscator.obfuscate(js, OPZIONI).getObfuscatedCode();

let stat = { offuscati: 0, copiati: 0, errori: 0 };

function trattaHtml(src) {
  let s = fs.readFileSync(src, 'utf8');
  if (giaOffuscato(s)) { stat.copiati++; return s; }
  s = s.replace(/<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/gi, (m, attr, code) => {
    if (!code.trim() || /type\s*=\s*["']?(application\/(ld\+)?json|text\/template)/i.test(attr)) return m;
    return `<script${attr}>${offusca(code)}</script>`;
  });
  s = s.replace(/<!DOCTYPE html>/i, d => `${d}\n<!-- ${COPYRIGHT} -->`);
  stat.offuscati++;
  return s;
}

function trattaJs(src) {
  const s = fs.readFileSync(src, 'utf8');
  if (giaOffuscato(s)) { stat.copiati++; return s; }
  stat.offuscati++;
  return `/* ${COPYRIGHT} */\n` + offusca(s);
}

function giro(dirIn, dirOut) {
  fs.mkdirSync(dirOut, { recursive: true });
  for (const e of fs.readdirSync(dirIn, { withFileTypes: true })) {
    const a = path.join(dirIn, e.name), b = path.join(dirOut, e.name);
    if (e.isDirectory()) { giro(a, b); continue; }
    try {
      if (/\.html?$/i.test(e.name)) fs.writeFileSync(b, trattaHtml(a));
      else if (/\.js$/i.test(e.name)) fs.writeFileSync(b, trattaJs(a));
      else { fs.copyFileSync(a, b); stat.copiati++; }
    } catch (err) {
      stat.errori++;
      console.error(`ERRORE ${a}: ${err.message}`);
    }
  }
}

giro(IN, OUT);
console.log(`Fatto: ${stat.offuscati} offuscati, ${stat.copiati} copiati così come sono, ${stat.errori} errori.`);
console.log(`Domini autorizzati: ${DOMINI.join(', ')}`);
if (stat.errori) process.exit(2);
