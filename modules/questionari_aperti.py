# -*- coding: utf-8 -*-
"""🔗 Link aperti per i questionari.

Un link (o QR) senza dati del paziente, riutilizzabile. Chi lo apre compila prima una breve
scheda anagrafica e il consenso, poi il questionario. Il gestionale riconosce la persona:
- 🟢 certa (nome, cognome e data di nascita uguali, anche invertiti) → collega da solo
- 🟡 probabile (stessa data di nascita, nomi quasi uguali)           → casella d'arrivo
- 🟠 stessa famiglia (stesso telefono o email, persona diversa)       → casella d'arrivo
- ⚪ nuova                                                             → casella d'arrivo
Nella casella d'arrivo il clinico collega a un paziente esistente o crea la nuova anagrafica.
URL: <BASE_URL>/?q=<QUESTIONARIO>&qa=<token>
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import io
import json
import re
import secrets
import unicodedata

import streamlit as st

ESCLUSI = {"DIARIO_ALIM"}          # il diario si compila in più giorni: serve un paziente già noto
STATI = {"collegato_auto": "🟢 collegato in automatico", "da_verificare": "da verificare",
         "collegato": "✓ collegato", "nuovo_creato": "✓ nuovo paziente creato", "scartato": "scartato"}
ESITI = {"certo": "🟢 Stessa persona", "probabile": "🟡 Probabilmente la stessa",
         "famiglia": "🟠 Stessa famiglia (persona diversa?)", "nuovo": "⚪ Persona nuova",
         "doppio": "🟡 Più pazienti uguali in archivio"}


# ───────────────────────────── utilità database ─────────────────────────────
def _righe(conn, sql, par=()):
    try:
        c = conn.cursor(); c.execute(sql, par)
        nomi = [d[0] for d in c.description]
        return [r if isinstance(r, dict) else dict(zip(nomi, r)) for r in c.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
    try:
        c = conn.cursor(); c.execute(sql, par); conn.commit(); return None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def assicura_tabelle(conn):
    if _righe(conn, "SELECT 1 AS ok FROM information_schema.tables WHERE table_name='questionari_arrivo'"):
        # il link aperto non contiene dati: lo conserviamo per poterlo rivedere e rimandare
        _esegui(conn, "ALTER TABLE questionari_link_aperti ADD COLUMN IF NOT EXISTS token TEXT")
        return
    _esegui(conn, """CREATE TABLE IF NOT EXISTS questionari_link_aperti (
        id BIGSERIAL PRIMARY KEY, questionario TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL,
        etichetta TEXT, creato_il TIMESTAMPTZ DEFAULT now(), scade_il TIMESTAMPTZ,
        max_compilazioni INTEGER DEFAULT 0, compilazioni INTEGER DEFAULT 0, attivo BOOLEAN DEFAULT TRUE, token TEXT)""")
    _esegui(conn, """CREATE TABLE IF NOT EXISTS questionari_arrivo (
        id BIGSERIAL PRIMARY KEY, link_id BIGINT, questionario TEXT, anagrafica JSONB, risposte JSONB,
        riassunto TEXT, chiave_json TEXT, motivo TEXT, esito TEXT, candidati JSONB,
        paziente_id BIGINT, stato TEXT DEFAULT 'da_verificare', creato_il TIMESTAMPTZ DEFAULT now(),
        gestito_il TIMESTAMPTZ)""")


def _segreto():
    s = st.secrets.get("public_links", {}).get("TOKEN_SECRET") or st.secrets.get("privacy", {}).get("TOKEN_SECRET") or "pnev"
    return s.encode("utf-8")


def _hash(token):
    return hmac.new(_segreto(), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _base_url():
    return str(st.secrets.get("public_links", {}).get("BASE_URL", "")).rstrip("/")


def crea_link(conn, questionario, etichetta, giorni, max_comp):
    token = secrets.token_urlsafe(24)
    scade = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=int(giorni))
    err = _esegui(conn, "INSERT INTO questionari_link_aperti (questionario, token_hash, etichetta, scade_il, max_compilazioni, token) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", (questionario, _hash(token), etichetta, scade, int(max_comp or 0), token))
    return (None, err) if err else (url_link(questionario, token), None)


def url_link(questionario, token):
    return f"{_base_url()}/?q={questionario}&qa={token}"


def _mostra_invio(url, q, chiave):
    """Link pronto da copiare, QR da scaricare e invio WhatsApp."""
    st.code(url, language="text")
    img = _qr(url)
    c1, c2 = st.columns([1, 2])
    if img:
        c1.image(img, width=180)
        c2.download_button("⬇️ Scarica il QR (PNG)", img, file_name=f"QR_{q}.png", mime="image/png", key=f"qr_{chiave}")
    testo = f"Buongiorno, per la valutazione presso lo Studio The Organism può compilare questo questionario: {url}"
    c2.markdown(f"[📱 Manda su WhatsApp](https://wa.me/?text={testo.replace(' ', '%20')})")
    c2.caption("Per l'email: copia il link qui sopra (icona in alto a destra del riquadro) e incollalo nel messaggio.")


def valida(conn, token, questionario):
    r = _righe(conn, "SELECT * FROM questionari_link_aperti WHERE token_hash=%s AND questionario=%s", (_hash(token), questionario))
    if not r:
        return None
    r = r[0]
    scade = r.get("scade_il")
    if isinstance(scade, str):
        try:
            scade = dt.datetime.fromisoformat(scade.replace("Z", "+00:00"))
        except Exception:
            scade = None
    if not r.get("attivo") or (scade and dt.datetime.now(dt.timezone.utc) > scade):
        return None
    if (r.get("max_compilazioni") or 0) > 0 and (r.get("compilazioni") or 0) >= r["max_compilazioni"]:
        return None
    return r


# ───────────────────────────── riconoscimento della persona ─────────────────────────────
def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip()


def tel(s):
    d = re.sub(r"\D", "", str(s or ""))
    d = re.sub(r"^(0039|39)(?=\d{9,10}$)", "", d)
    return d[-10:] if len(d) >= 8 else ""


def _data(v):
    if not v:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v)[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except Exception:
            pass
    return None


def lev(a, b):
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 2:
        return 3
    p = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        c = [i]
        for j, cb in enumerate(b, 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (ca != cb)))
        p = c
    return p[-1]


def _simile(a, b):
    return a == b or (min(len(a), len(b)) >= 4 and lev(a, b) <= (1 if min(len(a), len(b)) < 7 else 2))


def riconosci(conn, ana):
    """Ritorna (esito, candidati). candidati = [{id, nome, motivo}] in ordine di somiglianza."""
    cog, nom, dn = norm(ana.get("cognome")), norm(ana.get("nome")), _data(ana.get("data_nascita"))
    t, em = tel(ana.get("telefono")), str(ana.get("email") or "").strip().lower()
    certi, probabili, famiglia = [], [], []
    for p in _righe(conn, "SELECT id, cognome, nome, data_nascita, telefono, email FROM pazienti"):
        pc, pn, pd = norm(p.get("cognome")), norm(p.get("nome")), _data(p.get("data_nascita"))
        etich = f"{(p.get('cognome') or '').upper()} {(p.get('nome') or '').upper()}" + (f" · {pd:%d/%m/%Y}" if pd else "")
        stessa_data = dn and pd and dn == pd
        if stessa_data and ({pc, pn} == {cog, nom}):
            certi.append({"id": p["id"], "nome": etich, "motivo": "nome, cognome e data di nascita uguali"}); continue
        if stessa_data and ((_simile(pc, cog) and _simile(pn, nom)) or (_simile(pc, nom) and _simile(pn, cog))):
            probabili.append({"id": p["id"], "nome": etich, "motivo": "stessa data di nascita, nome quasi uguale"}); continue
        stesso_tel = t and tel(p.get("telefono")) == t
        stessa_mail = em and str(p.get("email") or "").strip().lower() == em
        if stesso_tel or stessa_mail:
            famiglia.append({"id": p["id"], "nome": etich, "motivo": "stesso " + ("telefono" if stesso_tel else "indirizzo email")})
    if len(certi) == 1:
        return "certo", certi + probabili + famiglia
    if len(certi) > 1:
        return "doppio", certi + probabili + famiglia
    if probabili:
        return "probabile", probabili + famiglia
    if famiglia:
        return "famiglia", famiglia
    return "nuovo", []


# ───────────────────────────── salvataggio nell'anamnesi (come i link personali) ─────────────────────────────
def salva_in_anamnesi(cur, paziente_id, q_data, q_summary, chiave_json, motivo_label):
    import pnev_module as pnev
    cur.execute("SELECT id, pnev_json, pnev_summary FROM anamnesi WHERE paziente_id = %s ORDER BY data_anamnesi DESC, id DESC LIMIT 1",
                (paziente_id,))
    last = cur.fetchone()
    obj = {}
    if last:
        raw = last.get("pnev_json") if hasattr(last, "get") else last[1]
        if raw:
            obj = pnev.pnev_load(raw)
    obj.setdefault("questionari", {})
    obj["questionari"][chiave_json] = q_data
    dump = pnev.pnev_dump(obj)
    prev = ((last.get("pnev_summary") if hasattr(last, "get") else last[2]) or "") if last else ""
    summary = (prev.strip() + "\n" + q_summary).strip() if prev.strip() else q_summary
    if last:
        cur.execute("UPDATE anamnesi SET pnev_json = %s, pnev_summary = %s WHERE id = %s",
                    (dump, summary, int(last.get("id") if hasattr(last, "get") else last[0])))
    else:
        cur.execute("INSERT INTO anamnesi (paziente_id, data_anamnesi, motivo, storia, note, pnev_json, pnev_summary) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (paziente_id, dt.date.today().isoformat(), motivo_label, summary, "", dump, summary))


# ───────────────────────────── pagina pubblica: scheda anagrafica ─────────────────────────────
def scheda_anagrafica(prefisso="qa"):
    """Campi anagrafici prima del questionario. Ritorna il dizionario (validato all'invio)."""
    st.markdown("#### 1 · Chi compila e per chi")
    chi = st.radio("Chi compila il questionario?", ["Un genitore o tutore, per un figlio/a", "La persona stessa (adulto)"],
                   key=f"{prefisso}_chi", horizontal=True)
    genitore = chi.startswith("Un genitore")
    c1, c2 = st.columns(2)
    cognome = c1.text_input("Cognome " + ("del bambino/a" if genitore else ""), key=f"{prefisso}_cog")
    nome = c2.text_input("Nome " + ("del bambino/a" if genitore else ""), key=f"{prefisso}_nom")
    c3, c4 = st.columns(2)
    nascita = c3.date_input("Data di nascita", value=None, min_value=dt.date(1920, 1, 1), max_value=dt.date.today(),
                            format="DD/MM/YYYY", key=f"{prefisso}_dn")
    sesso = c4.selectbox("Sesso", ["", "F", "M"], key=f"{prefisso}_sx")
    gen_nome = st.text_input("Nome e cognome del genitore o tutore", key=f"{prefisso}_gen") if genitore else ""
    c5, c6, c7 = st.columns(3)
    telefono = c5.text_input("Telefono", key=f"{prefisso}_tel")
    email = c6.text_input("Email", key=f"{prefisso}_mail")
    citta = c7.text_input("Città di residenza", key=f"{prefisso}_citta")
    consenso = st.checkbox("Ho letto l'informativa privacy dello Studio The Organism e acconsento al trattamento dei dati, "
                           "anche relativi alla salute, per la valutazione clinica.", key=f"{prefisso}_cons")
    st.markdown("#### 2 · Questionario")
    return {"chi_compila": "genitore" if genitore else "paziente", "cognome": cognome.strip(), "nome": nome.strip(),
            "data_nascita": nascita.isoformat() if nascita else "", "sesso": sesso, "genitore": gen_nome.strip(),
            "telefono": telefono.strip(), "email": email.strip(), "citta": citta.strip(), "consenso": bool(consenso),
            "consenso_il": dt.datetime.now().isoformat(timespec="seconds") if consenso else ""}


def errori_anagrafica(a):
    e = []
    if not a.get("cognome") or not a.get("nome"):
        e.append("nome e cognome")
    if not a.get("data_nascita"):
        e.append("data di nascita")
    if not (tel(a.get("telefono")) or re.match(r"[^@\s]+@[^@\s]+\.[a-z]{2,}$", a.get("email") or "", re.I)):
        e.append("un telefono o un'email validi")
    if not a.get("consenso"):
        e.append("il consenso privacy")
    return e


def gestisci_invio(conn, link, q, ana, q_data, q_summary, chiave_json, motivo_label):
    """Riconosce la persona, collega da solo se è certa, altrimenti mette in casella d'arrivo."""
    esito, cand = riconosci(conn, ana)
    paz = cand[0]["id"] if esito == "certo" else None
    cur = conn.cursor()
    try:
        if paz:
            salva_in_anamnesi(cur, paz, q_data, q_summary, chiave_json, motivo_label)
        cur.execute("INSERT INTO questionari_arrivo (link_id, questionario, anagrafica, risposte, riassunto, chiave_json, motivo, "
                    "esito, candidati, paziente_id, stato, gestito_il) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (link["id"], q, json.dumps(ana), json.dumps(q_data, default=str), q_summary, chiave_json, motivo_label,
                     esito, json.dumps(cand), paz, "collegato_auto" if paz else "da_verificare",
                     dt.datetime.now(dt.timezone.utc) if paz else None))
        cur.execute("UPDATE questionari_link_aperti SET compilazioni = COALESCE(compilazioni,0) + 1 WHERE id = %s", (link["id"],))
        conn.commit()
        return None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


# ───────────────────────────── gestionale: link e casella d'arrivo ─────────────────────────────
def _questionari():
    try:
        from .app_core import _QUESTIONARI_PUBBLICI as Q
    except Exception:
        Q = {}
    return {k: v for k, v in Q.items() if k not in ESCLUSI}


def _qr(url):
    try:
        import qrcode
        b = io.BytesIO(); qrcode.make(url).save(b, format="PNG"); return b.getvalue()
    except Exception:
        return None


def _scheda_crea(conn):
    Q = _questionari()
    if not Q:
        st.error("Elenco dei questionari non disponibile."); return
    if not _base_url():
        st.warning("Manca `BASE_URL` nella sezione `[public_links]` dei Secrets: il link non avrebbe l'indirizzo giusto.")
    with st.form("qa_nuovo"):
        q = st.selectbox("Questionario", list(Q), format_func=lambda k: Q[k])
        etich = st.text_input("Nome del link (per riconoscerlo)", placeholder="Es. Primo contatto · Screening scuola Pagani")
        c1, c2 = st.columns(2)
        giorni = c1.number_input("Valido per (giorni)", 1, 365, 30)
        mx = c2.number_input("Numero massimo di compilazioni (0 = senza limite)", 0, 10000, 0)
        ok = st.form_submit_button("🔗 Crea il link aperto", type="primary")
    if ok:
        url, err = crea_link(conn, q, etich.strip() or Q[q], giorni, mx)
        if err:
            st.error(f"Link non creato: {err}")
        else:
            st.success("Link creato. Non contiene dati personali: puoi pubblicarlo, mandarlo o stamparlo come QR. "
                       "Lo ritrovi sempre nell'elenco qui sotto.")
            _mostra_invio(url, q, "nuovo")
    st.markdown("**Link aperti esistenti** · apri un link per copiarlo, scaricare il QR o mandarlo")
    for r in _righe(conn, "SELECT * FROM questionari_link_aperti ORDER BY attivo DESC, creato_il DESC LIMIT 50"):
        stato = "🟢 attivo" if r.get("attivo") else "⚪ disattivato"
        lim = f"/{r['max_compilazioni']}" if r.get("max_compilazioni") else ""
        nome_q = Q.get(r["questionario"], r["questionario"])
        with st.expander(f"{stato} · {r.get('etichetta') or nome_q} · {nome_q[:40]} · compilazioni {r.get('compilazioni') or 0}{lim} · "
                         f"scade {str(r.get('scade_il'))[:10]}"):
            st.caption(Q.get(r["questionario"], r["questionario"]))
            if r.get("token"):
                _mostra_invio(url_link(r["questionario"], r["token"]), r["questionario"], r["id"])
            else:
                st.info("Questo link è stato creato prima dell'aggiornamento e non si può più rivedere: "
                        "funziona ancora per chi lo ha già ricevuto. Se devi mandarlo ad altri, creane uno nuovo.")
            b1, b2 = st.columns(2)
            if r.get("attivo") and b1.button("Disattiva questo link", key=f"qa_off_{r['id']}"):
                _esegui(conn, "UPDATE questionari_link_aperti SET attivo = FALSE WHERE id = %s", (r["id"],)); st.rerun()
            if b2.button("🗑️ Elimina questo link", key=f"qa_del_{r['id']}"):
                st.session_state["qa_conferma_del"] = r["id"]
            if st.session_state.get("qa_conferma_del") == r["id"]:
                st.warning("Eliminare definitivamente questo link? Chi lo ha ricevuto non potrà più usarlo. "
                           "I questionari già arrivati restano nell'archivio.")
                k1, k2 = st.columns(2)
                if k1.button("Sì, elimina", key=f"qa_del_si_{r['id']}", type="primary"):
                    _esegui(conn, "DELETE FROM questionari_link_aperti WHERE id = %s", (r["id"],))
                    st.session_state.pop("qa_conferma_del", None); st.rerun()
                if k2.button("No", key=f"qa_del_no_{r['id']}"):
                    st.session_state.pop("qa_conferma_del", None); st.rerun()


def _crea_paziente(conn, ana, mod):
    r = _righe(conn, "INSERT INTO pazienti (cognome, nome, data_nascita, sesso, telefono, email, citta, stato_paziente) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,'ATTIVO') RETURNING id",
               (mod["cognome"].upper(), mod["nome"].upper(), mod["data_nascita"] or None, mod["sesso"] or None,
                mod["telefono"], mod["email"], mod["citta"]))
    try:
        conn.commit()
    except Exception:
        pass
    return r[0]["id"] if r else None


def _collega(conn, arr, paz_id, stato):
    cur = conn.cursor()
    try:
        ris = arr["risposte"] if isinstance(arr["risposte"], dict) else json.loads(arr["risposte"] or "{}")
        salva_in_anamnesi(cur, paz_id, ris, arr.get("riassunto") or "", arr["chiave_json"], arr["motivo"])
        cur.execute("UPDATE questionari_arrivo SET paziente_id=%s, stato=%s, gestito_il=now() WHERE id=%s", (paz_id, stato, arr["id"]))
        conn.commit(); return None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _scheda_arrivo(conn):
    Q = _questionari()
    lista = _righe(conn, "SELECT * FROM questionari_arrivo WHERE stato='da_verificare' ORDER BY creato_il")
    if not lista:
        st.success("Nessun questionario da verificare. Quelli riconosciuti con certezza sono già nelle schede dei pazienti.")
        return
    for a in lista:
        ana = a["anagrafica"] if isinstance(a["anagrafica"], dict) else json.loads(a["anagrafica"] or "{}")
        cand = a["candidati"] if isinstance(a["candidati"], list) else json.loads(a["candidati"] or "[]")
        dn = _data(ana.get("data_nascita"))
        titolo = (f"{ESITI.get(a['esito'], a['esito'])} · {ana.get('cognome','').upper()} {ana.get('nome','').upper()}"
                  f"{' · ' + dn.strftime('%d/%m/%Y') if dn else ''} · {Q.get(a['questionario'], a['questionario'])} · {str(a['creato_il'])[:10]}")
        with st.expander(titolo):
            st.caption(f"Compilato da: {'genitore ' + ana.get('genitore','') if ana.get('chi_compila') == 'genitore' else 'la persona stessa'} · "
                       f"tel. {ana.get('telefono') or '—'} · {ana.get('email') or '—'} · {ana.get('citta') or '—'} · consenso {ana.get('consenso_il') or 'no'}")
            for c in cand:
                k1, k2 = st.columns([4, 1])
                k1.write(f"**{c['nome']}** — {c['motivo']}")
                if k2.button("Collega", key=f"qa_col_{a['id']}_{c['id']}"):
                    err = _collega(conn, a, c["id"], "collegato")
                    st.error(err) if err else st.rerun()
            st.markdown(("**Oppure crea un nuovo paziente**" if cand else "**Crea il nuovo paziente**") + " (controlla i dati):")
            with st.form(f"qa_nuovo_paz_{a['id']}"):
                c1, c2, c3 = st.columns(3)
                mod = {"cognome": c1.text_input("Cognome", ana.get("cognome", "")), "nome": c2.text_input("Nome", ana.get("nome", "")),
                       "data_nascita": (c3.date_input("Data di nascita", dn, format="DD/MM/YYYY") or "").__str__(),
                       "sesso": ana.get("sesso", ""), "telefono": ana.get("telefono", ""), "email": ana.get("email", ""), "citta": ana.get("citta", "")}
                b1, b2 = st.columns(2)
                crea = b1.form_submit_button("➕ Crea il paziente e collega", type="primary")
                scarta = b2.form_submit_button("🗑️ Scarta (compilazione non valida)")
            if crea:
                if not mod["cognome"].strip() or not mod["nome"].strip():
                    st.error("Servono nome e cognome.")
                else:
                    pid = _crea_paziente(conn, ana, mod)
                    err = _collega(conn, a, pid, "nuovo_creato") if pid else "paziente non creato"
                    st.error(err) if err else st.rerun()
            if scarta:
                _esegui(conn, "UPDATE questionari_arrivo SET stato='scartato', gestito_il=now() WHERE id=%s", (a["id"],)); st.rerun()


def _scheda_archivio(conn):
    Q = _questionari()
    for a in _righe(conn, "SELECT a.*, p.cognome AS p_cog, p.nome AS p_nom FROM questionari_arrivo a "
                          "LEFT JOIN pazienti p ON p.id = a.paziente_id WHERE a.stato <> 'da_verificare' "
                          "ORDER BY a.creato_il DESC LIMIT 100"):
        ana = a["anagrafica"] if isinstance(a["anagrafica"], dict) else json.loads(a["anagrafica"] or "{}")
        chi = f"{(a.get('p_cog') or '').upper()} {(a.get('p_nom') or '').upper()}".strip() or f"{ana.get('cognome','')} {ana.get('nome','')}"
        st.caption(f"{str(a['creato_il'])[:16]} · {Q.get(a['questionario'], a['questionario'])} · {chi} · {STATI.get(a['stato'], a['stato'])}")


def render_link_aperti(conn):
    st.header("🔗 Link aperti e questionari in arrivo")
    if conn is None:
        st.info("Database non disponibile."); return
    assicura_tabelle(conn)
    n = len(_righe(conn, "SELECT id FROM questionari_arrivo WHERE stato='da_verificare'"))
    t = st.tabs([f"📥 Da verificare ({n})", "🔗 Crea link aperto", "📜 Archivio"])
    with t[0]:
        _scheda_arrivo(conn)
    with t[1]:
        _scheda_crea(conn)
    with t[2]:
        _scheda_archivio(conn)
