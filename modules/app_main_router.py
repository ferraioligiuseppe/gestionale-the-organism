# -*- coding: utf-8 -*-
"""
Router principale — menu a 7 aree.
Sostituisce app_main_router.py e gestisce la nuova navigazione.
"""
from __future__ import annotations
from typing import Callable, Any
import streamlit as st

from .app_menu import (
    AREE_ORDINE, SOTTOSEZIONI,
    AREA_PAZIENTI, AREA_VALUTAZIONE, AREA_VALUTAZIONE_VISIVA, AREA_TEST_NEUROEVOL, AREA_TEST_LIVE,
    AREA_QUESTIONARI, AREA_REPORT_AI, AREA_AUDIOLOGIA,
    AREA_MARKETING, AREA_STUDIO,
)


# ══════════════════════════════════════════════════════════════════════
#  SELETTORE PAZIENTE
# ══════════════════════════════════════════════════════════════════════

def _seleziona_paziente(conn, key_suffix: str = "") -> tuple[int | None, str]:
    """Selettore paziente — ritorna (id, label)."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, Cognome, Nome, Data_Nascita FROM Pazienti "
            "WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' "
            "ORDER BY Cognome, Nome"
        )
        rows = cur.fetchall() or []
    except Exception as e:
        st.error(f"Errore caricamento pazienti: {e}")
        return None, ""

    if not rows:
        st.info("Nessun paziente registrato.")
        return None, ""

    def _label(r):
        if isinstance(r, dict):
            pid = r.get("id"); c = r.get("Cognome",""); n = r.get("Nome","")
            dn  = r.get("Data_Nascita","")
        else:
            pid, c, n = r[0], r[1], r[2]
            dn = r[3] if len(r) > 3 else ""
        return f"{pid} — {c} {n}" + (f" · {dn}" if dn else "")

    sel = st.selectbox("👤 Paziente", options=rows,
                       format_func=_label, key=f"paz_{key_suffix}")
    if isinstance(sel, dict):
        return int(sel.get("id")), _label(sel)
    return int(sel[0]), _label(sel)


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD HOME
# ══════════════════════════════════════════════════════════════════════

def _fmt_data(raw) -> str:
    """Formatta data in italiano: 19 Apr 2026"""
    try:
        import datetime as _dt
        s = str(raw)[:10]
        d = _dt.date.fromisoformat(s)
        mesi = ["","Gen","Feb","Mar","Apr","Mag","Giu",
                "Lug","Ago","Set","Ott","Nov","Dic"]
        return f"{d.day} {mesi[d.month]} {d.year}"
    except Exception:
        return str(raw)[:10] if raw else "—"


def _seleziona_paziente_card(conn) -> tuple:
    """Selettore paziente con formato pulito (solo Cognome Nome)."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, Cognome, Nome, Data_Nascita, Email "
            "FROM Pazienti WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' "
            "ORDER BY Cognome, Nome"
        )
        rows = cur.fetchall() or []
    except Exception:
        return None, "", {}

    if not rows:
        st.info("Nessun paziente registrato.")
        return None, "", {}

    def _label(r):
        if isinstance(r, dict):
            c = r.get("Cognome",""); n = r.get("Nome","")
            dn = r.get("Data_Nascita","")
        else:
            c, n = r[1], r[2]
            dn = r[3] if len(r) > 3 else ""
        eta = ""
        if dn:
            try:
                import datetime as _dt
                anni = (_dt.date.today() - _dt.date.fromisoformat(str(dn)[:10])).days // 365
                eta = f"  ({anni} anni)"
            except Exception:
                pass
        return f"{c} {n}{eta}"

    sel = st.selectbox(
        "Seleziona paziente",
        options=rows,
        format_func=_label,
        key="paz_home_card",
        label_visibility="collapsed",
    )
    if isinstance(sel, dict):
        pid = int(sel.get("id"))
        info = sel
    else:
        pid = int(sel[0])
        cols_names = ["id","Cognome","Nome","Data_Nascita","Email"]
        info = dict(zip(cols_names, sel))
    return pid, _label(sel), info


def _render_dashboard(conn) -> None:
    """Dashboard home — riepilogo paziente corrente."""

    # ── Intestazione grafica con loghi PNEV + The Organism ────────────
    try:
        import base64 as _b64
        from .loghi_data import LOGO_PNEV_B64, LOGO_ORGANISM_B64
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:22px;justify-content:space-between;
     background:linear-gradient(120deg,#f3f0ff 0%,#eef7f4 100%);
     border:1px solid var(--color-border-tertiary);
     border-radius:16px;padding:18px 26px;margin:4px 0 18px 0">
  <div style="display:flex;align-items:center;gap:16px">
    <img src="data:image/png;base64,{LOGO_PNEV_B64}" style="height:46px">
    <div style="width:1px;height:38px;background:#d8d4e8"></div>
    <img src="data:image/png;base64,{LOGO_ORGANISM_B64}" style="height:34px">
  </div>
  <div style="text-align:right;color:#6b6478;font-size:.82rem;font-style:italic">
    Metodo PNEV · Studio The Organism
  </div>
</div>
<p style='color:#8b949e;margin:0 0 14px'>Seleziona un paziente</p>
""", unsafe_allow_html=True)
    except Exception:
        st.markdown(
            "<h2 style='margin-bottom:4px'>🏠 The Organism</h2>"
            "<p style='color:#8b949e;margin-top:0'>Seleziona un paziente</p>",
            unsafe_allow_html=True
        )

    paz_id, paz_label, paz_info = _seleziona_paziente_card(conn)
    if not paz_id:
        return

    # ── Card paziente ────────────────────────────────────────────────
    cognome  = paz_info.get("Cognome","")
    nome     = paz_info.get("Nome","")
    dn_raw   = paz_info.get("Data_Nascita","")
    email    = paz_info.get("Email","") or "—"
    dn_fmt   = _fmt_data(dn_raw)

    try:
        import datetime as _dt
        eta = (_dt.date.today() - _dt.date.fromisoformat(str(dn_raw)[:10])).days // 365
        eta_str = f"{eta} anni"
    except Exception:
        eta_str = ""

    st.markdown(f"""
<div style="background:var(--color-background-secondary);
     border:1px solid var(--color-border-tertiary);
     border-radius:12px;padding:20px 24px;margin:8px 0 20px 0">
  <div style="font-size:1.6rem;font-weight:700;color:var(--color-text-primary)">
    {cognome} {nome}
  </div>
  <div style="color:#8b949e;font-size:.95rem;margin-top:4px">
    Nato il {dn_fmt} &nbsp;·&nbsp; {eta_str} &nbsp;·&nbsp; {email}
  </div>
</div>""", unsafe_allow_html=True)

    # ── Tre colonne info ─────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📅 Ultima seduta**")
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT Data_Ora, Tipo FROM Sedute "
                "WHERE paziente_id=%s ORDER BY Data_Ora DESC LIMIT 1",
                (paz_id,)
            )
            s = cur.fetchone()
            if s:
                data = _fmt_data(s[0] if not isinstance(s, dict) else s.get("Data_Ora",""))
                tipo = (s[1] if not isinstance(s, dict) else s.get("Tipo","")) or "—"
                st.info(f"**{data}** — {tipo}")
            else:
                st.caption("Nessuna seduta")
        except Exception:
            st.caption("—")

    with col2:
        st.markdown("**📋 Questionari**")
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT questionario, used_at, expires_at "
                "FROM questionari_links "
                "WHERE paziente_id=%s ORDER BY created_at DESC LIMIT 5",
                (paz_id,)
            )
            links = cur.fetchall() or []
            if links:
                for lk in links:
                    if isinstance(lk, dict):
                        q    = lk.get("questionario","")
                        used = lk.get("used_at")
                        exp  = lk.get("expires_at","")
                    else:
                        q, used, exp = lk[0], lk[1], lk[2]
                    q_clean = q.replace("_"," ").title()
                    if used:
                        st.markdown(f"✅ &nbsp;{q_clean}", unsafe_allow_html=True)
                    else:
                        exp_fmt = _fmt_data(exp)
                        st.markdown(f"⏳ {q_clean} — scade {exp_fmt}", unsafe_allow_html=True)
            else:
                st.caption("Nessun link inviato")
        except Exception:
            st.caption("—")

    with col3:
        st.markdown("**🔬 Ultimi test**")
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT nome_test, data_somm FROM somministrazioni_test "
                "WHERE paziente_id=%s ORDER BY created_at DESC LIMIT 5",
                (paz_id,)
            )
            tests = cur.fetchall() or []
            if tests:
                for t in tests:
                    nome = t[0] if not isinstance(t, dict) else t.get("nome_test","")
                    data = _fmt_data(t[1] if not isinstance(t, dict) else t.get("data_somm",""))
                    st.markdown(f"**{nome}** — {data}")
            else:
                st.caption("Nessun test registrato")
        except Exception:
            st.caption("—")

    # ── Sintesi economica: incassi + coupon ───────────────────────────
    st.markdown("---")
    st.markdown("**💶 Sintesi economica**")
    ce1, ce2, ce3, ce4 = st.columns(4)
    tot_sedute = tot_terapia = 0.0
    n_coupon = n_coupon_usati = 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(Pagato),0) FROM Sedute WHERE paziente_id=%s", (paz_id,))
        r = cur.fetchone()
        tot_sedute = float(r[0] if not isinstance(r, dict) else list(r.values())[0]) or 0.0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(Incassato),0) FROM terapia_sedute WHERE paziente_id=%s",
                    (paz_id,))
        r = cur.fetchone()
        tot_terapia = float(r[0] if not isinstance(r, dict) else list(r.values())[0]) or 0.0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(CASE WHEN Utilizzato=1 OR Utilizzato=TRUE "
                    "THEN 1 ELSE 0 END),0) FROM Coupons WHERE paziente_id=%s", (paz_id,))
        r = cur.fetchone()
        if r:
            n_coupon = int(r[0] if not isinstance(r, dict) else list(r.values())[0]) or 0
            n_coupon_usati = int(r[1] if not isinstance(r, dict) else list(r.values())[1]) or 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    ce1.metric("Incassato sedute", f"{tot_sedute:,.0f} €".replace(",", "."))
    ce2.metric("Incassato terapie", f"{tot_terapia:,.0f} €".replace(",", "."))
    ce3.metric("Totale complessivo", f"{tot_sedute + tot_terapia:,.0f} €".replace(",", "."))
    ce4.metric("Coupon", f"{n_coupon_usati}/{n_coupon} usati" if n_coupon else "—")

    # ── Accesso rapido alle pagine del paziente ───────────────────────
    st.markdown("**🔗 Vai a**")
    _link_dest = [
        ("🧩 Quadro storico", "👥 Pazienti", "🧩 Quadro storico"),
        ("📎 Documenti clinici", "👥 Pazienti", "📎 Documenti clinici"),
        ("📝 Diagnosi assistita", "👥 Pazienti", "📝 Diagnosi assistita"),
        ("📈 Esiti / Follow-up", "👥 Pazienti", "📈 Esiti / Follow-up"),
        ("🧘 Percorsi terapeutici", "🎧 Terapia & relazione", "🧘 Percorsi terapeutici"),
        ("🧩 Programma PNEV", "🎧 Terapia & relazione", "🧩 Programma PNEV"),
        ("👁️ Valutazione visuo-percettiva", "🔍 Valutazione funzionale",
         "👁️ Valutazione visuo-percettiva"),
        ("🎟️ Coupon OF / SDS", "👥 Pazienti", "🎟️ Coupon OF / SDS"),
    ]
    lcols = st.columns(4)
    for i, (etichetta, area_dest, sotto_dest) in enumerate(_link_dest):
        with lcols[i % 4]:
            if st.button(etichetta, key=f"dash_link_{i}", use_container_width=True):
                st.session_state["goto_area"] = area_dest
                st.session_state["goto_sotto"] = sotto_dest
                st.session_state["paziente_attivo_id"] = paz_id
                st.rerun()

    # ── Anamnesi ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**📊 Riepilogo valutazioni**")
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT data_anamnesi, motivo, pnev_summary "
            "FROM anamnesi WHERE paziente_id=%s "
            "ORDER BY data_anamnesi DESC LIMIT 1",
            (paz_id,)
        )
        an = cur.fetchone()
        if an:
            data_an = _fmt_data(an[0] if not isinstance(an, dict) else an.get("data_anamnesi",""))
            motivo  = (an[1] if not isinstance(an, dict) else an.get("motivo","")) or "—"
            summary = (an[2] if not isinstance(an, dict) else an.get("pnev_summary","")) or ""
            st.success(f"Ultima anamnesi: **{data_an}** — {motivo}")
            if summary:
                with st.expander("Leggi sintesi"):
                    st.markdown(summary[:800] + ("…" if len(summary) > 800 else ""))
        else:
            st.info("Nessuna anamnesi registrata.")
    except Exception:
        st.caption("—")


# ══════════════════════════════════════════════════════════════════════
#  RENDER AREA — dispatch per sottosezione
# ══════════════════════════════════════════════════════════════════════

def _assistente_coda(conn, paz_id):
    """Riquadro Assistente PNEV in coda a una schermata di test: lettura del
    caso sul paziente in lavorazione, appena hai inserito/salvato un dato."""
    if not paz_id:
        return
    try:
        import streamlit as st
        from .assistente_pnev import render_assistente
        st.markdown("---")
        with st.expander("💡 Assistente PNEV — leggi il caso con l'AI", expanded=False):
            render_assistente(conn, paz_id, compatto=True)
    except Exception:
        pass


# ── Sequenza guidata di visita: INPP → Visiva → Uditiva → Diagnosi ────
# (area_destinazione, sotto_destinazione, etichetta bottone)
_PROSSIMO_PASSO = {
    "🧬 INPP — Valutazione diagnostica": (
        "🔍 Valutazione funzionale", "👁️ Valutazione visuo-percettiva",
        "▶ Passo successivo: Valutazione visiva"),
    "👁️ Valutazione visuo-percettiva": (
        "🔍 Valutazione funzionale", "🔉 Diagnostica uditiva",
        "▶ Passo successivo: Valutazione uditiva"),
    "🔉 Diagnostica uditiva": (
        "👥 Pazienti", "📝 Diagnosi assistita",
        "▶ Passo successivo: Diagnosi"),
}


def _bottone_prossimo_passo(conn, paz_id, sotto_corrente):
    """Bottone in fondo alla schermata che porta al passo successivo della
    sequenza di visita (INPP → Visiva → Uditiva → Diagnosi), senza dover
    tornare al menu e ricercare l'area giusta."""
    dest = _PROSSIMO_PASSO.get(sotto_corrente)
    if not dest or not paz_id:
        return
    area_dest, sotto_dest, etichetta = dest
    st.markdown("---")
    if st.button(etichetta, key=f"prossimo_{sotto_corrente}", type="primary",
                use_container_width=True):
        st.session_state["goto_area"] = area_dest
        st.session_state["goto_sotto"] = sotto_dest
        st.session_state["paziente_attivo_id"] = paz_id
        st.rerun()


def _dispatch_sotto(sotto: str, conn, is_admin: bool) -> bool:
    """Dispatch PIATTO: aggancia ogni voce SOLO al suo nome (sotto).

    Da v4 il routing non dipende più dall'area che contiene la voce:
    così le aree nel menu (app_menu.py) si possono riorganizzare senza
    toccare questo file. Ritorna True se la voce è stata gestita.
    Le voci cliniche che richiedono un paziente selezionato mostrano
    prima l'header paziente.
    """
    from .app_menu import PLACEHOLDER_VOCI
    if sotto in PLACEHOLDER_VOCI:
        st.info(f"🚧 **{sotto}** — sezione in costruzione, arriva presto.")
        return True

    from .paziente_attivo import header_paziente_attivo

    VOCI_CON_PAZIENTE = {
        "📅 Sedute / Terapie", "🔒 Privacy & Consensi",
        "📎 Documenti clinici", "🧩 Quadro storico", "💡 Assistente PNEV",
        "📈 Esiti / Follow-up", "📝 Diagnosi assistita",
        "🧘 Percorsi terapeutici", "🧩 Programma PNEV",
        "🔬 PNEV", "📋 Anamnesi PNEV", "👁️ Anamnesi visiva",
        "🧠 NPS — Neuropsicologica", "📚 DSA — Apprendimento",
        "🔬 Test psicologici", "⚡ Funzioni esecutive",
        "👁️ Valutazione visuo-percettiva", "🔢 DEM interattivo",
        "👁️ Getman (manipolazione visiva)",
        "👁️ Groffman (visual tracing)",
        "👁️ Eye tracking",
        "🧬 INPP — Valutazione diagnostica", "🗣️ Logopedia / SMOF",
        "🖥️ Somministrazione test",
        "📋 Questionari remoti", "🎮 Esercizi Wordwall",
        "🔉 Diagnostica uditiva", "🎧 MAPS", "🗂 Programmi MAPS",
        "🧭 Percorsi MAPS", "🎧 Bilancio uditivo", "📊 Audiometria funzionale",
        "🤖 Relazioni cliniche (AI)", "📝 Relazione clinica",
        "🎯 Piano Vision Therapy", "📄 Report PDF con grafici",
    }

    paz_id = None
    if sotto in VOCI_CON_PAZIENTE:
        paz_id = header_paziente_attivo(conn)
        if not paz_id:
            return True  # header mostrato, in attesa di selezione paziente

    # ── PAZIENTI ──────────────────────────────────────────────────────
    if sotto == "🏠 Dashboard":
        _render_dashboard(conn); return True
    if sotto == "📅 Agenda appuntamenti":
        try:
            from .agenda import render_agenda
            render_agenda(conn, is_admin)
        except Exception as e:
            import traceback
            st.error(f"Errore agenda: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "👤 Anagrafica pazienti":
        try:
            from .ui_anagrafica import render_anagrafica
            render_anagrafica(conn)
        except Exception as e:
            import traceback
            st.error(f"Errore anagrafica: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "📎 Documenti clinici":
        try:
            from .documenti_clinici import render_documenti
            render_documenti(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore documenti clinici: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "🧩 Quadro storico":
        try:
            from .quadro_storico import render_quadro
            render_quadro(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore quadro storico: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "📝 Diagnosi assistita":
        try:
            from .diagnosi_assistita import render_diagnosi
            render_diagnosi(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore diagnosi assistita: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "📄 Modulistica / Schede da stampare":
        try:
            from .modulistica import render_modulistica
            render_modulistica(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore modulistica: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "💡 Assistente PNEV":
        try:
            from .assistente_pnev import render_assistente
            render_assistente(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore assistente PNEV: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "📈 Esiti / Follow-up":
        try:
            from .esiti import render_esiti
            render_esiti(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore esiti: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "🧪 Apprendimento PNEV":
        try:
            from .apprendimento import render_apprendimento
            render_apprendimento(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore apprendimento PNEV: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        return True
    if sotto == "🎟️ Coupon OF / SDS":
        try:
            from modules import app_core
            app_core.ui_coupons()
        except Exception as e:
            st.error(f"Errore coupon: {e}")
        return True
    if sotto == "📅 Sedute / Terapie":
        from .sections.ui_cliniche import render_sedute_section
        render_sedute_section(); return True
    if sotto == "🔒 Privacy & Consensi":
        from .privacy.ui_privacy_section import render_privacy_section
        render_privacy_section(); return True
    if sotto == "📥 Import pazienti":
        from .sections.ui_cliniche import render_import_section
        render_import_section(); return True
    if sotto == "🔗 Sincronizza pnev.it":
        from .ui_sync_pnev import render_sync_pnev
        render_sync_pnev(conn); return True
    if sotto == "🚀 Trasferisci a pnev.it":
        from .ui_trasferimento_pnev import render_trasferimento_pnev
        render_trasferimento_pnev(conn); return True
    if sotto == "🎧 Screening uditivo":
        from .ui_screening_link import render_screening_link
        render_screening_link(conn); return True
    if sotto == "🎧 MAPS-CLEAR pubblico":
        try:
            from modules.pnev_pubblico.ui_pnev_pubblico_admin import render_pnev_pubblico_admin
            render_pnev_pubblico_admin(conn)
        except Exception as e:
            st.error(f"Modulo MAPS-CLEAR pubblico non disponibile: {e}")
        return True

    # ── INVII AL PAZIENTE ─────────────────────────────────────────────
    if sotto == "📋 Questionari remoti":
        try:
            from .ui_questionari import render_questionari_section
            render_questionari_section(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo questionari non disponibile: {e}")
        return True
    if sotto == "🎮 Esercizi Wordwall":
        try:
            from .ui_wordwall import render_wordwall
            render_wordwall(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo Wordwall non disponibile: {e}")
        return True

    # ── VALUTAZIONE FUNZIONALE ────────────────────────────────────────
    if sotto == "🔬 PNEV":
        from .pnev.ui_pnev import render_pnev_section
        render_pnev_section(); return True
    if sotto == "📋 Anamnesi PNEV":
        try:
            from .ui_anamnesi_the_organism import render_anamnesi_the_organism
            render_anamnesi_the_organism(conn, paz_id)
        except Exception as e:
            st.error(f"Modulo anamnesi non disponibile: {e}")
        return True
    if sotto == "👁️ Anamnesi visiva":
        try:
            from .ui_anamnesi_visiva import render_anamnesi_visiva
            render_anamnesi_visiva(conn, paz_id)
        except Exception as e:
            st.error(f"Modulo anamnesi visiva non disponibile: {e}")
        return True
    if sotto == "👁️ Valutazione visuo-percettiva":
        try:
            from .ui_valutazione_visuo_percettiva import render_valutazione_visuo_percettiva
            cur2 = conn.cursor()
            cur2.execute("SELECT * FROM Pazienti WHERE id=%s", (paz_id,))
            paz_rec = cur2.fetchone()
            if paz_rec and not isinstance(paz_rec, dict):
                cols = [d[0] for d in cur2.description]
                paz_rec = dict(zip(cols, paz_rec))
            render_valutazione_visuo_percettiva(conn, paz_id, paz_rec or {})
        except Exception as e:
            st.error(f"Errore valutazione visuo-percettiva: {e}")
        _assistente_coda(conn, paz_id)
        _bottone_prossimo_passo(conn, paz_id, sotto)
        return True
    if sotto == "👓 Optometria comportamentale":
        st.info("Sezione in costruzione — usa la Valutazione visuo-percettiva per ora.")
        return True
    if sotto == "🧠 NPS — Neuropsicologica":
        try:
            from .ui_nps_completo import render_nps_completo
            render_nps_completo(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo NPS non disponibile: {e}")
        return True
    if sotto == "📚 DSA — Apprendimento":
        try:
            from .ui_dsa import render_dsa
            render_dsa(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo DSA non disponibile: {e}")
        return True
    if sotto == "🔬 Test psicologici":
        try:
            from .ui_nps_completo import render_test_psy
            render_test_psy(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo PSY non disponibile: {e}")
        return True
    if sotto == "⚡ Funzioni esecutive":
        try:
            from .ui_nps_completo import render_funzioni_esecutive
            render_funzioni_esecutive(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo FE non disponibile: {e}")
        return True
    if sotto == "🧬 INPP — Valutazione diagnostica":
        try:
            from .inpp import render_inpp
            cur2 = conn.cursor()
            cur2.execute("SELECT cognome, nome FROM Pazienti WHERE id=%s", (paz_id,))
            row = cur2.fetchone()
            cur2.close()
            nome = f"{row[0]} {row[1]}".strip() if row else "Paziente"
            render_inpp(conn, paz_id, nome)
        except Exception as e:
            st.error(f"Errore modulo INPP: {e}")
        _bottone_prossimo_passo(conn, paz_id, sotto)
        return True
    if sotto == "🗣️ Logopedia / SMOF":
        try:
            from .logopedia import render_logopedia
            render_logopedia(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore modulo Logopedia: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        _assistente_coda(conn, paz_id)
        return True

    # ── TEST LIVE ─────────────────────────────────────────────────────
    if sotto == "🔢 DEM interattivo":
        try:
            from .dem_test import render_dem
            render_dem(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore modulo DEM: {e}")
            with st.expander("Dettagli"):
                st.code(traceback.format_exc())
        _assistente_coda(conn, paz_id)
        return True
    if sotto == "👁️ Getman (manipolazione visiva)":
        try:
            from .getman import render_getman
            render_getman(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore modulo Getman: {e}")
            with st.expander("Dettagli"):
                st.code(traceback.format_exc())
        _assistente_coda(conn, paz_id)
        return True
    if sotto == "👁️ Groffman (visual tracing)":
        try:
            from .groffman import render_groffman
            render_groffman(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore modulo Groffman: {e}")
            with st.expander("Dettagli"):
                st.code(traceback.format_exc())
        _assistente_coda(conn, paz_id)
        return True
    if sotto == "🖥️ Somministrazione test":
        try:
            from .ui_test_somministrazione import render_somministrazione
            render_somministrazione(conn, paz_id)
        except ImportError as e:
            st.error(f"Modulo somministrazione non disponibile: {e}")
        return True
    if sotto == "👁️ Eye tracking":
        from .sections.ui_cliniche import render_gaze_section
        render_gaze_section(); return True
    if sotto == "📸 Photoref AI":
        try:
            from .photoref_ai.ui_photoref import ui_photoref
            ui_photoref()
        except ImportError as e:
            st.error(f"Modulo Photoref non disponibile: {e}")
        return True
    if sotto == "📖 Lettura avanzata":
        try:
            from .reading.ui_reading_dom import ui_reading_dom
            ui_reading_dom()
        except ImportError as e:
            st.error(f"Modulo Lettura non disponibile: {e}")
        return True

    # ── TERAPIA & RELAZIONE ───────────────────────────────────────────
    if sotto == "🧘 Percorsi terapeutici":
        try:
            from .terapia import render_terapia
            render_terapia(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore percorsi terapeutici: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        _assistente_coda(conn, paz_id)
        return True
    if sotto == "🧩 Programma PNEV":
        try:
            from .terapia_procedure import render_programma
            render_programma(conn, paz_id)
        except Exception as e:
            import traceback
            st.error(f"Errore programma PNEV: {e}")
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())
        _assistente_coda(conn, paz_id)
        return True
    if sotto in ("🤖 Relazioni cliniche (AI)", "📝 Relazione clinica"):
        try:
            from .ui_relazione_clinica import render_relazione_clinica
            render_relazione_clinica(conn)
        except Exception as e:
            st.error(f"Errore relazione clinica: {e}")
        return True
    if sotto in ("🎯 Piano Vision Therapy", "📄 Report PDF con grafici",
                 "📊 Export statistici", "🧪 Caso demo"):
        mappa = {
            "🎯 Piano Vision Therapy":    "PianoVT",
            "📄 Report PDF con grafici":  "ReportPDF",
            "📊 Export statistici":       "ExportStatistici",
            "🧪 Caso demo":               "SeedDemo",
        }
        try:
            from .gestionale_new_modules import render_nuovi_moduli
            render_nuovi_moduli(conn, mappa[sotto], paziente_id=paz_id)
        except ImportError as e:
            st.error(f"Modulo non disponibile: {e}")
        return True
    if sotto == "👁️ Lenti a contatto":
        from .ui_lenti_contatto import ui_lenti_contatto
        ui_lenti_contatto(); return True

    # ── AUDIO (MAPS & diagnostica uditiva) ────────────────────────────
    _audio_map = {
        "🔉 Diagnostica uditiva":    ("ui_diagnostica_uditiva",   "ui_diagnostica_uditiva"),
        "🎧 MAPS":                   ("ui_maps",                  "ui_maps"),
        "🗂 Programmi MAPS":         ("ui_programmi",             "ui_programmi"),
        "🧭 Percorsi MAPS":          ("ui_percorsi",              "ui_percorsi"),
        "🎧 Bilancio uditivo":       ("ui_bilancio_uditivo",      "ui_bilancio_uditivo"),
        "📊 Audiometria funzionale": ("ui_audiometria_funzionale","ui_audiometria_funzionale"),
    }
    if sotto in _audio_map:
        mod_name, fn_name = _audio_map[sotto]
        try:
            import importlib
            m  = importlib.import_module(f"modules.{mod_name}")
            fn = getattr(m, fn_name)
            try:
                fn(conn=conn)
            except TypeError:
                fn()
        except Exception as e_audio:
            st.error(f"Errore {sotto}: {e_audio}")
        _bottone_prossimo_passo(conn, paz_id, sotto)
        return True

    # ── FORMAZIONE & PROFESSIONISTI ───────────────────────────────────
    if sotto == "🦴 Osteopatia":
        from .sections.ui_cliniche import render_osteopatia_section
        render_osteopatia_section(); return True
    if sotto == "📅 Eventi e iscrizioni":
        try:
            from .eventi.ui_eventi import render_eventi_section
            render_eventi_section()
        except ImportError as e:
            st.error(f"Modulo Eventi non disponibile: {e}")
        return True

    # ── STUDIO ────────────────────────────────────────────────────────
    if sotto == "📊 Dashboard incassi":
        from .sections.ui_cliniche import render_dashboard_section
        render_dashboard_section(); return True
    if sotto == "👤 Il mio profilo":
        try:
            from .ui_profilo_professionista import render_profilo_professionista
            render_profilo_professionista(conn)
        except Exception as e:
            st.error(f"Errore profilo: {e}")
        return True
    if sotto == "🏥 Il mio studio":
        try:
            from .saas_tenant import render_gestione_studio
            render_gestione_studio(conn,
                                   st.session_state.get("studio_id", 1),
                                   st.session_state.get("piano", "professional"))
        except ImportError as e:
            st.error(f"Modulo Studio non disponibile: {e}")
        return True
    if sotto == "👥 Utenti / Ruoli":
        try:
            from .ui_gestione_utenti import render_gestione_utenti
            render_gestione_utenti(conn, is_admin)
        except Exception as e:
            st.error(f"Modulo gestione utenti non disponibile: {e}")
        return True
    if sotto == "⚙️ Platform Admin":
        try:
            from .saas_tenant import render_admin_saas
            render_admin_saas(conn)
        except ImportError as e:
            st.error(f"Modulo Admin non disponibile: {e}")
        return True
    if sotto == "🐛 Debug DB":
        from .sections.ui_cliniche import render_debug_section
        render_debug_section(); return True

    return False


def _render_area(area: str, sotto: str, conn, is_admin: bool) -> None:
    """Dispatch per sottosezione (indipendente dall'area).

    Da v4 ogni voce è agganciata SOLO al suo nome tramite _dispatch_sotto,
    così riorganizzare le aree nel menu (app_menu.py) non richiede più di
    toccare questo file. Il vecchio dispatch per-area resta sotto come
    fallback (normalmente non raggiunto).
    """
    if _dispatch_sotto(sotto, conn, is_admin):
        return

    # ── (fallback legacy per-area — normalmente non raggiunto) ────────
    # ── AREA PAZIENTI ─────────────────────────────────────────────────
    if area == AREA_PAZIENTI:
        if sotto == "🏠 Dashboard":
            _render_dashboard(conn)
            return
        if sotto == "👤 Anagrafica pazienti":
            try:
                from .ui_anagrafica import render_anagrafica
                render_anagrafica(conn)
            except Exception as e:
                import traceback
                st.error(f"Errore anagrafica: {e}")
                with st.expander("Dettagli tecnici"):
                    st.code(traceback.format_exc())
            return
        if sotto == "🎟️ Coupon OF / SDS":
            from .paziente_attivo import header_paziente_attivo
            paz_id = header_paziente_attivo(conn)
            if not paz_id:
                return
            try:
                from modules import app_core
                app_core.ui_coupons()
            except Exception as e:
                st.error(f"Errore coupon: {e}")
            return
        if sotto == "📅 Sedute / Terapie":
            from .paziente_attivo import header_paziente_attivo
            paz_id = header_paziente_attivo(conn)
            if not paz_id:
                return
            from .sections.ui_cliniche import render_sedute_section
            render_sedute_section(); return
        if sotto == "🔒 Privacy & Consensi":
            from .paziente_attivo import header_paziente_attivo
            paz_id = header_paziente_attivo(conn)
            if not paz_id:
                return
            from .privacy.ui_privacy_section import render_privacy_section
            render_privacy_section(); return
        if sotto == "📥 Import pazienti":
            from .sections.ui_cliniche import render_import_section
            render_import_section(); return
        if sotto == "🔗 Sincronizza pnev.it":
            from .ui_sync_pnev import render_sync_pnev
            render_sync_pnev(conn); return
        if sotto == "🚀 Trasferisci a pnev.it":
            from .ui_trasferimento_pnev import render_trasferimento_pnev
            render_trasferimento_pnev(conn); return
        if sotto == "🎧 Screening uditivo":
            from .ui_screening_link import render_screening_link
            render_screening_link(conn); return
        if sotto == "🎧 MAPS-CLEAR pubblico":
            try:
                from modules.pnev_pubblico.ui_pnev_pubblico_admin import render_pnev_pubblico_admin
                render_pnev_pubblico_admin(conn)
            except Exception as e:
                st.error(f"Modulo MAPS-CLEAR pubblico non disponibile: {e}")
            return

    # ── AREA VALUTAZIONE ──────────────────────────────────────────────
    elif area == AREA_VALUTAZIONE:
        from .paziente_attivo import header_paziente_attivo
        paz_id = header_paziente_attivo(conn)
        if not paz_id:
            return
        if sotto == "🔬 PNEV":
            from .pnev.ui_pnev import render_pnev_section
            render_pnev_section(); return
        if sotto == "📋 Anamnesi PNEV":
            try:
                from .ui_anamnesi_the_organism import render_anamnesi_the_organism
                render_anamnesi_the_organism(conn, paz_id)
            except Exception as e:
                st.error(f"Modulo anamnesi non disponibile: {e}")
            return
        if sotto == "👁️ Anamnesi visiva":
            try:
                from .ui_anamnesi_visiva import render_anamnesi_visiva
                render_anamnesi_visiva(conn, paz_id)
            except Exception as e:
                st.error(f"Modulo anamnesi visiva non disponibile: {e}")
            return
        if sotto == "🧠 NPS — Neuropsicologica":
            try:
                from .ui_nps_completo import render_nps_completo
                render_nps_completo(conn, paz_id)
            except ImportError as e:
                st.error(f"Modulo NPS non disponibile: {e}")
            return
        if sotto == "📚 DSA — Apprendimento":
            try:
                from .ui_dsa import render_dsa
                render_dsa(conn, paz_id)
            except ImportError as e:
                st.error(f"Modulo DSA non disponibile: {e}")
            return
        if sotto == "🔬 Test psicologici":
            try:
                from .ui_nps_completo import render_test_psy
                render_test_psy(conn, paz_id)
            except ImportError as e:
                st.error(f"Modulo PSY non disponibile: {e}")
            return
        if sotto == "⚡ Funzioni esecutive":
            try:
                from .ui_nps_completo import render_funzioni_esecutive
                render_funzioni_esecutive(conn, paz_id)
            except ImportError as e:
                st.error(f"Modulo FE non disponibile: {e}")
            return
        if sotto == "👓 Optometria comportamentale":
            st.info("Sezione in costruzione — usa la Valutazione visiva (VVF) per ora.")
            return

    # ── AREA VALUTAZIONE VISIVA ───────────────────────────────────────
    elif area == AREA_VALUTAZIONE_VISIVA:
        from .paziente_attivo import header_paziente_attivo
        paz_id = header_paziente_attivo(conn)
        if not paz_id:
            return
        if sotto == "👁️ Anamnesi visiva":
            try:
                from .ui_anamnesi_visiva import render_anamnesi_visiva
                render_anamnesi_visiva(conn, paz_id)
            except Exception as e:
                st.error(f"Modulo anamnesi visiva non disponibile: {e}")
            return
        if sotto == "👓 Optometria comportamentale":
            st.info("Sezione in costruzione — usa la Valutazione visiva (VVF) per ora.")
            return
        if sotto == "👁️ Valutazione visuo-percettiva":
            try:
                from .ui_valutazione_visuo_percettiva import render_valutazione_visuo_percettiva
                cur2 = conn.cursor()
                cur2.execute("SELECT * FROM Pazienti WHERE id=%s", (paz_id,))
                paz_rec = cur2.fetchone()
                if paz_rec and not isinstance(paz_rec, dict):
                    cols = [d[0] for d in cur2.description]
                    paz_rec = dict(zip(cols, paz_rec))
                render_valutazione_visuo_percettiva(conn, paz_id, paz_rec or {})
            except Exception as e:
                st.error(f"Errore valutazione visuo-percettiva: {e}")
            return
        if sotto == "🔢 DEM interattivo":
            try:
                from .gestionale_new_modules import render_nuovi_moduli
                render_nuovi_moduli(conn, "DEM")
            except ImportError as e:
                st.error(f"Modulo DEM non disponibile: {e}")
            return
        if sotto == "👁️ K-D interattivo":
            try:
                from .gestionale_new_modules import render_nuovi_moduli
                render_nuovi_moduli(conn, "KD")
            except ImportError as e:
                st.error(f"Modulo K-D non disponibile: {e}")
            return
        if sotto == "👁️ Eye tracking":
            from .sections.ui_cliniche import render_gaze_section
            render_gaze_section(); return
        if sotto == "👁️ Lenti a contatto":
            from .ui_lenti_contatto import ui_lenti_contatto
            ui_lenti_contatto(); return

    # ── AREA TEST NEUROEVOLUTIVI ──────────────────────────────────────
    elif area == AREA_TEST_NEUROEVOL:
        from .paziente_attivo import header_paziente_attivo
        paz_id = header_paziente_attivo(conn)
        if not paz_id:
            return
        if sotto == "👁️ Valutazione visuo-percettiva":
            try:
                from .ui_valutazione_visuo_percettiva import render_valutazione_visuo_percettiva
                cur2 = conn.cursor()
                cur2.execute("SELECT * FROM Pazienti WHERE id=%s", (paz_id,))
                paz_rec = cur2.fetchone()
                if paz_rec and not isinstance(paz_rec, dict):
                    cols = [d[0] for d in cur2.description]
                    paz_rec = dict(zip(cols, paz_rec))
                render_valutazione_visuo_percettiva(conn, paz_id, paz_rec or {})
            except Exception as e:
                st.error(f"Errore valutazione visuo-percettiva: {e}")
            return
        if sotto == "🧬 INPP — Valutazione diagnostica":
            try:
                from .inpp import render_inpp
                cur2 = conn.cursor()
                cur2.execute("SELECT cognome, nome FROM Pazienti WHERE id=%s", (paz_id,))
                row = cur2.fetchone()
                cur2.close()
                if row:
                    nome = f"{row[0]} {row[1]}".strip()
                else:
                    nome = "Paziente"
                render_inpp(conn, paz_id, nome)
            except Exception as e:
                st.error(f"Errore modulo INPP: {e}")
            return

    # ── AREA TEST LIVE ────────────────────────────────────────────────
    elif area == AREA_TEST_LIVE:
        from .paziente_attivo import header_paziente_attivo
        paz_id = header_paziente_attivo(conn)
        if not paz_id:
            return
        if sotto == "🔢 DEM interattivo":
            try:
                from .gestionale_new_modules import render_nuovi_moduli
                render_nuovi_moduli(conn, "DEM")
            except ImportError as e:
                st.error(f"Modulo DEM non disponibile: {e}")
            return
        if sotto == "👁️ K-D interattivo":
            try:
                from .gestionale_new_modules import render_nuovi_moduli
                render_nuovi_moduli(conn, "KD")
            except ImportError as e:
                st.error(f"Modulo K-D non disponibile: {e}")
            return
        if sotto == "🖥️ Somministrazione test":
            try:
                from .ui_test_somministrazione import render_somministrazione
                render_somministrazione(conn, paz_id)
            except ImportError as e:
                st.error(f"Modulo somministrazione non disponibile: {e}")
            return
        if sotto == "👁️ Eye tracking":
            from .sections.ui_cliniche import render_gaze_section
            render_gaze_section(); return

    # ── AREA QUESTIONARI ──────────────────────────────────────────────
    elif area == AREA_QUESTIONARI:
        if sotto == "📋 Questionari remoti":
            from .paziente_attivo import header_paziente_attivo
            paz_id = header_paziente_attivo(conn)
            if paz_id:
                try:
                    from .ui_questionari import render_questionari_section
                    render_questionari_section(conn, paz_id)
                except ImportError as e:
                    st.error(f"Modulo questionari non disponibile: {e}")
            return
        if sotto == "🎮 Esercizi Wordwall":
            from .paziente_attivo import header_paziente_attivo
            paz_id = header_paziente_attivo(conn)
            if paz_id:
                try:
                    from .ui_wordwall import render_wordwall
                    render_wordwall(conn, paz_id)
                except ImportError as e:
                    st.error(f"Modulo Wordwall non disponibile: {e}")
            return
        if sotto == "👁️ Lenti a contatto":
            from .ui_lenti_contatto import ui_lenti_contatto
            ui_lenti_contatto(); return
        if sotto == "🦴 Osteopatia":
            from .sections.ui_cliniche import render_osteopatia_section
            render_osteopatia_section(); return
        if sotto == "📸 Photoref AI":
            try:
                from .photoref_ai.ui_photoref import ui_photoref
                ui_photoref()
            except ImportError as e:
                st.error(f"Modulo Photoref non disponibile: {e}")
            return

    # ── AREA REPORT & AI ──────────────────────────────────────────────
    elif area == AREA_REPORT_AI:
        if sotto in ("🤖 Relazioni cliniche (AI)", "📝 Relazione clinica"):
            from .paziente_attivo import header_paziente_attivo
            paz_id = header_paziente_attivo(conn)
            if not paz_id:
                return
            try:
                from .ui_relazione_clinica import render_relazione_clinica
                render_relazione_clinica(conn)
            except Exception as e:
                st.error(f"Errore relazione clinica: {e}")
            return
        if sotto in ("🎯 Piano Vision Therapy", "📄 Report PDF con grafici",
                     "📊 Export statistici", "🧪 Caso demo"):
            mappa = {
                "🎯 Piano Vision Therapy":    "PianoVT",
                "📄 Report PDF con grafici":  "ReportPDF",
                "📊 Export statistici":       "ExportStatistici",
                "🧪 Caso demo":               "SeedDemo",
            }
            try:
                from .gestionale_new_modules import render_nuovi_moduli
                paz_id = None
                if sotto in ("🎯 Piano Vision Therapy", "📄 Report PDF con grafici"):
                    from .paziente_attivo import header_paziente_attivo
                    paz_id = header_paziente_attivo(conn)
                    if not paz_id:
                        return
                render_nuovi_moduli(conn, mappa[sotto], paziente_id=paz_id)
            except ImportError as e:
                st.error(f"Modulo non disponibile: {e}")
            return

    # ── AREA AUDIOLOGIA ───────────────────────────────────────────────
    elif area == AREA_AUDIOLOGIA:
        from .paziente_attivo import header_paziente_attivo
        # L'header serve solo per i moduli che richiedono un paziente
        _audio_map = {
            "🔉 Diagnostica uditiva":    ("ui_diagnostica_uditiva",   "ui_diagnostica_uditiva"),
            "🎧 MAPS":                   ("ui_maps",                  "ui_maps"),
            "🗂 Programmi MAPS":         ("ui_programmi",             "ui_programmi"),
            "🧭 Percorsi MAPS":          ("ui_percorsi",              "ui_percorsi"),
            "🎧 Bilancio uditivo":       ("ui_bilancio_uditivo",      "ui_bilancio_uditivo"),
            "📊 Audiometria funzionale": ("ui_audiometria_funzionale","ui_audiometria_funzionale"),
        }
        if sotto in _audio_map:
            paz_id = header_paziente_attivo(conn)
            if not paz_id:
                return
            mod_name, fn_name = _audio_map[sotto]
            try:
                import importlib
                m  = importlib.import_module(f"modules.{mod_name}")
                fn = getattr(m, fn_name)
                try:
                    fn(conn=conn)
                except TypeError:
                    fn()
            except Exception as e_audio:
                st.error(f"Errore {sotto}: {e_audio}")
            return
        if sotto == "📖 Lettura avanzata":
            try:
                from .reading.ui_reading_dom import ui_reading_dom
                ui_reading_dom()
            except ImportError as e:
                st.error(f"Modulo Lettura non disponibile: {e}")
            return

    # ── AREA MARKETING ────────────────────────────────────────────────
    elif area == AREA_MARKETING:
        if sotto == "📅 Eventi e iscrizioni":
            try:
                from .eventi.ui_eventi import render_eventi_section
                render_eventi_section()
            except ImportError as e:
                st.error(f"Modulo Eventi non disponibile: {e}")
            return

    # ── AREA STUDIO ───────────────────────────────────────────────────
    elif area == AREA_STUDIO:
        if sotto == "📊 Dashboard incassi":
            from .sections.ui_cliniche import render_dashboard_section
            render_dashboard_section(); return
        if sotto == "👤 Il mio profilo":
            try:
                from .ui_profilo_professionista import render_profilo_professionista
                render_profilo_professionista(conn)
            except Exception as e:
                st.error(f"Errore profilo: {e}")
            return
        if sotto == "🏥 Il mio studio":
            try:
                from .saas_tenant import render_gestione_studio
                render_gestione_studio(conn,
                                       st.session_state.get("studio_id", 1),
                                       st.session_state.get("piano", "professional"))
            except ImportError as e:
                st.error(f"Modulo Studio non disponibile: {e}")
            return
        if sotto == "👥 Utenti / Ruoli":
            try:
                from .ui_gestione_utenti import render_gestione_utenti
                render_gestione_utenti(conn, is_admin)
            except Exception as e:
                st.error(f"Modulo gestione utenti non disponibile: {e}")
            return
        if sotto == "⚙️ Platform Admin":
            try:
                from .saas_tenant import render_admin_saas
                render_admin_saas(conn)
            except ImportError as e:
                st.error(f"Modulo Admin non disponibile: {e}")
            return
        if sotto == "🐛 Debug DB":
            from .sections.ui_cliniche import render_debug_section
            render_debug_section(); return

    st.warning(f"Sezione '{sotto}' non ancora implementata.")


# ══════════════════════════════════════════════════════════════════════
#  NAVIGAZIONE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

def build_smart_menu(is_admin: bool) -> tuple[str, str]:
    """
    Costruisce il menu a 7 aree nella sidebar.
    Ritorna (area_corrente, sottosezione_corrente).
    """
    # Nasconde la lista automatica delle pagine tecniche (cron, migrazioni,
    # debug — file in pages/) che Streamlit mostra di default in sidebar.
    # Restano raggiungibili dall'admin tramite il pannello qui sotto.
    st.markdown(
        "<style>[data-testid='stSidebarNav']{display:none}</style>",
        unsafe_allow_html=True)

    # ── Tema grafico "Vision Manager" (Wellness Minimal) ──────────────
    # Iniettato una sola volta per sessione: font DM Sans/DM Serif, palette
    # sage/sand, bottoni sidebar grandi con solo il selezionato evidenziato.
    if not st.session_state.get("_pnev_theme_injected"):
        try:
            with open("assets/pnev_theme.css", "r", encoding="utf-8") as _f:
                st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)
        except Exception:
            pass
        st.session_state["_pnev_theme_injected"] = True

    # ── Selezione area ────────────────────────────────────────────────
    st.sidebar.markdown("### The Organism")

    if is_admin:
        with st.sidebar.expander("🛠️ Strumenti tecnici (admin)"):
            st.caption("Script di servizio: cron, migrazioni, debug.")
            _tool_pages = [
                ("cron_promemoria", "Cron promemoria"),
                ("cron_sync_pnev", "Cron sync pnev"),
                ("debug_timezone", "Debug timezone"),
                ("diagnostica_eventi", "Diagnostica eventi"),
                ("firma_pubblica", "Firma pubblica"),
                ("fix_timezone_eventi", "Fix timezone eventi"),
                ("iscrizione_evento", "Iscrizione evento"),
                ("migra_promemoria", "Migra promemoria"),
                ("pnev_pubblico", "Pnev pubblico"),
                ("seed_consensi_costellazioni", "Seed consensi costellazioni"),
            ]
            for slug, etichetta in _tool_pages:
                try:
                    st.page_link(f"pages/{slug}.py", label=etichetta)
                except Exception:
                    st.caption(f"• {etichetta} (pages/{slug}.py)")
        st.sidebar.markdown("---")

    # Salto "in sospeso" richiesto da un'altra pagina (es. ▶️ Apri DEM).
    # Va applicato PRIMA di creare i widget, altrimenti Streamlit blocca
    # la modifica delle chiavi nav_area / nav_sotto_*.
    _goto_a = st.session_state.pop("goto_area", None)
    if _goto_a in AREE_ORDINE:
        st.session_state["nav_area"] = _goto_a
        _goto_s = st.session_state.pop("goto_sotto", None)
        if _goto_s:
            st.session_state[f"nav_sotto_{_goto_a}"] = _goto_s

    area = st.sidebar.radio(
        "Area",
        AREE_ORDINE,
        key="nav_area",
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")

    # ── Area PNEV: selettore di ramo annidato (Child/Visiva/Sensoriale/Uditiva) ──
    from .app_menu import AREA_PNEV, PNEV_RAMI
    if area == AREA_PNEV:
        rami = list(PNEV_RAMI.keys())
        ramo = st.sidebar.radio(
            "Ramo",
            rami,
            key="nav_pnev_ramo",
            label_visibility="visible",
        )
        voci = PNEV_RAMI.get(ramo, [])
        sotto_key = f"nav_sotto_{area}_{ramo}"
        st.sidebar.markdown("---")
    else:
        voci = SOTTOSEZIONI.get(area, [])
        sotto_key = f"nav_sotto_{area}"

    # Filtra admin-only
    if not is_admin:
        voci = [v for v in voci if "Admin" not in v and "Utenti" not in v
                and "Debug" not in v and "demo" not in v.lower()]

    sotto = st.sidebar.radio(
        area,
        voci,
        key=sotto_key,
        label_visibility="visible",
    )

    return area, sotto


def dispatch_smart_section(*, area: str, sotto: str,
                            get_connection: Callable[..., Any],
                            is_admin: bool) -> None:
    """Entry point chiamato da app_core.py."""
    conn = get_connection()
    _render_area(area, sotto, conn, is_admin)


# ══════════════════════════════════════════════════════════════════════
#  COMPATIBILITÀ LEGACY — dispatch_main_section
# ══════════════════════════════════════════════════════════════════════

def dispatch_main_section(*, sezione: str,
                           get_connection: Callable[..., Any]) -> bool:
    """
    Mantiene compatibilità con app_core.py che chiama ancora
    dispatch_main_section. Mappa le sezioni legacy alle nuove aree.
    """
    conn = get_connection()

    # Routing legacy → nuovo sistema
    _legacy_map = {
        "Pazienti":                      (AREA_PAZIENTI,    "👤 Anagrafica pazienti"),
        "Valutazione PNEV":              (AREA_VALUTAZIONE, "🔬 PNEV"),
        "Valutazioni visive / oculistiche": (AREA_VALUTAZIONE, "👁️ Valutazione visuo-percettiva"),
        "Sedute / Terapie":              (AREA_PAZIENTI,    "📅 Sedute / Terapie"),
        "Osteopatia":                    (AREA_QUESTIONARI, "🦴 Osteopatia"),
        "Dashboard incassi":             (AREA_STUDIO,      "📊 Dashboard incassi"),
        "️ Relazioni cliniche":          (AREA_REPORT_AI,   "🤖 Relazioni cliniche (AI)"),
        " Privacy & Consensi (PDF)":     (AREA_PAZIENTI,    "🔒 Privacy & Consensi"),
        "️ Debug DB":                    (AREA_STUDIO,      "🐛 Debug DB"),
        " Import Pazienti":              (AREA_PAZIENTI,    "📥 Import pazienti"),
        " Utenti / Ruoli":               (AREA_STUDIO,      "👥 Utenti / Ruoli"),
        " Eye Tracking":                 (AREA_AUDIOLOGIA,  "👁️ Eye tracking"),
        " Lettura Avanzata DOM":         (AREA_AUDIOLOGIA,  "📖 Lettura avanzata"),
        "🔉 Diagnostica Uditiva":        (AREA_AUDIOLOGIA,  "🔉 Diagnostica uditiva"),
        "🧠 Terapia":                    (AREA_VALUTAZIONE, "⚡ Funzioni esecutive"),
        "🧠 NPS — Valutazione Neuropsicologica": (AREA_VALUTAZIONE, "🧠 NPS — Neuropsicologica"),
        "📚 DSA — Apprendimento":        (AREA_VALUTAZIONE, "📚 DSA — Apprendimento"),
        "🔬 Test Psicologici":           (AREA_VALUTAZIONE, "🔬 Test psicologici"),
        "⚡ Funzioni Esecutive":          (AREA_VALUTAZIONE, "⚡ Funzioni esecutive"),
        "📋 Questionari Remoti":         (AREA_QUESTIONARI, "📋 Questionari remoti"),
        "🖥️ Somministrazione Test":      (AREA_TEST_LIVE,   "🖥️ Somministrazione test"),
        "🔢 DEM Interattivo":            (AREA_TEST_LIVE,   "🔢 DEM interattivo"),
        "👁️ K-D Interattivo":            (AREA_TEST_LIVE,   "👁️ K-D interattivo"),
        "🎯 Piano Vision Therapy":       (AREA_REPORT_AI,   "🎯 Piano Vision Therapy"),
        "📄 Report PDF Clinico":         (AREA_REPORT_AI,   "📄 Report PDF con grafici"),
        "📊 Export Statistici":          (AREA_REPORT_AI,   "📊 Export statistici"),
        "🧪 Caso Demo":                  (AREA_REPORT_AI,   "🧪 Caso demo"),
        "🏥 Il mio studio":              (AREA_STUDIO,      "🏥 Il mio studio"),
        "⚙️ Platform Admin":             (AREA_STUDIO,      "⚙️ Platform Admin"),
        "👁️ Lenti a contatto":           (AREA_QUESTIONARI, "👁️ Lenti a contatto"),
        "📸 Photoref AI":                (AREA_QUESTIONARI, "📸 Photoref AI"),
    }

    if sezione in _legacy_map:
        area, sotto = _legacy_map[sezione]
        _render_area(area, sotto, conn, is_admin=True)
        return True

    return False
