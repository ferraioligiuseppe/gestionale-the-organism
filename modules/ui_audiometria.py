# -*- coding: utf-8 -*-
"""
modules/ui_audiometria.py

UI Audiometria Tonale con Calibrazione — importa il codice JSON generato da
PNEV-audiometria-v1.html (strumento standalone), mostra l'audiogramma e lo storico.
"""
import json
import streamlit as st

from .db_audiometria import assicura_tabella, salva_esame, lista_esami, elimina_esame

FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]


def _classe(pta):
    if pta is None:
        return "—"
    p = float(pta)
    if p <= 20: return "Normoacusia"
    if p <= 40: return "Ipoacusia lieve"
    if p <= 70: return "Ipoacusia moderata"
    if p <= 90: return "Ipoacusia severa"
    return "Ipoacusia profonda"


def _svg_audiogramma(dati: dict) -> str:
    """Ridisegna l'audiogramma dal JSON salvato (stessa logica del file standalone, in miniatura)."""
    import math
    mL, mR, mT, mB, W, H = 56, 16, 30, 22, 680, 360

    def fx(f):
        return mL + (math.log2(f / 125) / math.log2(8000 / 125)) * (W - mL - mR)

    def fy(db):
        return mT + ((db + 10) / 130) * (H - mT - mB)

    parts = [f'<rect x="{mL}" y="{fy(-10):.1f}" width="{W-mL-mR}" height="{fy(20)-fy(-10):.1f}" fill="#F2F8F4"/>']
    for db in range(-10, 121, 10):
        parts.append(f'<line x1="{mL}" y1="{fy(db):.1f}" x2="{W-mR}" y2="{fy(db):.1f}" '
                      f'stroke="{"#333" if db==0 else "#E3ECE6"}" stroke-width="{1.6 if db==0 else 1}"/>')
        parts.append(f'<text x="{mL-8}" y="{fy(db)+4:.1f}" font-size="11" text-anchor="end" fill="#5B6E63">{db}</text>')
    ottave = [125, 250, 500, 1000, 2000, 4000, 8000]
    for f in FREQS:
        oct_ = f in ottave
        parts.append(f'<line x1="{fx(f):.1f}" y1="{fy(-10):.1f}" x2="{fx(f):.1f}" y2="{fy(120):.1f}" '
                      f'stroke="{"#B9CCC0" if oct_ else "#E3ECE6"}" stroke-width="{1.2 if oct_ else .6}"/>')
        lbl = f"{f//1000}k" if f >= 1000 else str(f)
        parts.append(f'<text x="{fx(f):.1f}" y="{mT-14}" font-size="{11.5 if oct_ else 9.5}" '
                      f'font-weight="{700 if oct_ else 400}" text-anchor="middle" fill="#1C2B23">{lbl}</text>')

    cols = {"od": "#C1272D", "os": "#1B4F9C"}
    for ear_key, ear_data_key in (("od", "od"), ("os", "os")):
        vals = dati.get(ear_data_key) or {}
        pts = []
        for f in FREQS:
            v = vals.get(str(f))
            if v is not None and v != "NR":
                pts.append(f"{fx(f):.1f},{fy(float(v)):.1f}")
        if len(pts) > 1:
            parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{cols[ear_key]}" '
                          f'stroke-width="1.4" opacity=".85"/>')
        for f in FREQS:
            v = vals.get(str(f))
            if v is None:
                continue
            x, nr = fx(f), (v == "NR")
            db = float(v) if not nr else 110
            y = fy(db)
            if ear_key == "od":
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="none" stroke="{cols["od"]}" stroke-width="2.4"/>')
            else:
                parts.append(f'<g stroke="{cols["os"]}" stroke-width="2.4">'
                              f'<line x1="{x-6:.1f}" y1="{y-6:.1f}" x2="{x+6:.1f}" y2="{y+6:.1f}"/>'
                              f'<line x1="{x-6:.1f}" y1="{y+6:.1f}" x2="{x+6:.1f}" y2="{y-6:.1f}"/></g>')
    parts.insert(0, f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;background:#fff;'
                     f'border:1px solid #D8E4DD;border-radius:12px">')
    parts.append("</svg>")
    return "".join(parts)


def render_audiometria(conn, paz_id):
    st.subheader("🎧 Audiometria tonale con calibrazione")
    st.caption("Esame eseguito con lo strumento standalone (calibrato o generico) — incolla qui il codice per salvarlo in cartella.")
    try:
        assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return

    with st.expander("📥 Importa esame (codice JSON)", expanded=True):
        st.caption("Apri lo strumento, esegui l'esame, copia il codice al passo 'Risultati' e incollalo qui.")
        codice = st.text_area("Codice esame", height=110, key=f"aud_import_{paz_id}")
        if st.button("Importa e salva", key=f"aud_import_btn_{paz_id}", type="primary"):
            try:
                dati = json.loads(codice)
                salva_esame(conn, paz_id, dati)
                st.success("Esame importato e salvato.")
                st.rerun()
            except json.JSONDecodeError:
                st.error("Il codice incollato non è valido — controlla di averlo copiato per intero.")
            except Exception as e:
                st.error(f"Errore salvataggio: {e}")

    righe = lista_esami(conn, paz_id)
    if not righe:
        st.info("Nessun esame di audiometria tonale ancora salvato per questo paziente.")
        return

    st.markdown("#### Storico esami")
    for r in righe:
        (eid, modalita, cuffia, calibrazione, pta_od, pta_os, falsi_pos, dati_json, creato_il) = r
        dati = dati_json if isinstance(dati_json, dict) else json.loads(dati_json)
        titolo = f"{creato_il.strftime('%d/%m/%Y %H:%M') if creato_il else ''} — {cuffia or '—'} · {modalita or '—'}"
        with st.expander(titolo, expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("PTA O.D.", f"{pta_od:.0f} dB HL" if pta_od is not None else "—", _classe(pta_od))
            c2.metric("PTA O.S.", f"{pta_os:.0f} dB HL" if pta_os is not None else "—", _classe(pta_os))
            c3.metric("Falsi positivi", falsi_pos if falsi_pos is not None else "—")
            if calibrazione == "generica":
                st.warning("⚠️ Calibrazione generica — soglie orientative (screening), non audiometria funzionale.")
            if dati.get("swap"):
                st.info("Canali hardware invertiti in fase d'esame, corretti via software.")
            retest = dati.get("retest1k") or {}
            for lato, scarto in retest.items():
                if scarto and scarto > 5:
                    st.warning(f"Retest 1000 Hz {'O.D.' if lato=='R' else 'O.S.'}: scarto {scarto} dB (>5) — affidabilità da verificare.")
            st.markdown(_svg_audiogramma(dati), unsafe_allow_html=True)
            if st.button("🗑 Elimina esame", key=f"aud_del_{eid}"):
                try:
                    elimina_esame(conn, eid)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore eliminazione: {e}")
