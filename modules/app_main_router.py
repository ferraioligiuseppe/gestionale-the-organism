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
    AREA_PAZIENTI, AREA_VALUTAZIONE, AREA_TEST_LIVE,
    AREA_QUESTIONARI, AREA_REPORT_AI, AREA_AUDIOLOGIA, AREA_STUDIO,
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

    # ── Intestazione ─────────────────────────────────────────────────
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

def _render_area(area: str, sotto: str, conn, is_admin: bool) -> None:
    """Dispatch per area + sottosezione."""

    # ── AREA PAZIENTI ─────────────────────────────────────────────────
    if area == AREA_PAZIENTI:
        if sotto == "🏠 Dashboard":
            _render_dashboard(conn)
            return
        if sotto == "👤 Anagrafica pazienti":
            try:
                from .ui_anagrafica import render_anagrafica
                render_anagrafica(conn)
            except Exception:
                try:
                    from .pazienti import render_pazienti_section
                    render_pazienti_section()
                except Exception as e2:
                    st.error(f"Anagrafica non disponibile: {e2}")
            return
        if sotto == "🎟️ Coupon OF / SDS":
            try:
                from modules import app_core
                app_core.ui_coupons()
            except Exception as e:
                st.error(f"Errore coupon: {e}")
            return
        if sotto == "📅 Sedute / Terapie":
            from .sections.ui_cliniche import render_sedute_section
            render_sedute_section(); return
        if sotto == "🔒 Privacy & Consensi":
            from .privacy.ui_privacy_section import render_privacy_section
            render_privacy_section(); return
        if sotto == "📥 Import pazienti":
            from .sections.ui_cliniche import render_import_section
            render_import_section(); return

    # ── AREA VALUTAZIONE ──────────────────────────────────────────────
    elif area == AREA_VALUTAZIONE:
        from .paziente_attivo import header_paziente_attivo
        paz_id = header_paziente_attivo(conn)
        if not paz_id:
            return
        if sotto == "🔬 PNEV":
            from .pnev.ui_pnev import render_pnev_section
            render_pnev_section(); return
        if sotto == "📋 Anamnesi The Organism":
            try:
                from .ui_anamnesi_the_organism import render_anamnesi_the_organism
                render_anamnesi_the_organism(conn, paz_id)
            except Exception as e:
                st.error(f"Modulo anamnesi non disponibile: {e}")
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
        # I moduli audio gestiscono internamente il paziente
        # Proviamo prima con conn, poi senza
        _audio_map = {
            "🔉 Diagnostica uditiva":    ("ui_diagnostica_uditiva",   "ui_diagnostica_uditiva"),
            "🎵 Stimolazione passiva":   ("ui_stimolazione_passiva",  "ui_stimolazione_passiva"),
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
            return
        if sotto == "📖 Lettura avanzata":
            try:
                from .reading.ui_reading_dom import ui_reading_dom
                ui_reading_dom()
            except ImportError as e:
                st.error(f"Modulo Lettura non disponibile: {e}")
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
    # ── Selezione area ────────────────────────────────────────────────
    st.sidebar.markdown("### The Organism")

    area = st.sidebar.radio(
        "Area",
        AREE_ORDINE,
        key="nav_area",
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")

    # ── Sottosezione nell'area ────────────────────────────────────────
    voci = SOTTOSEZIONI.get(area, [])

    # Filtra admin-only
    if not is_admin:
        voci = [v for v in voci if "Admin" not in v and "Utenti" not in v
                and "Debug" not in v and "demo" not in v.lower()]

    sotto = st.sidebar.radio(
        area,
        voci,
        key=f"nav_sotto_{area}",
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
        "🎵 Stimolazione Passiva":       (AREA_AUDIOLOGIA,  "🎵 Stimolazione passiva"),
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
