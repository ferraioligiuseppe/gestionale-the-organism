"""
Modulo Genetica PNEV · interfaccia Streamlit.

Uso nel gestionale:
    from modules.genetica.ui_genetica import render_genetica
    render_genetica(conn, paziente_id, paziente_nome, studio_id)

Con conn=None il modulo funziona in modalità DEMO (dati solo in memoria, nulla viene salvato).
Strumento di orientamento all'invio al genetista: NON ha valore diagnostico.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from .engine_genetica import MotoreGenetica
from .ponte_pnev import AREE, BRIDGE
from . import db_genetica as db

AVVISO = ("Strumento di **orientamento** all'invio al genetista, basato sui profili della "
          "Human Phenotype Ontology. **Non ha valore diagnostico**: la diagnosi richiede la visita "
          "di genetica clinica e un test di laboratorio. Non comunicare alla famiglia i nomi delle "
          "sindromi come ipotesi.")
STATI = ["—", "Presente", "Assente"]


@st.cache_resource(show_spinner="Carico 8.512 sindromi HPO…")
def _motore() -> MotoreGenetica:
    return MotoreGenetica()


# --------------------------------------------------------------------------- archivio
class _Mem:
    """Archivio in memoria per la modalità demo."""
    def __init__(self, pid):
        self.k = f"_gen_demo_{pid}"
        st.session_state.setdefault(self.k, {"profilo": {}, "esiti": [], "analisi": []})

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


# --------------------------------------------------------------------------- UI
def render_genetica(conn, paziente_id: int, paziente_nome: str = "", studio_id: str | None = None):
    m = _motore()
    store = _DB(conn, paziente_id, studio_id) if conn is not None else _Mem(paziente_id)

    st.subheader(f"🧬 Profilo genetico PNEV{' · ' + paziente_nome if paziente_nome else ''}")
    if conn is None:
        st.info("Modalità DEMO: i dati restano in memoria e non vengono salvati.")
    st.caption(AVVISO)

    profilo = store.get_profilo()
    t1, t2, t3, t4 = st.tabs(["1 · Segni PNEV", "2 · Altri segni HPO", "3 · Analisi", "4 · Esiti genetici"])

    # 1 · tabella ponte
    with t1:
        st.markdown("Segna i reperti come **Presente** o **Assente**. Lascia **—** ciò che non hai valutato. "
                    "Anche i segni assenti aiutano il confronto.")
        for a, nome_area in AREE.items():
            righe = [b for b in BRIDGE if b[0] == a]
            with st.expander(nome_area, expanded=False):
                n_set = sum(1 for b in righe if b[1] in profilo)
                st.caption(f"{n_set}/{len(righe)} reperti valutati")
                for _, h, reperto, strumento in righe:
                    cur = profilo.get(h, {}).get("stato")
                    idx = 1 if cur == "presente" else 2 if cur == "assente" else 0
                    c1, c2 = st.columns([3, 2])
                    c1.markdown(f"**{reperto}**  \n<span style='color:#7F8C8D;font-size:0.85em'>{h} · {strumento}</span>",
                                unsafe_allow_html=True)
                    v = c2.radio(reperto, STATI, index=idx, horizontal=True, key=f"gen_{paziente_id}_{h}",
                                 label_visibility="collapsed")
                    nuovo = None if v == "—" else v.lower()
                    if nuovo != cur:
                        store.set_segno(h, nuovo, "ponte PNEV")
                        profilo = store.get_profilo()

    # 2 · ricerca libera HPO
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

    # 3 · analisi
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

    # 4 · esiti genetici
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
