import os
import json
from datetime import datetime
from typing import Dict

from config import SAVE_DIR, NUM_TABLES, SEATS_PER_TABLE, ROUNDS, POINTS_FOR_WIN


def ensure_save_dir():
    """Ensure the save directory exists."""
    os.makedirs(SAVE_DIR, exist_ok=True)


def timestamp():
    """Generate a timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def serialize_state(tournament_state) -> Dict:
    """Build a JSON-serializable snapshot of the whole tournament state."""
    data = {
        "meta": {
            "version": 5,
            "timestamp": timestamp(),
            "config": {
                "NUM_TABLES": NUM_TABLES,
                "SEATS_PER_TABLE": SEATS_PER_TABLE,
                "ROUNDS": ROUNDS,
                "POINTS_FOR_WIN": POINTS_FOR_WIN,
            },
            "tiebreak": "buchholz_wl"  # new variant
        },
        "round_no": tournament_state.round_no,
        "players": tournament_state.players[:],
        "scores": tournament_state.scores.copy(),
        "prev_opponents": {p: sorted(list(s)) for p, s in tournament_state.prev_opponents.items()},
        "prev_tables": {p: sorted(list(s)) for p, s in tournament_state.prev_tables.items()},
        "current_table_pairs": {int(t): list(pair) for t, pair in tournament_state.current_table_pairs.items()},
        "tables_to_decks": {int(t): decks[:] for t, decks in tournament_state.tables_to_decks.items()},
        "tables_to_maps": {int(t): m for t, m in tournament_state.tables_to_maps.items()},
        "match_log": [dict(m) for m in tournament_state.match_log],
    }
    return data


def deserialize_state(data: Dict, tournament_state):
    """Restore state from a JSON snapshot."""
    from collections import defaultdict
    
    tournament_state.round_no = int(data.get("round_no", 0))
    tournament_state.players = list(data.get("players", []))
    tournament_state.scores = {str(k): int(v) for k, v in data.get("scores", {}).items()}

    tournament_state.prev_opponents = defaultdict(
        set, {str(p): set(list(s)) for p, s in data.get("prev_opponents", {}).items()}
    )
    tournament_state.prev_tables = defaultdict(
        set, {str(p): set(list(s)) for p, s in data.get("prev_tables", {}).items()}
    )

    tournament_state.current_table_pairs = {
        int(t): (pair[0], pair[1]) for t, pair in data.get("current_table_pairs", {}).items()
    }
    tournament_state.tables_to_decks = {
        int(t): list(decks) for t, decks in data.get("tables_to_decks", {}).items()
    }
    tournament_state.tables_to_maps = {
        int(t): str(m) for t, m in data.get("tables_to_maps", {}).items()
    }
    tournament_state.match_log = list(data.get("match_log", []))


def autosave(tournament_state, reason: str):
    """Automatic save to SAVE_DIR with unique filename."""
    ensure_save_dir()
    fname = f"{reason}_r{tournament_state.round_no:02d}_{timestamp()}.json"
    path = os.path.join(SAVE_DIR, fname)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serialize_state(tournament_state), f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"Autosave failed: {e}")


def export_to_file(tournament_state, file_path: str):
    """Manual save to specified file path."""
    ensure_save_dir()
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serialize_state(tournament_state), f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"Export failed: {e}")


def import_from_file(file_path: str, tournament_state):
    """Load state from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise Exception(f"Could not read file: {e}")

    try:
        deserialize_state(data, tournament_state)
    except Exception as e:
        raise Exception(f"Invalid state structure: {e}") 