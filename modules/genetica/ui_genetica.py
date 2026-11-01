"""
Modulo Genetica PNEV · interfaccia Streamlit.

Uso nel gestionale:
    from modules.genetica.ui_genetica import render_genetica
    render_genetica(conn, paziente_id, paziente_nome, studio_id)

Con conn=None il modulo funziona in modalità DEMO (dati solo in memoria, nulla viene salvato).
Strumento di orientamento all'invio al genetista: NON ha valore diagnostico.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import streamlit as st

from .engine_genetica import MotoreGenetica
from .ponte_pnev import AREE, BRIDGE
from .volto import GRUPPI, VISTE, VOLTO
from .import_gestionale import raccogli_proposte
from . import db_genetica as db

AVVISO = ("Strumento di **orientamento** all'invio al genetista, basato sui profili della "
          "Human Phenotype Ontology. **Non ha valore diagnostico**: la diagnosi richiede la visita "
          "di genetica clinica e un test di laboratorio. Non comunicare alla famiglia i nomi delle "
          "sindromi come ipotesi.")
STATI = ["—", "Presente", "Assente"]
AVVISO_FOTO = ("Le foto restano nel database dello Studio e **non vengono inviate a nessun servizio esterno "
               "o AI**: servono solo a te per valutare il volto. Non c'è riconoscimento automatico: "
               "i segni li scegli tu. Si salvano solo con il **consenso dei genitori/tutore**.")
_LATO_MAX = 1600   # px: basta per la valutazione e tiene leggero il database


def _prepara_foto(file) -> tuple[bytes, str]:
    """Raddrizza la foto, la ridimensiona e la salva in JPEG senza dati EXIF (niente GPS né modello
    del telefono). Restituisce (bytes, mime)."""
    from PIL import Image, ImageOps
    img = Image.open(file)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((_LATO_MAX, _LATO_MAX))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)   # Pillow non copia l'EXIF se non glielo si passa
    return buf.getvalue(), "image/jpeg"


def _cambia_segno(store, h, k, fonte):
    v = st.session_state.get(k, "—")
    store.set_segno(h, None if v == "—" else v.lower(), fonte)


def _radio_segno(store, profilo, prefisso, paziente_id, h, etichetta, fonte):
    """Radio Presente/Assente sempre allineato al database.
    Il valore si scrive solo quando l'utente cambia il radio (on_change): così un segno aggiunto da
    un'altra scheda (ricerca HPO, proposte dal gestionale) non viene cancellato al rerun."""
    k = f"{prefisso}_{paziente_id}_{h}"
    cur = profilo.get(h, {}).get("stato")
    st.session_state[k] = "Presente" if cur == "presente" else "Assente" if cur == "assente" else "—"
    st.radio(etichetta, STATI, horizontal=True, key=k, label_visibility="collapsed",
             on_change=_cambia_segno, args=(store, h, k, fonte))


@st.cache_resource(show_spinner="Carico 8.512 sindromi HPO…")
def _motore() -> MotoreGenetica:
    return MotoreGenetica()


# --------------------------------------------------------------------------- archivio
class _Mem:
    """Archivio in memoria per la modalità demo."""
    def __init__(self, pid):
        self.k = f"_gen_demo_{pid}"
        st.session_state.setdefault(self.k, {"profilo": {}, "esiti": [], "analisi": [], "foto": []})

    @property
    def s(self): return st.session_state[self.k]
    def get_profilo(self): return dict(self.s["profilo"])
    def set_segno(self, h, stato, fonte=""):
        if stato is None: self.s["profilo"].pop(h, None)
        else: self.s["profilo"][h] = {"stato": stato, "fonte": fonte, "note": ""}
    def add_esito(self, **kw): self.s["esiti"].insert(0, kw)
    def get_esiti(self): return self.s["esiti"]
    def casi_confermati(self): return []
    def salva_analisi(self, **kw): self.s["analisi"].insert(0, kw)
    def get_foto(self): return self.s.setdefault("foto", [])
    def add_foto(self, **kw):
        f = self.get_foto()
        f.insert(0, {"id": max([x["id"] for x in f] or [0]) + 1, "created_at": None, **kw})
    def del_foto(self, foto_id): self.s["foto"] = [x for x in self.get_foto() if x["id"] != foto_id]


class _DB:
    def __init__(self, conn, pid, studio_id):
        self.c, self.pid, self.sid = conn, pid, studio_id
        db.ensure_tables(conn)
    def get_profilo(self): return db.get_profilo(self.c, self.pid)
    def set_segno(self, h, stato, fonte=""): db.set_segno(self.c, self.pid, h, stato, fonte, studio_id=self.sid)
    def add_esito(self, **kw): db.add_esito(self.c, self.pid, studio_id=self.sid, **kw)
    def get_esiti(self): return db.get_esiti(self.c, self.pid)
    def casi_confermati(self): return db.casi_confermati(self.c, escludi_paziente=self.pid)
    def salva_analisi(self, **kw): db.salva_analisi(self.c, self.pid, studio_id=self.sid, **kw)
    def get_foto(self): return db.get_foto(self.c, self.pid)
    def add_foto(self, **kw): db.add_foto(self.c, self.pid, studio_id=self.sid, **kw)
    def del_foto(self, foto_id): db.del_foto(self.c, foto_id, self.pid)


# --------------------------------------------------------------------------- UI
def render_genetica(conn, paziente_id: int, paziente_nome: str = "", studio_id: str | None = None):
    m = _motore()
    store = _DB(conn, paziente_id, studio_id) if conn is not None else _Mem(paziente_id)

    st.subheader(f"🧬 Profilo genetico PNEV{' · ' + paziente_nome if paziente_nome else ''}")
    if conn is None:
        st.info("Modalità DEMO: i dati restano in memoria e non vengono salvati.")
    st.caption(AVVISO)

    profilo = store.get_profilo()
    t1, tv, t2, t3, t4 = st.tabs(["1 · Segni PNEV", "2 · Volto e foto", "3 · Altri segni HPO",
                                  "4 · Analisi", "5 · Esiti genetici"])

    # 1 · tabella ponte
    with t1:
        profilo = _render_proposte(conn, store, paziente_id, profilo, m)
        st.markdown("Segna i reperti come **Presente** o **Assente**. Lascia **—** ciò che non hai valutato. "
                    "Anche i segni assenti aiutano il confronto.")
        for a, nome_area in AREE.items():
            righe = [b for b in BRIDGE if b[0] == a]
            with st.expander(nome_area, expanded=False):
                n_set = sum(1 for b in righe if b[1] in profilo)
                st.caption(f"{n_set}/{len(righe)} reperti valutati")
                for _, h, reperto, strumento in righe:
                    c1, c2 = st.columns([3, 2])
                    c1.markdown(f"**{reperto}**  \n<span style='color:#7F8C8D;font-size:0.85em'>{h} · {strumento}</span>",
                                unsafe_allow_html=True)
                    with c2:
                        _radio_segno(store, profilo, "gen", paziente_id, h, reperto, "ponte PNEV")

    # 2 · volto e foto
    with tv:
        profilo = _render_volto(store, paziente_id, profilo)

    # 3 · ricerca libera HPO
    with t2:
        q = st.text_input("Cerca un segno (italiano, inglese o codice HP:…)", key=f"gen_q_{paziente_id}")
        if q:
            ris = m.cerca(q)
            if not ris:
                st.warning("Nessun termine trovato.")
            else:
                scelta = st.selectbox("Risultati", ris, format_func=lambda x: x[1], key=f"gen_sel_{paziente_id}")
                c1, c2 = st.columns(2)
                if c1.button("➕ Presente", key=f"gen_addp_{paziente_id}"):
                    store.set_segno(scelta[0], "presente", "ricerca HPO"); st.rerun()
                if c2.button("➖ Assente", key=f"gen_adda_{paziente_id}"):
                    store.set_segno(scelta[0], "assente", "ricerca HPO"); st.rerun()
        profilo = store.get_profilo()
        if profilo:
            st.markdown("**Profilo attuale del paziente**")
            df = pd.DataFrame([{"Codice": h, "Segno": m.label(h), "Stato": v["stato"], "Fonte": v.get("fonte") or ""}
                               for h, v in sorted(profilo.items(), key=lambda x: (x[1]["stato"], m.label(x[0])))])
            st.dataframe(df, hide_index=True, use_container_width=True)
            togli = st.selectbox("Rimuovi un segno", [""] + list(profilo), key=f"gen_rm_{paziente_id}",
                                 format_func=lambda h: h and f"{m.label(h)} · {h}")
            if togli and st.button("Rimuovi", key=f"gen_rmb_{paziente_id}"):
                store.set_segno(togli, None); st.rerun()
            pres = [h for h, v in profilo.items() if v["stato"] == "presente"]
            ass = [h for h, v in profilo.items() if v["stato"] == "assente"]
            testo = ("SEGNI PRESENTI (HPO)\n" + "\n".join(f"- {m.label(h)} ({h})" for h in pres) +
                     "\n\nSEGNI ASSENTI (esclusi)\n" + "\n".join(f"- {m.label(h)} ({h})" for h in ass))
            st.download_button("⬇️ Elenco HPO per la lettera al genetista", testo,
                               file_name=f"profilo_HPO_{paziente_id}.txt", key=f"gen_dl_{paziente_id}")

    # 4 · analisi
    with t3:
        pres = [h for h, v in profilo.items() if v["stato"] == "presente"]
        ass = [h for h, v in profilo.items() if v["stato"] == "assente"]
        if len(pres) < 3:
            st.warning("Servono almeno 3 segni presenti per un confronto sensato.")
        else:
            tot, giudizio = m.informativita(pres)
            st.markdown(f"**{len(pres)} segni presenti, {len(ass)} assenti** · informatività del profilo: "
                        f"**{tot:.1f}**, {giudizio}")
            if st.button("🔎 Confronta con le 8.512 sindromi", type="primary", key=f"gen_run_{paziente_id}"):
                casi = store.casi_confermati()
                if casi:
                    m.carica_casi_confermati(casi)
                with st.spinner("Calcolo in corso…"):
                    ris = m.analizza(pres, ass)
                st.session_state[f"gen_ris_{paziente_id}"] = (ris, tot)
                store.salva_analisi(n_presenti=len(pres), n_assenti=len(ass), informativita=tot,
                                    versione_dati=m.versione, risultati=ris)
                if casi:
                    st.caption(f"Frequenze aggiornate con {len(casi)} casi confermati dello Studio.")
            ris_tot = st.session_state.get(f"gen_ris_{paziente_id}")
            if ris_tot:
                ris, _ = ris_tot
                df = pd.DataFrame([{
                    "#": r["rank"], "Sindrome": r["nome"], "Codice": r["disease_id"],
                    "Geni": ", ".join(r["geni"][:4]), "Eredità": ", ".join(r["eredita"]),
                    "Somiglianza": r["somiglianza"], "p*": r["p_value"],
                    "Segni coincidenti": len(r["segni_corrispondenti"]),
                    "Casi Studio": r["casi_studio"]} for r in ris])
                st.dataframe(df, hide_index=True, use_container_width=True,
                             column_config={"Somiglianza": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
                gap = ris[0]["somiglianza"] - ris[1]["somiglianza"] if len(ris) > 1 else 0
                if gap >= 0.15 and tot >= 16:
                    st.success(f"La prima sindrome si stacca nettamente dalle altre (+{gap:.2f}). "
                               "Ha senso segnalarla al genetista come ipotesi da verificare.")
                else:
                    st.info("Nessuna sindrome si stacca nettamente: il profilo indica un approfondimento "
                            "genetico generale (array/esoma), senza un'ipotesi specifica.")
                st.caption("*p = confronto con 300 profili casuali della stessa dimensione, non corretto "
                           "per i confronti multipli: usalo come indicazione, non come prova.")

    # 5 · esiti genetici
    with t4:
        st.markdown("Registra qui gli esiti dei test genetici. Le **diagnosi confermate con consenso alla "
                    "ricerca** servono al sistema per imparare (livello 3 dell'Atlante).")
        with st.form(f"gen_esito_{paziente_id}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Test", ["CGH-array", "Esoma", "Esoma trio", "Genoma", "X-fragile", "Pannello", "Altro"])
            esito = c2.selectbox("Esito", ["in_attesa", "diagnosi_confermata", "negativo", "vus"],
                                 format_func=lambda x: {"in_attesa": "In attesa", "diagnosi_confermata": "Diagnosi confermata",
                                                        "negativo": "Negativo", "vus": "Variante di significato incerto"}[x])
            c3, c4, c5 = st.columns(3)
            dis = c3.text_input("Codice sindrome (es. OMIM:616789)")
            gene = c4.text_input("Gene")
            var = c5.text_input("Variante")
            c6, c7 = st.columns(2)
            lab = c6.text_input("Laboratorio")
            data_es = c7.date_input("Data esito", value=date.today())
            consenso = st.checkbox("Il paziente / tutore ha firmato il consenso all'uso pseudonimizzato dei dati per la ricerca")
            note = st.text_area("Note", height=70)
            if st.form_submit_button("Salva esito"):
                dis = dis.strip().upper().replace(" ", "")
                if dis and dis not in m.dis_index:
                    st.error(f"Codice {dis} non presente tra le 8.512 sindromi HPO.")
                else:
                    store.add_esito(esito=esito, tipo_test=tipo, disease_id=dis, gene=gene, variante=var,
                                    laboratorio=lab, data_esito=data_es, consenso_ricerca=consenso, note=note)
                    st.success("Esito salvato.")
        es = store.get_esiti()
        if es:
            st.dataframe(pd.DataFrame(es), hide_index=True, use_container_width=True)


# --------------------------------------------------------------------------- volto e foto
def _render_volto(store, paziente_id: int, profilo: dict) -> dict:
    st.caption(AVVISO_FOTO)
    col_foto, col_segni = st.columns([2, 3])

    with col_foto:
        st.markdown("**📷 Foto del volto**")
        with st.expander("➕ Aggiungi una foto", expanded=False):
            with st.form(f"genv_up_{paziente_id}", clear_on_submit=True):
                file = st.file_uploader("Foto (JPG, PNG, WEBP)", type=["jpg", "jpeg", "png", "webp"])
                vista = st.selectbox("Vista", VISTE)
                note = st.text_input("Note (facoltative)")
                consenso = st.checkbox("I genitori/il tutore hanno firmato il consenso alla foto per uso clinico")
                if st.form_submit_button("Salva foto"):
                    if not file:
                        st.error("Scegli prima una foto.")
                    elif not consenso:
                        st.error("Senza consenso dei genitori/tutore la foto non si salva.")
                    else:
                        try:
                            dati, mime = _prepara_foto(file)
                            store.add_foto(dati=dati, mime=mime, vista=vista, consenso=True, note=note)
                            st.success("Foto salvata.")
                        except Exception as e:
                            st.error(f"Foto non salvata: {e}")
        foto = store.get_foto()
        if not foto:
            st.info("Nessuna foto. Ideali: una frontale e una di profilo, viso neutro, buona luce.")
        else:
            def _etich(f):
                quando = f["created_at"].strftime("%d/%m/%Y") if f.get("created_at") else "demo"
                return f"{f.get('vista') or 'Foto'} · {quando}"
            scelta = st.selectbox("Foto", foto, format_func=_etich, key=f"genv_sel_{paziente_id}")
            st.image(scelta["dati"], use_container_width=True)
            if scelta.get("note"):
                st.caption(scelta["note"])
            st.caption(f"{len(foto)} foto salvate per questo paziente.")
            conferma = st.checkbox("Voglio eliminare questa foto", key=f"genv_delc_{paziente_id}_{scelta['id']}")
            if conferma and st.button("🗑️ Elimina foto", key=f"genv_del_{paziente_id}_{scelta['id']}"):
                store.del_foto(scelta["id"])
                st.rerun()

    with col_segni:
        st.markdown("**🙂 Segni del volto**")
        st.caption("Guarda la foto (o il bambino) e segna **Presente** o **Assente**. Lascia **—** se non "
                   "sei sicuro: un segno dubbio inserito come presente peggiora il confronto.")
        for gruppo in GRUPPI:
            righe = [v for v in VOLTO if v[0] == gruppo]
            n_set = sum(1 for v in righe if v[1] in profilo)
            with st.expander(f"{gruppo} · {n_set}/{len(righe)}", expanded=False):
                for _, h, etichetta, inglese in righe:
                    c1, c2 = st.columns([3, 2])
                    c1.markdown(f"**{etichetta}**  \n<span style='color:#7F8C8D;font-size:0.85em'>{h} · {inglese}</span>",
                                unsafe_allow_html=True)
                    with c2:
                        _radio_segno(store, profilo, "genv", paziente_id, h, etichetta, "volto")
    return profilo


# --------------------------------------------------------------------------- proposte dal gestionale
def _render_proposte(conn, store, paziente_id: int, profilo: dict, m) -> dict:
    if conn is None:
        st.caption("📥 Nel gestionale qui compaiono i segni proposti dalle altre valutazioni del paziente.")
        return profilo
    prop = raccogli_proposte(conn, paziente_id)
    nuove = {h: l for h, l in prop.items() if h not in profilo}
    contrasto = {h: l for h, l in prop.items() if profilo.get(h, {}).get("stato") == "assente"}
    gia = [h for h, l in prop.items() if profilo.get(h, {}).get("stato") == "presente"]

    with st.expander(f"📥 Proposte dalle altre valutazioni del gestionale · {len(nuove)} nuove",
                     expanded=bool(nuove)):
        st.caption("Segni che risultano **presenti** nelle valutazioni già salvate (INPP, visiva, uditiva, "
                   "anamnesi, logopedia, DSA, NPS). Il modulo li **propone**: controlla e conferma tu. "
                   "Gli altri moduli non vengono modificati.")
        if not prop:
            st.info("Nessun segno da proporre: le valutazioni salvate non contengono reperti che superano le soglie.")
            return profilo
        if nuove:
            scelti = []
            for h, lista in sorted(nuove.items(), key=lambda x: m.label(x[0])):
                if st.checkbox(f"**{m.label(h)}** · {h}", value=True, key=f"genp_{paziente_id}_{h}"):
                    scelti.append(h)
                st.caption(" · ".join(f"{p.fonte}{' ' + p.data if p.data else ''}: {p.dettaglio}" for p in lista))
            if st.button(f"✅ Aggiungi {len(scelti)} segni come Presente", type="primary",
                         disabled=not scelti, key=f"genp_ok_{paziente_id}"):
                for h in scelti:
                    fonti = "; ".join(dict.fromkeys(f"{p.fonte} {p.data}".strip() for p in nuove[h]))
                    store.set_segno(h, "presente", f"gestionale: {fonti}"[:300])
                st.rerun()
        if contrasto:
            st.warning("Segnati **Assente** ma il gestionale li indica presenti: " +
                       "; ".join(f"{m.label(h)} ({', '.join(dict.fromkeys(p.fonte for p in l))})"
                                 for h, l in contrasto.items()) + ". Ricontrolla.")
        if gia:
            st.caption(f"Già nel profilo: {len(gia)} segni proposti dal gestionale.")
    return profilo
