# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  AGENDA — vista calendari Google di tutti i professionisti           ║
║                                                                      ║
║  Strada 1 ("a vista"): mostra i Google Calendar dei professionisti   ║
║  sovrapposti e colorati. Gli appuntamenti si creano/spostano dentro  ║
║  Google Calendar; qui li vedi tutti insieme. I promemoria email li   ║
║  manda Google in automatico.                                         ║
║                                                                      ║
║  PER AGGIUNGERE UN PROFESSIONISTA: aggiungi una riga a PROFESSIONISTI ║
║  con nome, cal_id (l'ID calendario preso da Google) e un colore.     ║
║  Lascia cal_id = "" per chi non ha ancora l'agenda (non viene        ║
║  mostrato finché non lo compili).                                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import urllib.parse
import streamlit as st
import streamlit.components.v1 as components

CTZ = "Europe/Rome"

# ── Professionisti dello Studio ───────────────────────────────────────
# color = esadecimale SENZA '#'. Verrà passato a Google come %23color.
PROFESSIONISTI = [
    {"nome": "Giuseppe Ferraioli", "ruolo": "Optometria / PNEV",
     "cal_id": "dr.ferraioligiuseppe@gmail.com", "color": "039BE5"},
    {"nome": "Alessandra Munno", "ruolo": "",
     "cal_id": "19f10b52c488e38e35203fb4292ae5674dcd18a3e48a6cd7c19995ff141d50a9@group.calendar.google.com", "color": "0B8043"},
    {"nome": "Mariella Salvatore", "ruolo": "",
     "cal_id": "44e8a5afcc974df13a87209999fd1647c7be15f438b04c7f81abf6c8abb2b533@group.calendar.google.com", "color": "8E24AA"},
    {"nome": "Cirillo Salvatore", "ruolo": "",
     "cal_id": "centro.oculus@gmail.com", "color": "F4511E"},
    {"nome": "Valentina", "ruolo": "Stanza del sale",
     "cal_id": "92eb161615f5ca4eb20539bfe26371936d5b173c422f5de8c705779d2549cb6f@group.calendar.google.com", "color": "F6BF26"},
    {"nome": "Erika D'Auria", "ruolo": "",
     "cal_id": "355c715a188e72f65d544407c24d412f46ae3893db6c00abd6b860169894dfef@group.calendar.google.com", "color": "00897B"},
]

MODI = {
    "Settimana": "WEEK",
    "Giorno": "DAY",
    "Mese": "MONTH",
    "Elenco": "AGENDA",
}


def _build_embed_url(professionisti, mode: str) -> str:
    base = "https://calendar.google.com/calendar/embed?"
    parts = []
    for p in professionisti:
        cid = (p.get("cal_id") or "").strip()
        if not cid:
            continue
        parts.append("src=" + urllib.parse.quote(cid, safe=""))
        parts.append("color=%23" + (p.get("color") or "039BE5"))
    parts.append("ctz=" + urllib.parse.quote(CTZ, safe=""))
    parts.append("mode=" + mode)
    parts.append("wkst=2")          # settimana inizia lunedì
    parts.append("showTitle=0")
    parts.append("showPrint=0")
    parts.append("showCalendars=0")
    parts.append("showTz=0")
    return base + "&".join(parts)


def render_agenda(conn=None, is_admin: bool = False):
    st.header("📅 Agenda appuntamenti")

    attivi = [p for p in PROFESSIONISTI if (p.get("cal_id") or "").strip()]
    mancanti = [p for p in PROFESSIONISTI if not (p.get("cal_id") or "").strip()]

    if not attivi:
        st.warning("Nessun calendario configurato. Aggiungi gli ID calendario in modules/agenda.py.")
        return

    # Barra controlli
    c1, c2 = st.columns([1, 2])
    with c1:
        scelta = st.radio("Vista", list(MODI.keys()), horizontal=True, index=0,
                          key="agenda_mode")
    with c2:
        # Legenda colori professionisti
        chips = []
        for p in attivi:
            chips.append(
                f"<span style='display:inline-block;width:11px;height:11px;"
                f"border-radius:3px;background:#{p['color']};margin:0 6px -1px 12px'></span>"
                f"<span style='font-size:13px'>{p['nome']}"
                + (f" · {p['ruolo']}" if p.get('ruolo') else "") + "</span>"
            )
        st.markdown(
            "<div style='padding-top:6px'>" + "".join(chips) + "</div>",
            unsafe_allow_html=True,
        )

    url = _build_embed_url(attivi, MODI[scelta])
    components.html(
        f'<iframe src="{url}" style="border:0;width:100%;height:720px" '
        f'frameborder="0" scrolling="no"></iframe>',
        height=735,
    )

    st.caption(
        "Gli appuntamenti si creano e si modificano in Google Calendar "
        "(da telefono o computer); qui li vedi tutti insieme. I promemoria "
        "email li invia Google in automatico."
    )

    # ── Apri / modifica in Google Calendar ────────────────────────────
    st.markdown("#### ✏️ Crea o modifica un appuntamento")
    st.link_button(
        "📅 Apri Google Calendar (tutti)",
        "https://calendar.google.com/calendar/r",
        use_container_width=False,
    )
    st.caption("Apre Google Calendar in una nuova scheda: lì aggiungi o sposti gli appuntamenti.")

    with st.expander("Apri l'agenda di un singolo professionista"):
        for p in attivi:
            cid = urllib.parse.quote(p["cal_id"], safe="")
            url_p = f"https://calendar.google.com/calendar/r?cid={cid}"
            st.markdown(
                f"<span style='display:inline-block;width:11px;height:11px;"
                f"border-radius:3px;background:#{p['color']};margin:0 8px -1px 0'></span>"
                f"<a href='{url_p}' target='_blank' style='text-decoration:none'>"
                f"{p['nome']}" + (f" · {p['ruolo']}" if p.get('ruolo') else "") + " ↗</a>",
                unsafe_allow_html=True,
            )

    if mancanti:
        with st.expander(f"➕ Professionisti senza agenda ({len(mancanti)})"):
            st.write(
                "Per aggiungerli servono i loro **ID calendario** Google. "
                "In Google Calendar: tre puntini sul calendario → "
                "Impostazioni e condivisione → *Integra calendario* → "
                "copia **ID calendario**. Poi me lo passi e lo collego."
            )
            for p in mancanti:
                st.write(f"• {p['nome']}" + (f" — {p['ruolo']}" if p.get('ruolo') else ""))
