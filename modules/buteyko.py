# -*- coding: utf-8 -*-
"""Respirazione · metodo Buteyko.

Due pezzi:
  · Valutazione e programma: l'app HTML static_protocollo/Buteyko_MASTER.html
    (Pausa Controllo, questionari, programma esercizi, dispense), montata con
    render_protocollo_pdf_app come gli altri protocolli. Si salva nel
    fascicolo (tabella screening_esterni, dati->'V'->>'_app' = 'buteyko').
  · Diario della Pausa Controllo: tabella buteyko_diario. Il paziente riceve
    un link personale (?diario=TOKEN, senza login) e ogni mattina segna la
    Pausa Controllo e gli esercizi fatti; in studio si vede il grafico.

Collegamento con gli altri moduli: all'app HTML arrivano (window.PNEV_FASCICOLO)
respirazione e sonno dell'anamnesi, il TRMR dell'ultima valutazione del
frenulo e le ultime misure del diario.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import urllib.parse

import streamlit as st

ESERCIZI = json.loads(r'''[{"id":"naso","nome":"Liberare il naso","come":"Seduto o in piedi, inspira ed espira piano dal naso. Dopo l'espirazione tappa il naso con le dita e cammina (o annuisci con la testa, se sei seduto) trattenendo il respiro finché senti una fame d'aria da moderata a forte. Lascia il naso e respira solo dal naso, con calma: in 30–60 secondi il respiro deve tornare tranquillo. Aspetta un minuto e ripeti.","dose":"5–6 ripetizioni, quando il naso è chiuso","cautela":"Con le precauzioni attive: solo fame d'aria lieve, poche ripetizioni, mai fino al disagio."},{"id":"leggera","nome":"Respirare leggero","come":"Seduto con la schiena dritta e le spalle rilassate. Respira dal naso e riduci a poco a poco la quantità d'aria, senza trattenere il respiro, finché senti una lieve fame d'aria, tollerabile. Mantienila per 4 minuti, poi riposa un minuto respirando normalmente. Varianti: A · una mano sul petto e una sulla pancia, per sentire il respiro scendere; B · mani a coppa davanti a naso e bocca, per sentire l'aria più calda e umida; C · un dito sotto le narici, per sentire appena il flusso; D · ritmata, contando i tempi di inspirazione ed espirazione.","dose":"4 minuti + 1 di pausa, 3–4 cicli · 2 volte al giorno","cautela":""},{"id":"lento","nome":"Respirare lento e basso","come":"Respira dal naso, portando l'aria verso la pancia e non verso il petto. Rallenta fino a circa 6 respiri al minuto: inspira in 4 secondi, espira in 6, senza forzare la quantità d'aria. Se arriva un sospiro, lascialo passare senza prendere un respiro grande.","dose":"5 minuti · 2–3 volte al giorno e quando sale l'agitazione","cautela":""},{"id":"cammina","nome":"Camminare con la bocca chiusa","come":"Cammina respirando solo dal naso. Se senti di dover aprire la bocca, rallenta il passo finché il naso basta. Poco a poco si potrà camminare più veloce con la bocca chiusa.","dose":"Ogni camminata, 10–20 minuti al giorno","cautela":""},{"id":"passi10","nome":"Apnee brevi in camminata (fino a 10 passi)","come":"Dopo un'espirazione normale tappa il naso e cammina da 2 a 10 passi, poi lascia il naso e respira normalmente per circa 30 secondi. È la versione leggera dell'apnea in camminata: adatta ai bambini e a chi ha una Pausa Controllo bassa.","dose":"10 ripetizioni · 1 volta al giorno","cautela":""},{"id":"apnea_cam","nome":"Apnea in camminata","come":"Dopo un'espirazione normale tappa il naso e cammina contando i passi, fino a una fame d'aria da moderata a forte. Lascia il naso, respira dal naso e calma il respiro entro poche respirazioni. Annota i passi: l'obiettivo, nelle settimane, è arrivare a 80–100.","dose":"6–10 ripetizioni, a 1 minuto di distanza · solo con Pausa Controllo ≥ 20 s","cautela":"Da non fare con le precauzioni attive."},{"id":"corsa","nome":"Fame d'aria in corsa","come":"Durante una corsa leggera, respirando dal naso: espira normalmente e trattieni il respiro per 10–15 passi, poi riprendi a respirare dal naso per circa un minuto. Simula l'allenamento in quota.","dose":"8–10 ripetizioni durante una corsa leggera · solo con Pausa Controllo ≥ 25 s","cautela":"Da non fare con le precauzioni attive. Mai in acqua."},{"id":"apnee_brevi","nome":"Molte apnee brevi","come":"Espira normalmente, trattieni il respiro per 2–5 secondi, poi respira normalmente per circa 10 secondi. Ripeti finché il sintomo si calma. Serve a fermare l'aumento del respiro che alimenta tosse, sibilo e panico.","dose":"Per qualche minuto, ai primi segni di tosse, sibilo, affanno o agitazione","cautela":"Nell'asma i farmaci di soccorso restano quelli indicati dal medico."},{"id":"sospiri","nome":"Fermare sospiri e sbadigli","come":"Quando senti salire un sospiro o uno sbadiglio, deglutisci oppure trattieni il respiro per qualche secondo, invece di prendere una boccata d'aria. I sospiri frequenti mantengono il respiro eccessivo.","dose":"Ogni volta che arriva un sospiro","cautela":""},{"id":"sera","nome":"Respiro della sera","come":"A letto, prima di dormire, senza schermi: respirazione leggera e lenta dal naso. Meglio sul fianco che a pancia in su.","dose":"15–20 minuti a letto, ogni sera","cautela":""},{"id":"cerotto","nome":"Bocca chiusa di notte (cerotto)","come":"Si usa un cerotto di carta specifico per le labbra (per esempio MyoTape), che tiene le labbra unite ma lascia la bocca libera di aprirsi. Prima si prova di giorno per 20 minuti, poi si usa di notte.","dose":"Ogni notte, dopo la prova di giorno","cautela":"Non usarlo con il naso chiuso, nausea o vomito, dopo alcol o sedativi. Sotto i 5 anni solo su indicazione del clinico. Con apnee notturne diagnosticate, solo dopo aver sentito il medico del sonno."},{"id":"giochi","nome":"Giochi di respiro (bambini)","come":"Il respiro del topolino: respirare così piano che un topolino vicino al naso non se ne accorga. La sfida dei passi: quanti passi riesci a fare con il naso tappato, segnando il record su un foglio. Le camminate a bocca chiusa, contando chi resiste di più.","dose":"5–10 minuti al giorno, come un gioco","cautela":""}]''')
_ES = {e["id"]: e for e in ESERCIZI}
GIORNI_LINK = 120


# ── database ──────────────────────────────────────────────────────────

def _assicura(conn):
    if st.session_state.get("_bty_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS buteyko_diario ("
            " id BIGSERIAL PRIMARY KEY,"
            " paziente_id BIGINT NOT NULL,"
            " data DATE NOT NULL,"
            " bolt INTEGER,"
            " polso INTEGER,"
            " benessere INTEGER,"
            " esercizi JSONB,"
            " minuti INTEGER,"
            " note TEXT,"
            " fonte TEXT DEFAULT 'casa',"
            " creato_il TIMESTAMPTZ DEFAULT now())")
        cur.execute("CREATE INDEX IF NOT EXISTS buteyko_diario_paz ON buteyko_diario (paziente_id, data)")
        conn.commit()
        st.session_state["_bty_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        righe = cur.fetchall() or []
        if righe and not isinstance(righe[0], dict):
            nomi = [c[0] for c in cur.description]
            righe = [dict(zip(nomi, r)) for r in righe]
        return righe
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        conn.commit()
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _json(x):
    if isinstance(x, dict):
        return x
    try:
        return json.loads(x) if x else {}
    except Exception:
        return {}


def ultima_valutazione(conn, pid) -> dict:
    r = _q(conn, "SELECT dati, creato_il FROM screening_esterni WHERE paziente_id=%s "
                 "AND dati->'V'->>'_app'='buteyko' ORDER BY id DESC LIMIT 1", (int(pid),))
    if not r:
        return {}
    v = _json(r[0].get("dati")).get("V") or {}
    v["_salvata_il"] = r[0].get("creato_il")
    return v


def programma(v: dict) -> list[dict]:
    out = []
    for e in ESERCIZI:
        if v.get("pr_" + e["id"]):
            out.append({**e, "minuti": v.get(f"pr_{e['id']}_min") or "",
                        "volte": v.get(f"pr_{e['id']}_volte") or "",
                        "nota": v.get(f"pr_{e['id']}_note") or ""})
    return out


def diario(conn, pid, giorni=None):
    _assicura(conn)
    sql = "SELECT * FROM buteyko_diario WHERE paziente_id=%s"
    par = [int(pid)]
    if giorni:
        sql += " AND data >= %s"
        par.append(dt.date.today() - dt.timedelta(days=giorni))
    return _q(conn, sql + " ORDER BY data, id", tuple(par))


def _trmr_frenulo(conn, pid):
    r = _q(conn, "SELECT dati, creato_il FROM screening_esterni WHERE paziente_id=%s "
                 "AND dati->'V'->>'fr_a1' IS NOT NULL ORDER BY id DESC LIMIT 1", (int(pid),))
    if not r:
        return None
    v = _json(r[0].get("dati")).get("V") or {}
    a, b = [], []
    for i in (1, 2, 3):
        try:
            x, y = float(str(v.get(f"fr_a{i}")).replace(",", ".")), float(str(v.get(f"fr_b{i}")).replace(",", "."))
            if x > 0:
                a.append(x); b.append(y)
        except Exception:
            pass
    if not a:
        return None
    rr = (sum(b) / len(b)) / (sum(a) / len(a)) * 100
    gr = 1 if rr > 80 else 2 if rr >= 50 else 3 if rr >= 25 else 4
    d = r[0].get("creato_il")
    return {"r": round(rr), "grado": gr, "data": d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else ""}


def dal_fascicolo(conn, pid) -> dict:
    f = {}
    try:
        from .anamnesi_sviluppo import carica_anamnesi_sviluppo
        sv = carica_anamnesi_sviluppo(conn, pid) or {}
        f["respirazione"] = list(sv.get("respirazione") or [])
        f["sonno_qualita"] = list(sv.get("sonno_qualita") or [])
        f["sonno"] = sv.get("sonno") or ""
    except Exception:
        pass
    try:
        f["trmr"] = _trmr_frenulo(conn, pid)
    except Exception:
        pass
    f["bolt"] = [{"data": r["data"].strftime("%d/%m"), "bolt": r["bolt"], "fonte": r.get("fonte")}
                 for r in diario(conn, pid) if r.get("bolt")][-10:]
    return f


# ── link personale del diario ─────────────────────────────────────────

def _sec(nome):
    try:
        return st.secrets.get(nome, {}) or {}
    except Exception:
        return {}


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _segreto() -> bytes:
    s = _sec("public_links").get("TOKEN_SECRET") or _sec("privacy").get("TOKEN_SECRET")
    if not s:
        raise RuntimeError("manca [public_links] TOKEN_SECRET nei Secrets")
    return str(s).encode()


def crea_link(pid) -> str:
    raw = json.dumps({"pid": int(pid), "k": "diario",
                      "exp": int(dt.datetime.utcnow().timestamp()) + GIORNI_LINK * 86400},
                     separators=(",", ":")).encode()
    tok = _b64(raw) + "." + _b64(hmac.new(_segreto(), raw, hashlib.sha256).digest())
    base = (_sec("public_links").get("BASE_URL") or _sec("app").get("BASE_URL") or "").rstrip("/")
    if not base:
        raise RuntimeError("manca [public_links] BASE_URL nei Secrets")
    return f"{base}/?diario={urllib.parse.quote(tok)}"


def leggi_token(tok: str):
    try:
        p, f = tok.split(".", 1)
        raw = _unb64(p)
        if not hmac.compare_digest(_unb64(f), hmac.new(_segreto(), raw, hashlib.sha256).digest()):
            return None, "link non valido"
        d = json.loads(raw)
        if d.get("k") != "diario":
            return None, "link non valido"
        if int(d.get("exp", 0)) < dt.datetime.utcnow().timestamp():
            return None, "link scaduto: chiedi allo studio quello nuovo"
        return int(d["pid"]), ""
    except Exception:
        return None, "link non valido"


# ── gestionale: valutazione e programma ───────────────────────────────

def render_buteyko(conn, paz_id):
    extra = ""
    if conn is not None and paz_id:
        try:
            dati = json.dumps(dal_fascicolo(conn, paz_id), ensure_ascii=False, default=str)
            extra = "<script>window.PNEV_FASCICOLO=" + dati.replace("</", "<\\/") + ";</script>"
        except Exception:
            extra = ""
    from .ui_protocollo_pdf_app import render_protocollo_pdf_app
    render_protocollo_pdf_app(
        conn, paz_id,
        html_file="Buteyko_MASTER.html",
        pdf_file="Buteyko_scheda.pdf",
        titolo="🫁 Respirazione · metodo Buteyko",
        sottotitolo="Pausa Controllo, questionari (Buteyko Clinic, Nijmegen, Epworth, SDSC, PSQ, BEARS), "
                    "programma di esercizi e dispense su carta intestata.",
        kp="bty", extra_js=extra)


# ── gestionale: diario ────────────────────────────────────────────────

def _grafico(righe):
    import pandas as pd
    dati = [{"data": r["data"], "Pausa Controllo (s)": r["bolt"]} for r in righe if r.get("bolt")]
    if not dati:
        st.caption("Ancora nessuna Pausa Controllo registrata.")
        return
    df = pd.DataFrame(dati).groupby("data").max()
    st.line_chart(df, height=260)


def render_diario(conn, paz_id):
    st.subheader("📈 Diario della Pausa Controllo")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _assicura(conn)
    v = ultima_valutazione(conn, paz_id)
    prog = programma(v)
    righe = diario(conn, paz_id)

    misure = [r for r in righe if r.get("bolt")]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prima misura", f"{misure[0]['bolt']} s" if misure else "—")
    ultima = misure[-1]["bolt"] if misure else None
    c2.metric("Ultima", f"{ultima} s" if ultima else "—",
              delta=(f"{ultima - misure[0]['bolt']:+d} s" if len(misure) > 1 else None))
    ult14 = {r["data"] for r in righe if r["data"] >= dt.date.today() - dt.timedelta(days=13)}
    c3.metric("Giorni registrati (ultimi 14)", len(ult14))
    c4.metric("Obiettivo", f"{v.get('pr_obiettivo')} s" if v.get("pr_obiettivo") else "—")
    _grafico(righe)

    with st.expander("📋 Programma assegnato", expanded=not righe):
        if not prog:
            st.caption("Nessun programma salvato: si prepara in «🫁 Valutazione e programma Buteyko» "
                       "(scheda 4) e si salva nel fascicolo.")
        for e in prog:
            dose = ", ".join(x for x in (f"{e['minuti']} min" if e["minuti"] else "",
                                         f"{e['volte']} volte al giorno" if e["volte"] else "") if x) or e["dose"]
            st.markdown(f"**{e['nome']}** · {dose}" + (f"  \n_{e['nota']}_" if e["nota"] else ""))

    st.markdown("**🔗 Link per il paziente**")
    st.caption(f"Personale, vale {GIORNI_LINK} giorni. Dal telefono segna ogni mattina la Pausa Controllo "
               "e gli esercizi fatti; i dati arrivano qui.")
    try:
        from .privacy.firma_remota import email_paziente, nome_paziente, _invia
    except Exception:
        email_paziente = nome_paziente = _invia = None
    k = f"bty_mail_{paz_id}"
    if k not in st.session_state and email_paziente:
        st.session_state[k] = email_paziente(conn, paz_id)
    a, b = st.columns([3, 2])
    mail = a.text_input("Email", key=k)
    b.write(""); b.write("")
    if b.button("📧 Invia il link del diario", key=f"bty_inv_{paz_id}", type="primary", use_container_width=True):
        try:
            url = crea_link(paz_id)
            nome = nome_paziente(conn, paz_id) if nome_paziente else ""
            corpo = (f"Gentile {nome or 'cliente'},\n\nquesto è il link al tuo diario del respiro. "
                     "Aprilo ogni mattina dal telefono, misura la Pausa Controllo e segna gli esercizi fatti: "
                     f"li vediamo anche noi in studio.\n\n{url}\n\nConviene salvarlo tra i preferiti o "
                     "aggiungerlo alla schermata Home.\n\nStudio The Organism · www.pnev.it")
            ok, motivo = _invia(mail.strip(), "Il tuo diario del respiro — Studio The Organism", corpo) if _invia else (False, "modulo email non disponibile")
            (st.success if ok else st.error)(motivo if not ok else f"Link inviato a {mail.strip()}.")
            st.session_state[f"bty_url_{paz_id}"] = url
        except Exception as e:
            st.error(str(e))
    with st.expander("Copia il link o mandalo su WhatsApp"):
        if st.button("Genera il link", key=f"bty_gen_{paz_id}"):
            try:
                st.session_state[f"bty_url_{paz_id}"] = crea_link(paz_id)
            except Exception as e:
                st.error(str(e))
        u = st.session_state.get(f"bty_url_{paz_id}")
        if u:
            st.code(u, language=None)
            st.markdown("[Apri WhatsApp con il messaggio pronto](https://wa.me/?text="
                        + urllib.parse.quote("Il tuo diario del respiro: " + u) + ")")

    with st.expander("➕ Aggiungi una misura fatta in studio"):
        with st.form(f"bty_studio_{paz_id}", clear_on_submit=True):
            x, y, z = st.columns(3)
            d = x.date_input("Data", dt.date.today(), format="DD/MM/YYYY")
            bt = y.number_input("Pausa Controllo (s)", 0, 180, 0)
            po = z.number_input("Polso", 0, 220, 0)
            no = st.text_input("Note")
            if st.form_submit_button("Salva misura"):
                err = _esegui(conn, "INSERT INTO buteyko_diario (paziente_id, data, bolt, polso, note, fonte) "
                                    "VALUES (%s,%s,%s,%s,%s,'studio')",
                              (int(paz_id), d, int(bt) or None, int(po) or None, no.strip()))
                st.error(err) if err else st.rerun()

    if righe:
        st.markdown("**Registrazioni**")
        for r in reversed(righe[-30:]):
            fatti = [(_ES.get(i) or {}).get("nome", i) for i in (_json(r.get("esercizi")) if isinstance(r.get("esercizi"), str) else (r.get("esercizi") or []))]
            parti = [r["data"].strftime("%d/%m/%Y"), "🏥 studio" if r.get("fonte") == "studio" else "🏠 casa"]
            if r.get("bolt"): parti.append(f"**{r['bolt']} s**")
            if r.get("polso"): parti.append(f"polso {r['polso']}")
            if r.get("benessere") is not None: parti.append(f"benessere {r['benessere']}/10")
            if r.get("minuti"): parti.append(f"{r['minuti']} min di esercizi")
            st.markdown(" · ".join(parti) + (f"  \n<small>{', '.join(fatti)}</small>" if fatti else "")
                        + (f"  \n<small>📝 {r['note']}</small>" if r.get("note") else ""), unsafe_allow_html=True)


# ── pagina pubblica per il paziente ───────────────────────────────────

_CRONO = """<div style="font-family:system-ui,sans-serif;text-align:center;padding:6px">
<div id="t" style="font:600 46px ui-monospace,Menlo,monospace;color:#12385f">0</div>
<button id="b" style="font:600 18px system-ui;padding:14px 30px;border:0;border-radius:10px;background:#1D6B44;color:#fff;width:100%">▶ Avvia</button>
<script>var t0=null,i=null,b=document.getElementById('b'),t=document.getElementById('t');
b.onclick=function(){ if(!t0){t0=Date.now();b.textContent='■ Ferma';b.style.background='#8a1c1c';i=setInterval(function(){t.textContent=Math.floor((Date.now()-t0)/1000)},200);}
else{clearInterval(i);t.textContent=Math.round((Date.now()-t0)/1000)+' s';t0=null;b.textContent='▶ Avvia di nuovo';b.style.background='#1D6B44';}};</script></div>"""


def render_diario_pubblico(conn, tok):
    try:
        from .privacy.firma_remota import css_telefono, nome_paziente
        css_telefono()
    except Exception:
        nome_paziente = None
    st.markdown("#### Studio The Organism")
    st.title("🫁 Il mio diario del respiro")
    pid, err = leggi_token(tok or "")
    if not pid:
        st.error(err)
        st.stop()
    _assicura(conn)
    nome = nome_paziente(conn, pid) if nome_paziente else ""
    if nome:
        st.caption(f"Diario di **{nome}**")
    v = ultima_valutazione(conn, pid)
    prog = programma(v)
    oggi = dt.date.today()
    gia = [r for r in diario(conn, pid, 1) if r["data"] == oggi and r.get("fonte") == "casa"]

    st.markdown("**1 · Misura la Pausa Controllo**")
    st.caption("Seduto, a riposo. Inspira ed espira normalmente dal naso. Dopo l'espirazione tappa il naso, "
               "premi Avvia e ferma al primo desiderio di respirare: non resistere. Poi respira calmo dal naso.")
    import streamlit.components.v1 as components
    components.html(_CRONO, height=150)

    if gia:
        st.success(f"Oggi hai già registrato: Pausa Controllo {gia[-1].get('bolt') or '—'} s. "
                   "Puoi aggiungere un'altra registrazione se vuoi.")
    with st.form("bty_pub", clear_on_submit=True):
        bt = st.number_input("Pausa Controllo (secondi)", 0, 180, 0)
        st.markdown("**2 · Gli esercizi di oggi**")
        fatti = [e["id"] for e in prog if st.checkbox(e["nome"], key=f"pub_{e['id']}")] if prog else []
        if not prog:
            st.caption("Il programma degli esercizi te lo assegna lo studio alla prossima visita.")
        minuti = st.number_input("Minuti di esercizi in tutto", 0, 300, 0)
        st.markdown("**3 · Come stai oggi**")
        ben = st.select_slider("0 = molto male · 10 = benissimo", options=list(range(11)), value=5)
        note = st.text_area("Note (sintomi, notte, naso chiuso…)", height=80)
        if st.form_submit_button("💾 Salva", type="primary"):
            if not bt and not fatti and not note.strip():
                st.error("Inserisci almeno la Pausa Controllo, un esercizio o una nota.")
            else:
                e2 = _esegui(conn, "INSERT INTO buteyko_diario (paziente_id, data, bolt, benessere, esercizi, minuti, note, fonte) "
                                   "VALUES (%s,%s,%s,%s,%s,%s,%s,'casa')",
                             (pid, oggi, int(bt) or None, int(ben), json.dumps(fatti), int(minuti) or None, note.strip()))
                if e2:
                    st.error("Non salvato, riprova tra poco.")
                else:
                    st.success("Salvato ✓ A domani!")

    righe = diario(conn, pid, 30)
    if any(r.get("bolt") for r in righe):
        st.markdown("**I tuoi progressi · ultimi 30 giorni**")
        _grafico(righe)
        if v.get("pr_obiettivo"):
            st.caption(f"Obiettivo: {v.get('pr_obiettivo')} secondi.")

    if prog:
        st.markdown("**Come si fanno gli esercizi**")
        for e in prog:
            with st.expander(e["nome"]):
                dose = ", ".join(x for x in (f"{e['minuti']} minuti" if e["minuti"] else "",
                                             f"{e['volte']} volte al giorno" if e["volte"] else "") if x) or e["dose"]
                st.write(e["come"])
                st.caption("Quanto: " + dose)
                if e.get("cautela"):
                    st.warning(e["cautela"])
                if e.get("nota"):
                    st.info(e["nota"])
    st.caption("Se un esercizio ti dà disagio, fermati e respira normalmente dal naso. "
               "Per qualsiasi dubbio scrivi a apstheorganism@gmail.com.")
