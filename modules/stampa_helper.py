# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  STAMPA HELPER — scheda stampabile generica, riutilizzabile           ║
║                                                                        ║
║  Una funzione sola per generare un foglio pulito (HTML, carta         ║
║  intestata leggera) da qualunque schermata: anagrafica, valutazioni,  ║
║  test. Il clinico scarica il file e lo stampa dal browser (Cmd/Ctrl+P)║
║  — stesso schema già usato per le schede Getman/Groffman.             ║
║                                                                        ║
║  USO:                                                                  ║
║    from modules.stampa_helper import scheda_stampabile_html, bottone_stampa
║    html = scheda_stampabile_html("Titolo", "Sottotitolo", [            ║
║        ("Sezione 1", [("Campo", "Valore"), ...]),                     ║
║        ("Sezione 2", [...]),                                          ║
║    ])                                                                  ║
║    bottone_stampa(html, "scheda_mario_rossi", key="stampa_x")          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import html as _html
import streamlit as st

_CSS = """<style>
@page{size:A4;margin:16mm}
body{font-family:Georgia,'Times New Roman',serif;color:#1a1a1a;margin:0}
.hdr{border-bottom:2px solid #1a1a1a;padding-bottom:8px;margin-bottom:16px}
.hdr .studio{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:#6b6b6b}
h1{font-size:21px;margin:2px 0 2px}
.sub{font-size:13px;color:#555;margin-bottom:4px}
h2{font-size:15px;margin:18px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px}
table{border-collapse:collapse;width:100%;margin:4px 0}
td{padding:5px 8px;font-size:13px;vertical-align:top}
td.k{width:34%;color:#555;font-weight:bold}
td.v{width:66%}
.foot{margin-top:26px;padding-top:10px;border-top:1px solid #ccc;font-size:11px;color:#777}
</style>"""


def scheda_stampabile_html(titolo: str, sottotitolo: str, sezioni,
                           studio: str = "Studio The Organism · Metodo PNEV") -> str:
    """sezioni: lista di (intestazione_sezione, [(campo, valore), ...])."""
    corpo = ""
    for intest, campi in sezioni:
        if not campi:
            continue
        righe = "".join(
            f"<tr><td class='k'>{_html.escape(str(k))}</td>"
            f"<td class='v'>{_html.escape(str(v)) if v not in (None, '') else '&nbsp;'}</td></tr>"
            for k, v in campi
        )
        corpo += f"<h2>{_html.escape(intest)}</h2><table>{righe}</table>"
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>{_html.escape(titolo)}</title>{_CSS}</head><body>
<div class="hdr">
  <div class="studio">{_html.escape(studio)}</div>
  <h1>{_html.escape(titolo)}</h1>
  <div class="sub">{_html.escape(sottotitolo)}</div>
</div>
{corpo}
<div class="foot">Documento generato dal gestionale — uso clinico interno.</div>
</body></html>"""


def bottone_stampa(html_content: str, nome_file: str, key: str,
                   etichetta: str = "🖨️ Stampa / scarica scheda"):
    """Pulsante di download universale per una scheda stampabile."""
    st.download_button(etichetta, data=html_content,
                       file_name=f"{nome_file}.html", mime="text/html",
                       key=key, use_container_width=True)
