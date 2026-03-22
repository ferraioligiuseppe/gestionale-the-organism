from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


# =========================================================
# MODELLI DATI
# =========================================================

@dataclass
class VisualMetrics:
    stimulus_name: str = ""
    reading_mode: str = ""  # es. "silenziosa", "ad alta voce"
    viewing_distance_mm: Optional[float] = None

    fixations_total: Optional[int] = None
    fixations_per_min: Optional[float] = None
    fixation_mean_ms: Optional[float] = None
    fixation_sd_ms: Optional[float] = None
    fixation_median_ms: Optional[float] = None

    blinks_total: Optional[int] = None
    blink_rate_min: Optional[float] = None

    saccades_right_total: Optional[int] = None
    regressions_total: Optional[int] = None

    gaze_stability_index: Optional[float] = None
    operator_notes: str = ""


@dataclass
class OrofacialMetrics:
    task_name: str = ""  # es. "lettura standardizzata", "eloquio spontaneo"

    mouth_open_ratio: Optional[float] = None
    left_eye_open_ratio: Optional[float] = None
    right_eye_open_ratio: Optional[float] = None
    palpebral_asymmetry: Optional[float] = None
    head_tilt_deg: Optional[float] = None
    blink_index: Optional[float] = None

    oral_instability_index: Optional[float] = None
    oculo_postural_index: Optional[float] = None
    facial_balance_index: Optional[float] = None

    orbicularis_oculi_involved: bool = True
    frontalis_involved: bool = True
    zygomatic_involved: bool = True
    orbicularis_oris_involved: bool = True
    masseter_involved: bool = True

    operator_notes: str = ""


@dataclass
class IntegratedSession:
    patient_label: str = ""
    patient_id: Optional[int] = None
    session_datetime: str = ""
    operator_name: str = ""
    visual: Optional[VisualMetrics] = None
    orofacial: Optional[OrofacialMetrics] = None


# =========================================================
# HELPERS
# =========================================================

def _fmt_num(v: Any, digits: int = 2, suffix: str = "") -> str:
    if v is None:
        return "n.d."
    try:
        return f"{float(v):.{digits}f}{suffix}"
    except Exception:
        return str(v)


def _safe_int(v: Any) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(v)
    except Exception:
        return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _level_from_index(value: Optional[float], low_thr: float = 0.35, high_thr: float = 0.70) -> str:
    if value is None:
        return "non determinabile"
    if value < low_thr:
        return "basso"
    if value < high_thr:
        return "medio"
    return "elevato"


def _bool_label(flag: bool, yes: str, no: str = "") -> str:
    return yes if flag else no


# =========================================================
# COSTRUZIONE DA PAYLOAD
# =========================================================

def visual_metrics_from_clinical_eye_payload(payload: Dict[str, Any]) -> VisualMetrics:
    """
    Adatta un payload già parsato da Clinical Eye / export simile.
    Le chiavi possono essere adattate in base al tuo import reale.
    """
    return VisualMetrics(
        stimulus_name=str(payload.get("stimulus_name", "")),
        reading_mode=str(payload.get("reading_mode", "")),
        viewing_distance_mm=_safe_float(payload.get("viewing_distance_mm")),

        fixations_total=_safe_int(payload.get("fixations_total")),
        fixations_per_min=_safe_float(payload.get("fixations_per_min")),
        fixation_mean_ms=_safe_float(payload.get("fixation_mean_ms")),
        fixation_sd_ms=_safe_float(payload.get("fixation_sd_ms")),
        fixation_median_ms=_safe_float(payload.get("fixation_median_ms")),

        blinks_total=_safe_int(payload.get("blinks_total")),
        blink_rate_min=_safe_float(payload.get("blink_rate_min")),

        saccades_right_total=_safe_int(payload.get("saccades_right_total")),
        regressions_total=_safe_int(payload.get("regressions_total")),

        gaze_stability_index=_safe_float(payload.get("gaze_stability_index")),
        operator_notes=str(payload.get("operator_notes", "")),
    )


def orofacial_metrics_from_webcam_payload(payload: Dict[str, Any]) -> OrofacialMetrics:
    metrics = payload.get("metrics", {}) or {}
    pnev_indexes = payload.get("pnev_indexes", {}) or {}

    return OrofacialMetrics(
        task_name=str(payload.get("task_name", "lettura standardizzata")),

        mouth_open_ratio=_safe_float(metrics.get("mouth_open_ratio")),
        left_eye_open_ratio=_safe_float(metrics.get("left_eye_open_ratio")),
        right_eye_open_ratio=_safe_float(metrics.get("right_eye_open_ratio")),
        palpebral_asymmetry=_safe_float(metrics.get("palpebral_asymmetry")),
        head_tilt_deg=_safe_float(metrics.get("head_tilt_deg")),
        blink_index=_safe_float(metrics.get("blink_index")),

        oral_instability_index=_safe_float(pnev_indexes.get("oral_instability_index")),
        oculo_postural_index=_safe_float(pnev_indexes.get("oculo_postural_index")),
        facial_balance_index=_safe_float(pnev_indexes.get("facial_balance_index")),

        # qui puoi renderli dinamici in futuro, per ora restano attivi come overlay di base
        orbicularis_oculi_involved=True,
        frontalis_involved=True,
        zygomatic_involved=True,
        orbicularis_oris_involved=True,
        masseter_involved=True,

        operator_notes=str(payload.get("operator_notes", "")),
    )


# =========================================================
# LOGICA INTERPRETATIVA
# =========================================================

def _interpret_visual(v: VisualMetrics) -> str:
    parts: List[str] = []

    if v.gaze_stability_index is not None:
        lvl = _level_from_index(v.gaze_stability_index, 0.45, 0.75)
        if lvl == "elevato":
            parts.append("Si osserva una buona stabilità dello sguardo durante il compito visivo.")
        elif lvl == "medio":
            parts.append("La stabilità dello sguardo risulta discreta ma non costante per tutta la prova.")
        else:
            parts.append("Si rileva una ridotta stabilità dello sguardo, con possibile variabilità del focus visivo.")

    if v.regressions_total is not None:
        if v.regressions_total <= 5:
            parts.append("Le regressioni visive risultano contenute.")
        elif v.regressions_total <= 15:
            parts.append("Si osserva una presenza moderata di regressioni visive.")
        else:
            parts.append("È presente un numero elevato di regressioni visive, da correlare al carico di lettura e all'efficienza della scansione.")

    if v.blink_rate_min is not None:
        if v.blink_rate_min < 10:
            parts.append("La frequenza di ammiccamento appare ridotta.")
        elif v.blink_rate_min <= 25:
            parts.append("La frequenza di ammiccamento rientra in un range compatibile con una buona tenuta del compito.")
        else:
            parts.append("La frequenza di ammiccamento risulta aumentata, elemento da correlare a fatica, regolazione attentiva o stress del compito visivo.")

    if v.fixation_mean_ms is not None:
        if v.fixation_mean_ms < 150:
            parts.append("La durata media delle fissazioni appare breve.")
        elif v.fixation_mean_ms <= 280:
            parts.append("La durata media delle fissazioni appare nel complesso adeguata al compito.")
        else:
            parts.append("La durata media delle fissazioni appare aumentata, con possibile rallentamento del processamento visivo.")

    return " ".join(parts).strip()


def _interpret_orofacial(o: OrofacialMetrics) -> str:
    parts: List[str] = []

    if o.oral_instability_index is not None:
        lvl = _level_from_index(o.oral_instability_index, 0.30, 0.60)
        if lvl == "elevato":
            parts.append("Il distretto orale evidenzia una instabilità funzionale marcata.")
        elif lvl == "medio":
            parts.append("Il distretto orale mostra una moderata variabilità funzionale.")
        else:
            parts.append("Il distretto orale appare nel complesso stabile.")

    if o.facial_balance_index is not None:
        lvl = _level_from_index(o.facial_balance_index, 0.35, 0.70)
        if lvl == "basso":
            parts.append("Si osserva una riduzione del bilanciamento facciale funzionale, con possibile asimmetria espressiva.")
        elif lvl == "medio":
            parts.append("Il bilanciamento facciale appare discreto, con lievi elementi di asimmetria.")
        else:
            parts.append("Il bilanciamento facciale risulta complessivamente conservato.")

    if o.oculo_postural_index is not None:
        lvl = _level_from_index(o.oculo_postural_index, 0.30, 0.60)
        if lvl == "elevato":
            parts.append("L'assetto oculo-posturale appare disorganizzato, con possibile interferenza tra orientamento visivo e stabilizzazione del capo.")
        elif lvl == "medio":
            parts.append("L'assetto oculo-posturale mostra una moderata variabilità.")
        else:
            parts.append("L'assetto oculo-posturale appare nel complesso ben organizzato.")

    if o.mouth_open_ratio is not None:
        if o.mouth_open_ratio > 0.35:
            parts.append("È presente una maggiore apertura orale durante il compito, da correlare alla tenuta del distretto buccale e alla regolazione orale.")
        elif o.mouth_open_ratio > 0.20:
            parts.append("L'apertura orale appare moderata.")
        else:
            parts.append("La tenuta orale appare relativamente contenuta e controllata.")

    return " ".join(parts).strip()


def _muscles_involved_text(o: OrofacialMetrics) -> str:
    muscles: List[str] = []

    if o.orbicularis_oculi_involved:
        muscles.append("Orbicularis oculi, in rapporto alla modulazione palpebrale e al blinking")
    if o.frontalis_involved:
        muscles.append("Frontalis / area glabellare, in rapporto alla stabilizzazione superiore e alla componente attentiva-espressiva")
    if o.zygomatic_involved:
        muscles.append("Zygomaticus area, in rapporto all'organizzazione laterale delle guance e della mimica")
    if o.orbicularis_oris_involved:
        muscles.append("Orbicularis oris, in rapporto alla tenuta labiale e alla regolazione del distretto orale")
    if o.masseter_involved:
        muscles.append("Masseter area, in rapporto alla stabilizzazione mandibolare e alla componente buccale inferiore")

    if not muscles:
        return "Non emergono aree muscolari chiaramente evidenziabili nella sessione corrente."

    return "Le aree muscolari/funzionali maggiormente coinvolte risultano: " + "; ".join(muscles) + "."


def _integrated_pnev_text(v: Optional[VisualMetrics], o: Optional[OrofacialMetrics]) -> str:
    parts: List[str] = []

    if v and o:
        parts.append(
            "L'integrazione tra canale visivo e canale orale-buccale suggerisce di osservare con attenzione il rapporto tra scansione oculare, stabilità del capo e regolazione del distretto orale durante il compito di lettura."
        )

        if (v.regressions_total or 0) > 10 and (o.oral_instability_index or 0) > 0.50:
            parts.append(
                "La compresenza di regressioni visive e di instabilità orale può indicare una difficoltà di integrazione funzionale tra organizzazione oculare e assetto oro-buccale."
            )

        if (v.blink_rate_min or 0) > 25 and (o.oculo_postural_index or 0) > 0.50:
            parts.append(
                "L'aumento dell'ammiccamento associato a variabilità oculo-posturale suggerisce un possibile aumento del carico neuro-funzionale del compito."
            )

        if (v.gaze_stability_index or 0) >= 0.70 and (o.facial_balance_index or 0) >= 0.70:
            parts.append(
                "Nel complesso si osserva una buona tenuta dell'integrazione visivo-facciale durante la prova."
            )

    elif v:
        parts.append(
            "Il quadro disponibile consente una lettura prevalentemente visivo-oculare; si suggerisce integrazione con osservazione oro-facciale per una valutazione PNEV più completa."
        )
    elif o:
        parts.append(
            "Il quadro disponibile consente una lettura prevalentemente oro-facciale; si suggerisce integrazione con metriche visivo-oculari per una valutazione PNEV più completa."
        )
    else:
        parts.append("Dati insufficienti per una sintesi integrata.")

    return " ".join(parts).strip()


# =========================================================
# GENERATORE REFERTI
# =========================================================

def generate_pnev_report(session: IntegratedSession) -> Dict[str, Any]:
    visual = session.visual
    orofacial = session.orofacial

    dt_str = session.session_datetime or datetime.now().strftime("%Y-%m-%d %H:%M")

    visual_text = _interpret_visual(visual) if visual else "Dati visivi non disponibili."
    orofacial_text = _interpret_orofacial(orofacial) if orofacial else "Dati oro-facciali non disponibili."
    muscles_text = _muscles_involved_text(orofacial) if orofacial else "Dati muscolari/funzionali non disponibili."
    integrated_text = _integrated_pnev_text(visual, orofacial)

    lines: List[str] = []
    lines.append("OSSERVAZIONE NEURO-FUNZIONALE COMPUTERIZZATA")
    lines.append("Modulo Eye Tracking / Lettura integrata – approccio PNEV")
    lines.append("")
    lines.append(f"Paziente: {session.patient_label or 'n.d.'}")
    lines.append(f"ID paziente: {session.patient_id if session.patient_id is not None else 'n.d.'}")
    lines.append(f"Data sessione: {dt_str}")
    lines.append(f"Operatore: {session.operator_name or 'n.d.'}")
    lines.append("")

    lines.append("1. CANALE VISIVO / OCULARE")
    if visual:
        lines.append(f"- Stimolo: {visual.stimulus_name or 'n.d.'}")
        lines.append(f"- Modalità di lettura: {visual.reading_mode or 'n.d.'}")
        lines.append(f"- Distanza di visione: {_fmt_num(visual.viewing_distance_mm, 0, ' mm')}")
        lines.append(f"- Fissazioni totali: {visual.fixations_total if visual.fixations_total is not None else 'n.d.'}")
        lines.append(f"- Fissazioni/min: {_fmt_num(visual.fixations_per_min, 1)}")
        lines.append(f"- Durata media fissazioni: {_fmt_num(visual.fixation_mean_ms, 0, ' ms')}")
        lines.append(f"- Deviazione standard fissazioni: {_fmt_num(visual.fixation_sd_ms, 0)}")
        lines.append(f"- Mediana fissazioni: {_fmt_num(visual.fixation_median_ms, 0, ' ms')}")
        lines.append(f"- Blinks totali: {visual.blinks_total if visual.blinks_total is not None else 'n.d.'}")
        lines.append(f"- Blink rate: {_fmt_num(visual.blink_rate_min, 1, '/min')}")
        lines.append(f"- Saccadi verso destra: {visual.saccades_right_total if visual.saccades_right_total is not None else 'n.d.'}")
        lines.append(f"- Regressioni: {visual.regressions_total if visual.regressions_total is not None else 'n.d.'}")
        lines.append(f"- Gaze stability index: {_fmt_num(visual.gaze_stability_index, 3)}")
        lines.append("")
        lines.append(visual_text)
        if visual.operator_notes:
            lines.append(f"Note operatore (visivo): {visual.operator_notes}")
    else:
        lines.append("Dati visivi non disponibili.")
    lines.append("")

    lines.append("2. CANALE ORALE / BUCCALE / MIMICO")
    if orofacial:
        lines.append(f"- Task: {orofacial.task_name or 'n.d.'}")
        lines.append(f"- Mouth open ratio: {_fmt_num(orofacial.mouth_open_ratio, 3)}")
        lines.append(f"- Left eye open ratio: {_fmt_num(orofacial.left_eye_open_ratio, 3)}")
        lines.append(f"- Right eye open ratio: {_fmt_num(orofacial.right_eye_open_ratio, 3)}")
        lines.append(f"- Palpebral asymmetry: {_fmt_num(orofacial.palpebral_asymmetry, 3)}")
        lines.append(f"- Head tilt: {_fmt_num(orofacial.head_tilt_deg, 1, '°')}")
        lines.append(f"- Blink index: {_fmt_num(orofacial.blink_index, 0)}")
        lines.append(f"- Oral instability index: {_fmt_num(orofacial.oral_instability_index, 3)}")
        lines.append(f"- Oculo-postural index: {_fmt_num(orofacial.oculo_postural_index, 3)}")
        lines.append(f"- Facial balance index: {_fmt_num(orofacial.facial_balance_index, 3)}")
        lines.append("")
        lines.append(orofacial_text)
        lines.append(muscles_text)
        if orofacial.operator_notes:
            lines.append(f"Note operatore (orale/buccale): {orofacial.operator_notes}")
    else:
        lines.append("Dati oro-facciali non disponibili.")
    lines.append("")

    lines.append("3. INTEGRAZIONE PNEV")
    lines.append(integrated_text)
    lines.append("")
    lines.append("4. CONCLUSIONE")
    lines.append(
        "Il presente output ha valore osservativo neuro-funzionale e va integrato con la valutazione clinica diretta, con l'osservazione del comportamento del paziente e con eventuali misure strumentali dedicate."
    )

    report_text = "\n".join(lines)

    return {
        "patient_id": session.patient_id,
        "patient_label": session.patient_label,
        "session_datetime": dt_str,
        "operator_name": session.operator_name,
        "visual_metrics": asdict(visual) if visual else None,
        "orofacial_metrics": asdict(orofacial) if orofacial else None,
        "visual_interpretation": visual_text,
        "orofacial_interpretation": orofacial_text,
        "muscles_involved_text": muscles_text,
        "integrated_pnev_text": integrated_text,
        "report_text": report_text,
    }


# =========================================================
# ESEMPIO USO
# =========================================================

def build_report_from_payloads(
    patient_label: str,
    patient_id: Optional[int],
    operator_name: str,
    clinical_eye_payload: Optional[Dict[str, Any]] = None,
    webcam_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    visual = visual_metrics_from_clinical_eye_payload(clinical_eye_payload or {}) if clinical_eye_payload else None
    orofacial = orofacial_metrics_from_webcam_payload(webcam_payload or {}) if webcam_payload else None

    session = IntegratedSession(
        patient_label=patient_label,
        patient_id=patient_id,
        session_datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
        operator_name=operator_name,
        visual=visual,
        orofacial=orofacial,
    )
    return generate_pnev_report(session)
