import random
import time
from typing import Optional

from modules.slap_tap.config_slap_tap import VALID_LETTERS, LETTER_MAPPING


def generate_sequence(length: int = 4, allow_repetitions: bool = True) -> list[str]:
    if length <= 0:
        return []

    if allow_repetitions:
        return [random.choice(VALID_LETTERS) for _ in range(length)]

    seq = []
    pool = VALID_LETTERS[:]
    while len(seq) < length:
        random.shuffle(pool)
        seq.extend(pool)
    return seq[:length]


def parse_operator_input(input_str: str) -> list[str]:
    if not input_str:
        return []
    tokens = input_str.lower().replace(",", " ").split()
    return [t for t in tokens if t in VALID_LETTERS]


def classify_error(expected: str, actual: Optional[str]) -> str:
    if actual is None:
        return "omissione"

    if actual == expected:
        return ""

    exp_meta = LETTER_MAPPING.get(expected, {})
    act_meta = LETTER_MAPPING.get(actual, {})

    if not exp_meta or not act_meta:
        return "errore_generico"

    same_segment = exp_meta.get("segment") == act_meta.get("segment")
    same_side = exp_meta.get("side") == act_meta.get("side")

    if same_segment and not same_side:
        return "errore_lateralita"

    if same_side and not same_segment:
        return "errore_segmento"

    return "errore_generico"


def evaluate_response(expected: list[str], actual: list[str]) -> dict:
    results = []
    n = len(expected)

    for i in range(n):
        exp = expected[i]
        act = actual[i] if i < len(actual) else None
        correct = act == exp
        error_type = "" if correct else classify_error(exp, act)

        results.append({
            "index": i,
            "expected": exp,
            "actual": act,
            "correct": correct,
            "error_type": error_type,
        })

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = round((correct_count / n) * 100, 2) if n else 0.0

    return {
        "results": results,
        "correct_count": correct_count,
        "total": n,
        "accuracy": accuracy,
    }


def expected_tick_times(start_ts: float, bpm: int, n_items: int, mode: str) -> list[float]:
    """
    mode:
      - '1:1' -> un movimento a ogni battito
      - '1:2' -> un movimento un battito sì e uno no
    """
    if bpm <= 0:
        bpm = 60

    interval = 60.0 / bpm
    times = []

    if mode == "1:2":
        for i in range(n_items):
            times.append(start_ts + (i * 2 * interval))
    else:
        for i in range(n_items):
            times.append(start_ts + (i * interval))

    return times


def compute_timing_errors(
    expected_times: list[float],
    actual_times: list[float],
    tolerance_ms: int = 350,
) -> list[dict]:
    tolerance_s = tolerance_ms / 1000.0
    out = []

    for i, exp_t in enumerate(expected_times):
        act_t = actual_times[i] if i < len(actual_times) else None

        if act_t is None:
            out.append({
                "index": i,
                "timing_label": "mancata_risposta",
                "delta_ms": None,
                "in_tolerance": False,
            })
            continue

        delta = act_t - exp_t
        in_tol = abs(delta) <= tolerance_s

        if in_tol:
            label = "in_tempo"
        elif delta < 0:
            label = "anticipo"
        else:
            label = "ritardo"

        out.append({
            "index": i,
            "timing_label": label,
            "delta_ms": int(delta * 1000),
            "in_tolerance": in_tol,
        })

    return out


def merge_scoring(symbol_eval: dict, timing_eval: list[dict]) -> dict:
    merged = []
    results = symbol_eval["results"]

    for i, r in enumerate(results):
        t = timing_eval[i] if i < len(timing_eval) else {
            "timing_label": "",
            "delta_ms": None,
            "in_tolerance": False,
        }

        merged.append({
            **r,
            "timing_label": t["timing_label"],
            "delta_ms": t["delta_ms"],
            "in_tolerance": t["in_tolerance"],
        })

    timing_ok = sum(1 for x in merged if x["in_tolerance"])
    timing_accuracy = round((timing_ok / len(merged)) * 100, 2) if merged else 0.0

    return {
        "rows": merged,
        "symbol_accuracy": symbol_eval["accuracy"],
        "timing_accuracy": timing_accuracy,
        "correct_symbols": symbol_eval["correct_count"],
        "total": symbol_eval["total"],
    }


def now_ts() -> float:
    return time.time()
