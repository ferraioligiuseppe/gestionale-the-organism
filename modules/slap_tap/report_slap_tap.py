def build_slap_tap_report(scoring):
    accuracy = 0
    results = []

    if isinstance(scoring, dict):
        accuracy = scoring.get("accuracy", 0)
        results = scoring.get("results", []) or []

    lines = [
        "SLAP TAP REPORT",
        "",
        f"Accuratezza: {accuracy}%",
        f"Numero prove: {len(results)}",
        "",
    ]

    if results:
        lines.append("Dettaglio:")
        for row in results:
            idx = row.get("index", 0) + 1
            expected = row.get("expected", "-")
            actual = row.get("actual", "-")
            correct = "OK" if row.get("correct") else "ERRORE"
            lines.append(f"- Pos {idx}: atteso={expected} | risposta={actual} | {correct}")

    return "\n".join(lines)
