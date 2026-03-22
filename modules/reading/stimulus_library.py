
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional

import streamlit as st

LIB_ROOT = Path(__file__).parent / "library"
TEXT_DIR = LIB_ROOT / "texts"
PDF_DIR = LIB_ROOT / "pdf"
IMAGE_DIR = LIB_ROOT / "images"

SUPPORTED_TEXT = {".txt", ".json"}
SUPPORTED_PDF = {".pdf"}
SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".webp"}

for _p in [TEXT_DIR, PDF_DIR, IMAGE_DIR]:
    _p.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_", ".", " "):
            keep.append(ch)
        else:
            keep.append("_")
    clean = "".join(keep).strip().replace("..", "_")
    return clean or "file"


def get_target_dir(filename: str) -> Path:
    ext = Path(filename).suffix.lower()
    if ext in SUPPORTED_TEXT:
        return TEXT_DIR
    if ext in SUPPORTED_PDF:
        return PDF_DIR
    if ext in SUPPORTED_IMAGE:
        return IMAGE_DIR
    raise ValueError(f"Formato non supportato: {ext}")


def save_uploaded_file(uploaded_file) -> Path:
    safe_name = _safe_name(uploaded_file.name)
    target_dir = get_target_dir(safe_name)
    target = target_dir / safe_name
    target.write_bytes(uploaded_file.getbuffer())
    return target


def list_stimuli() -> List[Dict]:
    items: List[Dict] = []
    for folder, stype in [(TEXT_DIR, "text"), (PDF_DIR, "pdf"), (IMAGE_DIR, "image")]:
        for fp in sorted(folder.glob("*")):
            if not fp.is_file():
                continue
            items.append(
                {
                    "id": fp.stem,
                    "title": fp.stem.replace("_", " "),
                    "filename": fp.name,
                    "path": str(fp),
                    "type": stype,
                    "ext": fp.suffix.lower(),
                    "size_kb": round(fp.stat().st_size / 1024, 1),
                }
            )
    return items


def delete_stimulus(filename: str) -> bool:
    for folder in [TEXT_DIR, PDF_DIR, IMAGE_DIR]:
        fp = folder / filename
        if fp.exists() and fp.is_file():
            fp.unlink()
            return True
    return False


def get_stimulus_by_filename(filename: str) -> Optional[Dict]:
    for item in list_stimuli():
        if item["filename"] == filename:
            return item
    return None


def load_text_content(filename: str) -> str:
    item = get_stimulus_by_filename(filename)
    if not item:
        return ""

    fp = Path(item["path"])
    if item["ext"] == ".txt":
        return fp.read_text(encoding="utf-8")

    if item["ext"] == ".json":
        data = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return str(data.get("content", ""))
        if isinstance(data, list):
            return "\n".join(str(x) for x in data)
        return str(data)

    return ""


def render_library_manager():
    st.markdown("### Libreria stimoli")
    st.caption("Puoi caricare file dall'esterno e cancellarli direttamente dal gestionale.")

    uploaded = st.file_uploader(
        "Carica uno o più file",
        type=["txt", "json", "pdf", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="reading_library_uploads",
    )

    if uploaded:
        saved = []
        errors = []
        for up in uploaded:
            try:
                fp = save_uploaded_file(up)
                saved.append(fp.name)
            except Exception as e:
                errors.append(f"{up.name}: {e}")

        if saved:
            st.success(f"Caricati {len(saved)} file: " + ", ".join(saved))
        if errors:
            for err in errors:
                st.error(err)

    items = list_stimuli()
    if not items:
        st.info("La libreria è ancora vuota.")
        return

    st.markdown("#### Elenco file")
    for item in items:
        c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
        with c1:
            st.write(f"**{item['title']}**  —  {item['filename']}")
            st.caption(f"Tipo: {item['type']} | Estensione: {item['ext']} | Dimensione: {item['size_kb']} KB")
        with c2:
            fp = Path(item["path"])
            st.download_button(
                "Scarica",
                data=fp.read_bytes(),
                file_name=fp.name,
                mime="application/octet-stream",
                key=f"dl_{fp.name}",
            )
        with c3:
            if item["type"] == "text":
                st.caption("DOM ok")
            elif item["type"] == "pdf":
                st.caption("Preview")
            else:
                st.caption("Immagine")
        with c4:
            if st.button("Cancella", key=f"del_{item['filename']}"):
                ok = delete_stimulus(item["filename"])
                if ok:
                    st.success(f"Eliminato: {item['filename']}")
                    st.rerun()
                else:
                    st.error("File non trovato.")
