"""
Smoke test automatico del Gestionale The Organism.
Apre il gestionale con Playwright, effettua il login, entra in ogni sezione
elencata sotto e controlla che non compaia un errore Streamlit.
Salva uno screenshot per sezione + un report.md con l'esito.

Non richiede terminale: viene eseguito da GitHub Actions (tab "Actions"),
tu lanci il workflow con un click e scarichi i risultati (screenshot + report)
come "artifact" al termine.
"""
import os
import re
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("GESTIONALE_URL", "https://testgestionale.streamlit.app")
USERNAME = os.environ.get("GESTIONALE_TEST_USER", "")
PASSWORD = os.environ.get("GESTIONALE_TEST_PASS", "")

OUT_DIR = "smoke-report"
os.makedirs(OUT_DIR, exist_ok=True)

# Elenco (area, sotto-sezione) da controllare. Aggiungi righe qui se vuoi
# coprire altre voci del menu — il testo deve combaciare con quello mostrato
# nell'interfaccia (emoji comprese).
SEZIONI_DA_CONTROLLARE = [
    ("VALUTAZIONE E TRATTAMENTO MULTISENSORIALE", "Bilancio Uditivo"),
    ("VALUTAZIONE E TRATTAMENTO MULTISENSORIALE", "Audiometria Funzionale"),
    ("VALUTAZIONE E TRATTAMENTO MULTISENSORIALE", "Diagnostica Uditiva"),
    ("OCULISTICA · LAC", "Lenti Inverse"),
    ("OCULISTICA · LAC", "LAC Ametropie"),
    ("OCULISTICA · LAC", "Calcolatore LAC Inversa"),
    ("OCULISTICA · LAC", "ESA Ortho-6"),
    ("VALUTAZIONE E TRATTAMENTO MULTISENSORIALE", "MAPS"),
    ("VALUTAZIONE E TRATTAMENTO MULTISENSORIALE", "Percorsi"),
    ("VALUTAZIONE E TRATTAMENTO MULTISENSORIALE", "Programmi"),
]

ERRORI_STREAMLIT = [
    "This app has encountered an error",
    "Traceback (most recent call last)",
    "StreamlitAPIException",
    "StreamlitDuplicateElementKey",
    "ModuleNotFoundError",
    "KeyError",
    "AttributeError",
]


def screenshot_error_scan(page, label):
    """Ritorna (ok: bool, motivo: str) e salva screenshot."""
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_")[:60]
    path = os.path.join(OUT_DIR, f"{safe}.png")
    page.screenshot(path=path, full_page=True)
    testo = page.locator("body").inner_text()
    for pattern in ERRORI_STREAMLIT:
        if pattern in testo:
            return False, pattern
    return True, ""


def login(page):
    page.goto(APP_URL, timeout=60000)
    page.wait_for_timeout(3000)
    try:
        page.wait_for_selector("input[type='password']", timeout=15000)
    except Exception:
        return True  # forse già loggato o nessun gate di login attivo
    pw_input = page.locator("input[type='password']").first
    text_inputs = page.locator("input[type='text']")
    if text_inputs.count() > 0:
        text_inputs.first.click()
        text_inputs.first.fill(USERNAME)
    pw_input.click()
    pw_input.fill(PASSWORD)
    for label in ["Entra", "Accedi", "Login", "Invia", "Conferma"]:
        btn = page.get_by_role("button", name=re.compile(label, re.IGNORECASE))
        if btn.count() > 0:
            btn.first.click()
            break
    else:
        page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    # Verifica reale: se c'è ancora il campo password, il login NON è riuscito
    ancora_password = page.locator("input[type='password']").count() > 0
    return not ancora_password


def click_nav(page, label, is_gruppo=False):
    """Clicca un elemento di menu che contiene il testo indicato.
    Per i gruppi (es. VALUTAZIONE E TRATTAMENTO MULTISENSORIALE) prova prima
    la freccina ▶ accanto al testo, poi il testo stesso come fallback."""
    if is_gruppo:
        riga = page.locator(f"text={label}").first
        riga.click(timeout=10000)
    else:
        el = page.get_by_text(label, exact=False).first
        el.click(timeout=10000)
    page.wait_for_timeout(2000)


def main():
    if not USERNAME or not PASSWORD:
        print("ATTENZIONE: GESTIONALE_TEST_USER / GESTIONALE_TEST_PASS non impostati nei secrets.")
        sys.exit(1)

    risultati = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        login_ok = login(page)

        ok, motivo = screenshot_error_scan(page, "00_home_dopo_login")
        if not login_ok:
            ok, motivo = False, "LOGIN FALLITO: pagina ancora sul form di login dopo il tentativo — controlla i secret GESTIONALE_TEST_USER/PASS"
        risultati.append(("Home dopo login", ok, motivo))

        if not login_ok:
            # Non ha senso proseguire: senza login tutte le sezioni sarebbero un falso fallimento identico
            browser.close()
            _scrivi_report(risultati)
            sys.exit(1)

        ultimo_gruppo_aperto = None
        for area, sotto in SEZIONI_DA_CONTROLLARE:
            label_completa = f"{area} / {sotto}"
            try:
                if area != ultimo_gruppo_aperto:
                    click_nav(page, area, is_gruppo=True)
                    ultimo_gruppo_aperto = area
                click_nav(page, sotto)
                ok, motivo = screenshot_error_scan(page, label_completa)
                risultati.append((label_completa, ok, motivo))
            except Exception as e:
                risultati.append((label_completa, False, f"click/navigazione fallita: {e}"))
                screenshot_error_scan(page, label_completa + "_ERRORE_NAV")

        browser.close()

    _scrivi_report(risultati)


def _scrivi_report(risultati):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [f"# Smoke test gestionale — {now}", ""]
    n_ok = sum(1 for _, ok, _ in risultati if ok)
    n_tot = len(risultati)
    lines.append(f"**Esito: {n_ok}/{n_tot} sezioni OK**")
    lines.append("")
    for label, ok, motivo in risultati:
        segno = "✅" if ok else "❌"
        riga = f"- {segno} {label}"
        if not ok:
            riga += f" — _{motivo}_"
        lines.append(riga)

    with open(os.path.join(OUT_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    if n_ok < n_tot:
        sys.exit(1)


if __name__ == "__main__":
    main()
