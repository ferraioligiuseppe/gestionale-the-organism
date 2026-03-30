from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


DEFAULT_STORAGE_DIR = Path("data/photoref_mobile")


@dataclass
class SaveInfo:
    original_path: str | None = None
    annotated_path: str | None = None
    db_saved: bool = False
    db_message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_path": self.original_path,
            "annotated_path": self.annotated_path,
            "db_saved": self.db_saved,
            "db_message": self.db_message,
        }


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_token(query_params: Any) -> str:
    token = query_params.get("photoref_token", "")
    if isinstance(token, list):
        token = token[0] if token else ""
    return str(token or "").strip()


def parse_uploaded_image(uploaded) -> tuple[bytes, Image.Image]:
    image_bytes = uploaded.read()
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return image_bytes, pil_image


def get_photoref_session_by_token(token: str, conn=None) -> dict[str, Any] | None:
    """
    Cerca la sessione nel DB se `conn` è disponibile.
    In fallback, restituisce una sessione demo sicura per test UI.
    """
    if not token:
        return None

    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, token, patient_id, visit_id, side, acquisition_type, status, operator, created_at
                    FROM photoref_sessions
                    WHERE token = %s
                    LIMIT 1
                    """,
                    (token,),
                )
                row = cur.fetchone()

            if row:
                cols = [
                    "id",
                    "token",
                    "patient_id",
                    "visit_id",
                    "mode",
                    "acquisition_type",
                    "status",
                    "operator",
                    "created_at",
                ]
                return dict(zip(cols, row))
        except Exception:
            # fallback demo senza rompere il flusso
            pass

    return {
        "id": None,
        "token": token,
        "patient_id": None,
        "visit_id": None,
        "mode": "BINOCULAR",
        "acquisition_type": "photoref",
        "status": "created",
        "operator": None,
        "created_at": utcnow_iso(),
    }


def update_photoref_session_status(token: str, status: str, conn=None) -> None:
    if not token:
        return

    if conn is None:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE photoref_sessions
                SET status = %s,
                    updated_at = NOW(),
                    captured_at = CASE WHEN %s = 'captured' THEN NOW() ELSE captured_at END,
                    analyzed_at = CASE WHEN %s IN ('completed', 'error') THEN NOW() ELSE analyzed_at END
                WHERE token = %s
                """,
                (status, status, status, token),
            )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _basic_quality_score(pil_image: Image.Image) -> float:
    w, h = pil_image.size
    if max(w, h) == 0:
        return 0.0
    aspect_penalty = min(w, h) / max(w, h)
    megapixel_bonus = min((w * h) / 1_000_000.0, 1.0)
    score = round((0.65 * aspect_penalty) + (0.35 * megapixel_bonus), 2)
    return max(0.0, min(1.0, score))


def _build_annotated_preview(pil_image: Image.Image) -> bytes:
    img = pil_image.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    box_w = int(w * 0.45)
    box_h = int(h * 0.28)
    y1 = int(h * 0.34)
    y2 = y1 + box_h
    x1_left = int(w * 0.08)
    x2_left = x1_left + box_w
    x1_right = int(w * 0.47)
    x2_right = x1_right + box_w

    draw.rectangle([x1_left, y1, x2_left, y2], width=4)
    draw.rectangle([x1_right, y1, x2_right, y2], width=4)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def run_photoref_analysis(pil_image: Image.Image, image_bytes: bytes, session_data: dict[str, Any]) -> dict[str, Any]:
    """
    Stub prudente: non sostituisce la tua pipeline reale.
    Restituisce un risultato demo ma strutturato.
    """
    w, h = pil_image.size
    quality = _basic_quality_score(pil_image)
    annotated = _build_annotated_preview(pil_image)

    return {
        "ok": True,
        "algorithm": "demo_stub_v1",
        "quality_score": quality,
        "image_width": w,
        "image_height": h,
        "eyes_detected": True,
        "reflex_detected": True,
        "anisometropia_suspect": False,
        "pupillary_symmetry": "good",
        "notes": "Analisi demo completata. Collegare qui la pipeline Photoref reale.",
        "annotated_image_bytes": annotated,
        "session_mode": session_data.get("mode"),
    }


def _ensure_storage_dir(storage_dir: Path | str | None = None) -> Path:
    base = Path(storage_dir or DEFAULT_STORAGE_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _write_bytes(filepath: Path, data: bytes | None) -> str | None:
    if not data:
        return None
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(data)
    return str(filepath)


def save_photoref_capture(
    token: str,
    session_data: dict[str, Any],
    image_bytes: bytes,
    annotated_image_bytes: bytes | None,
    analysis_result: dict[str, Any],
    source: str,
    conn=None,
    storage_dir: Path | str | None = None,
) -> dict[str, Any]:
    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = _ensure_storage_dir(storage_dir)
    session_folder = base / (token or f"session_{now_tag}")
    session_folder.mkdir(parents=True, exist_ok=True)

    original_path = _write_bytes(session_folder / f"capture_{now_tag}.jpg", image_bytes)
    annotated_path = _write_bytes(session_folder / f"capture_{now_tag}_annotated.png", annotated_image_bytes)
    analysis_json_path = session_folder / f"capture_{now_tag}_analysis.json"

    serializable_result = dict(analysis_result)
    if "annotated_image_bytes" in serializable_result:
        serializable_result["annotated_image_bytes"] = None
    analysis_json_path.write_text(json.dumps(serializable_result, ensure_ascii=False, indent=2), encoding="utf-8")

    save_info = SaveInfo(
        original_path=original_path,
        annotated_path=annotated_path,
        db_saved=False,
        db_message=None,
    )

    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO photoref_captures (
                        session_id,
                        token,
                        source,
                        image_path,
                        annotated_image_path,
                        analysis_json,
                        quality_score,
                        created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s::jsonb, %s, NOW()
                    )
                    """,
                    (
                        session_data.get("id"),
                        token,
                        source,
                        original_path,
                        annotated_path,
                        json.dumps(serializable_result, ensure_ascii=False),
                        analysis_result.get("quality_score"),
                    ),
                )
            conn.commit()
            save_info.db_saved = True
            save_info.db_message = "Capture salvata anche nel DB"
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            save_info.db_saved = False
            save_info.db_message = f"Salvataggio DB saltato: {exc}"

    return save_info.as_dict()
