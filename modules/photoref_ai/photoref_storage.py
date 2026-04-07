from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path

def ensure_dirs(base_dir: str) -> dict:
    data_dir = Path(base_dir) / "data"
    upload_dir = data_dir / "uploads"
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return {"data_dir": str(data_dir), "upload_dir": str(upload_dir)}

def build_capture_filename(patient_id: str, visit_id: str, eye_side: str, original_name: str) -> str:
    ext = os.path.splitext(original_name or "")[1].lower() or ".jpg"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"photoref_{str(patient_id or 'NA').replace(' ','_')}_{str(visit_id or 'NA').replace(' ','_')}_{str(eye_side or 'BINOCULAR').replace(' ','_')}_{ts}{ext}"

def save_uploaded_capture(uploaded_file, *, patient_id: str, visit_id: str, eye_side: str, base_dir: str) -> dict:
    dirs = ensure_dirs(base_dir)
    filename = build_capture_filename(patient_id, visit_id, eye_side, getattr(uploaded_file, "name", "capture.jpg"))
    out_path = os.path.join(dirs["upload_dir"], filename)
    content = uploaded_file.getbuffer()
    with open(out_path, "wb") as f:
        f.write(content)
    return {"filename": filename, "storage_path": out_path, "file_size": len(content)}
