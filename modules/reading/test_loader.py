
import json
from pathlib import Path

def load_tests():
    path = Path(__file__).parent / "library" / "tests.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

def get_test_by_id(test_id):
    tests = load_tests()
    for t in tests:
        if t["test_id"] == test_id:
            return t
    return None
