import random
import copy
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Optional

from config import NUM_TABLES, SEATS_PER_TABLE, ROUNDS, POINTS_FOR_WIN, DEFAULT_DECK_POOL, DEFAULT_MAPS
from swiss_logic import (
    swiss_make_pairs, assign_tables_avoiding_repeats, deal_tables, deal_maps,
    compute_buchholz_wl, head_to_head
)


class TournamentState:
    """Manages all tournament state and provides operations on that state."""
    
    def __init__(self):
        self.rng = random.Random()
        
        # Core state
        self.players: List[str] = []
        self.scores: Dict[str, int] = {}
        self.prev_opponents: Dict[str, Set[str]] = defaultdict(set)
        self.prev_tables: Dict[str, Set[int]] = defaultdict(set)
        self.round_no = 0
        self.current_table_pairs: Dict[int, Tuple[str, str]] = {}
        self.tables_to_decks: Dict[int, List[str]] = {}
        self.tables_to_maps: Dict[int, str] = {}
        
        # Match log for tiebreaks: list of dicts {round, table, a, b, winner}
        self.match_log: List[Dict] = []
        
        # Undo history (for last submitted round)
        self.history: List[Dict] = []
    
    def reset(self):
        """Reset tournament to empty state."""
        self.players = []
        self.scores.clear()
        self.prev_opponents.clear()
        self.prev_tables.clear()
        self.current_table_pairs.clear()
        self.tables_to_decks.clear()
        self.tables_to_maps.clear()
        self.history.clear()
        self.match_log.clear()
        self.round_no = 0
    
    def set_seed(self, seed):
        """Set random seed for reproducible tournaments."""
        if seed:
            try:
                self.rng.seed(int(seed))
            except ValueError:
                self.rng.seed(seed)
    
    def add_player(self, name: str) -> bool:
        """Add a player. Returns True if successful, False if already exists or at capacity."""
        if name in self.players:
            return False
        if len(self.players) >= NUM_TABLES * SEATS_PER_TABLE:
            return False
        self.players.append(name)
        return True
    
    def remove_player(self, name: str) -> bool:
        """Remove a player. Returns True if successful, False if not found or tournament started."""
        if self.round_no > 0:
            return False
        if name in self.players:
            self.players.remove(name)
            return True
        return False
    
    def can_start_tournament(self) -> Tuple[bool, str]:
        """Check if tournament can start. Returns (can_start, error_message)."""
        if len(self.players) == 0:
            return False, "Add players first."
        if len(self.players) % 2 == 1:
            return False, "Number of players must be EVEN (2 per table)."
        max_players = NUM_TABLES * SEATS_PER_TABLE
        if len(self.players) > max_players:
            return False, f"Max {max_players} players (12 tables × 2)."
        return True, ""
    
    def start_tournament(self):
        """Initialize tournament state."""
        can_start, error = self.can_start_tournament()
        if not can_start:
            raise ValueError(error)
        
        # Initialize state
        self.scores = {p: 0 for p in self.players}
        self.prev_opponents = defaultdict(set)
        self.prev_tables = defaultdict(set)
        self.match_log = []
        self.round_no = 0
        self.history.clear()
        
        # Deal decks and maps to tables ONCE
        self.tables_to_decks = deal_tables(DEFAULT_DECK_POOL, num_tables=NUM_TABLES, decks_per_table=4, rng=self.rng)
        self.tables_to_maps = deal_maps(DEFAULT_MAPS, num_tables=NUM_TABLES, rng=self.rng)
    
    def can_pair_next_round(self) -> Tuple[bool, str]:
        """Check if next round can be paired. Returns (can_pair, error_message)."""
        if self.round_no >= ROUNDS:
            return False, "All rounds completed."
        return True, ""
    
    def pair_next_round(self) -> Tuple[List[Tuple[str, int]], bool]:
        """
        Pair the next round.
        Returns (forced_table_repeats, success).
        forced_table_repeats is a list of (player, table) tuples for unavoidable repeats.
        """
        can_pair, error = self.can_pair_next_round()
        if not can_pair:
            raise ValueError(error)
        
        pairs = swiss_make_pairs(self.players, self.scores, self.prev_opponents, rng=self.rng)
        table_pairs, forced = assign_tables_avoiding_repeats(pairs, self.prev_tables, rng=self.rng)
        
        self.current_table_pairs = table_pairs
        self.round_no += 1
        
        return forced, True
    
    def can_submit_results(self, winners: Dict[int, str]) -> Tuple[bool, str]:
        """Check if results can be submitted. Returns (can_submit, error_message)."""
        if not self.current_table_pairs:
            return False, "No active round to submit."
        
        for t, (a, b) in self.current_table_pairs.items():
            if t not in winners or winners[t] not in (a, b):
                return False, f"Select winner for Table {t}."
        return True, ""
    
    def snapshot_before_submit(self):
        """Save a deep snapshot BEFORE applying results for undo."""
        snap = {
            "round_no": self.round_no,
            "scores": copy.deepcopy(self.scores),
            "prev_opponents": {p: list(s) for p, s in self.prev_opponents.items()},
            "prev_tables": {p: list(s) for p, s in self.prev_tables.items()},
            "current_table_pairs": copy.deepcopy(self.current_table_pairs),
            "players": self.players[:],
            "tables_to_decks": copy.deepcopy(self.tables_to_decks),
            "tables_to_maps": copy.deepcopy(self.tables_to_maps),
            "match_log": copy.deepcopy(self.match_log),
        }
        self.history.append(snap)
    
    def submit_results(self, winners: Dict[int, str]):
        """Submit results for current round."""
        can_submit, error = self.can_submit_results(winners)
        if not can_submit:
            raise ValueError(error)
        
        # Apply results + append to match_log
        for t, (a, b) in self.current_table_pairs.items():
            w = winners[t]
            self.scores[w] += POINTS_FOR_WIN
            self.prev_opponents[a].add(b)
            self.prev_opponents[b].add(a)
            self.prev_tables[a].add(t)
            self.prev_tables[b].add(t)
            self.match_log.append({"round": self.round_no, "table": t, "a": a, "b": b, "winner": w})
        
        self.current_table_pairs = {}
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self.history) > 0
    
    def undo_last_round(self):
        """Revert to the state BEFORE the last submitted round."""
        if not self.can_undo():
            raise ValueError("Nothing to undo.")
        
        snap = self.history.pop()
        
        # Restore state
        self.round_no = snap["round_no"]
        self.scores = snap["scores"]
        self.prev_opponents = defaultdict(set, {p: set(s) for p, s in snap["prev_opponents"].items()})
        self.prev_tables = defaultdict(set, {p: set(s) for p, s in snap["prev_tables"].items()})
        self.current_table_pairs = snap["current_table_pairs"]
        self.players = snap.get("players", self.players)
        self.tables_to_decks = snap.get("tables_to_decks", self.tables_to_decks)
        self.tables_to_maps = snap.get("tables_to_maps", self.tables_to_maps)
        self.match_log = snap.get("match_log", self.match_log)
    
    def get_sorted_standings(self) -> List[Tuple[str, int, int]]:
        """
        Return [(player, score, buchholz_wl)] sorted by:
            Score desc, Buchholz(W-L) desc, Head-to-Head, Name
        """
        buch = compute_buchholz_wl(self.players, self.match_log)
        rows = [(p, self.scores.get(p, 0), buch.get(p, 0)) for p in self.players]
        
        # Pre-sort by score, buchholz, name; then apply H2H swaps for exact ties
        rows.sort(key=lambda x: (-x[1], -x[2], x[0]))
        
        i = 0
        while i < len(rows) - 1:
            p1, s1, b1 = rows[i]
            p2, s2, b2 = rows[i+1]
            if s1 == s2 and b1 == b2:
                winner = head_to_head(p1, p2, self.match_log)
                if winner == p2:
                    rows[i], rows[i+1] = rows[i+1], rows[i]  # swap so winner goes above
                    if i > 0:
                        i -= 1
                        continue
            i += 1
        return rows
    
    def assign_places(self, rows: List[Tuple[str, int, int]]) -> List[Tuple[int, str, int, int]]:
        """
        Convert sorted rows into [(place, player, score, buchholz_wl)] with competition ranking.
        Players tie (share the same place) iff:
          - score equal, and
          - buchholz_wl equal, and
          - NO head-to-head result between adjacent tied players.
        """
        out = []
        if not rows:
            return out
        
        # helper to check if two players have an H2H result
        def has_h2h_result(a: str, b: str) -> bool:
            res = head_to_head(a, b, self.match_log)
            return res in (a, b)
        
        # first entry
        place = 1
        out.append((place, rows[0][0], rows[0][1], rows[0][2]))
        
        # others
        for idx in range(1, len(rows)):
            p, s, b = rows[idx]
            p_prev, s_prev, b_prev = rows[idx-1]
            
            # same score & buchholz?
            if s == s_prev and b == b_prev:
                # if there is NO H2H between them, they share place
                if not has_h2h_result(p, p_prev):
                    out.append((place, p, s, b))
                    continue
            
            # otherwise new place is index+1 (competition ranking)
            place = idx + 1
            out.append((place, p, s, b))
        
        return out
    
    def get_standings_with_places(self) -> List[Tuple[int, str, int, int]]:
        """Get standings with places assigned."""
        base_rows = self.get_sorted_standings() if self.scores else []
        return self.assign_places(base_rows)
    
    def is_tournament_finished(self) -> bool:
        """Check if tournament is complete."""
        return self.round_no >= ROUNDS and not self.current_table_pairs 