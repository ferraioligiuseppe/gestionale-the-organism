# The Organism UI Kit (Streamlit) — Modulo Visivo

## File inclusi
- `.streamlit/config.toml` → tema globale (verde The Organism)
- `assets/ui.css` → CSS globale (card, topbar, input rounded)
- `vision_manager/ui_kit.py` → componenti riusabili
- `vision_manager/ui_demo_visiva.py` → demo pronta

## Integrazione rapida
1) Copia nel root del repo:
- `.streamlit/`
- `assets/`
- `vision_manager/ui_kit.py`
- (opzionale) `vision_manager/ui_demo_visiva.py`

2) All’inizio della tua pagina Streamlit:
```python
from vision_manager.ui_kit import inject_ui
inject_ui("assets/ui.css")
```

3) Crea sezioni/card:
```python
from vision_manager.ui_kit import card_open, card_close
card_open("Pressione Endoculare (IOP)", "OD/OS e metodo", "👁️")
# ... widget Streamlit ...
card_close()
```
