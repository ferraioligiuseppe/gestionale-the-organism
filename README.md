# The Organism UI Kit v2 — Modulo Visivo (Streamlit)

Questa versione è più aggressiva: sidebar più pulita, tabs a pillola, cards con shadow,
e CTA verde come nel mockup.

## Copia nel repo (root)
- `.streamlit/config.toml`
- `assets/ui.css`
- `vision_manager/ui_kit.py`

## Uso
In cima alla tua pagina:
```python
from vision_manager.ui_kit import inject_ui, topbar
inject_ui("assets/ui.css")
topbar("Vision Manager", "Visita visiva • UI The Organism", right="Dr. Cirillo")
```

Poi avvolgi le sezioni:
```python
from vision_manager.ui_kit import card_open, card_close
card_open("Pressione endoculare (IOP)", "OD/OS e metodo", "🧿")
# widget...
card_close()
```

## Demo
`vision_manager/ui_demo_visiva.py` contiene una demo visuale (non collegata al DB).
