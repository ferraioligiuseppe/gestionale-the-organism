
from __future__ import annotations

def build_report_summary(report: dict) -> str:
    parts = []
    if report.get("distance_mean_cm") is not None:
        parts.append(f"Distanza media: {report['distance_mean_cm']} cm")
    if report.get("tracking_loss_pct") is not None:
        parts.append(f"Tracking loss: {report['tracking_loss_pct']}%")
    if report.get("target_hit_rate") is not None:
        parts.append(f"Target hit rate: {report['target_hit_rate']}%")
    return " | ".join(parts)
