import random
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Optional
import copy
import json
import os
from datetime import datetime

# --- Tournament config ---
NUM_TABLES = 12
SEATS_PER_TABLE = 2       # exactly two players per table
ROUNDS = 5
POINTS_FOR_WIN = 1

# --- Save config ---
SAVE_DIR = "saves"  # all autosaves and manual exports go here

# --- Deck pool (can be longer than needed) ---
DEFAULT_DECK_POOL = [
    "Alice", "Arthur", "Medusa", "Sindbad",
    "Alice", "Arthur", "Medusa", "Sindbad",
    "Enenga", "Wukon", "Achilles", "Bloody Mary",
    "Enenga", "Wukon", "Achilles", "Bloody Mary",
    "Sherlok", "Jackill&Hyde", "Invisible Man", "Dracula",
    "Sherlok", "Jackill&Hyde", "Invisible Man", "Dracula",
    "Houdini", "Djinn", "Red hood", "Beowulf",
    "Houdini", "Djinn", "Red hood", "Beowulf",
    "Robin Hood", "Big Foot", "Oda Nobunaga", "Tomoe Gozen",
    "Robin Hood", "Big Foot", "Oda Nobunaga", "Tomoe Gozen",
    "Shakespear", "Titania", "Hamlet", "Sisters",
    "Tesla", "Jill Trent", "Christmas", "Golden Bat",
    "Loki", "Pandora", "Black Beard", "Chupacabra"
]

# ----------------------------
# Utility: ensure save dir
# ----------------------------
def ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# ----------------------------
# Decks -> Tables (fixed once)
# ----------------------------
def deal_tables(
    deck_pool: List[str],
    num_tables: int = NUM_TABLES,
    decks_per_table: int = 4,
    rng: Optional[random.Random] = None
) -> Dict[int, List[str]]:
    """Assign decks to tables ONCE; ensure distinct decks per table."""
    if rng is None:
        rng = random.Random()

    total_needed = num_tables * decks_per_table
    if len(deck_pool) < total_needed:
        raise ValueError(f"Need at least {total_needed} decks, got {len(deck_pool)}.")

    pool = deck_pool[:]
    rng.shuffle(pool)

    tables_to_decks: Dict[int, List[str]] = {t: [] for t in range(1, num_tables + 1)}
    idx = 0
    for t in range(1, num_tables + 1):
        used_here: Set[str] = set()
        for _ in range(decks_per_table):
            pick_pos = None
            for j in range(idx, len(pool)):
                if pool[j] not in used_here:
                    pick_pos = j
                    break
            if pick_pos is None:
                raise ValueError("Cannot assemble distinct decks per table; diversify pool.")
            if pick_pos != idx:
                pool[idx], pool[pick_pos] = pool[pick_pos], pool[idx]
            chosen = pool[idx]
            idx += 1
            tables_to_decks[t].append(chosen)
            used_here.add(chosen)

    return tables_to_decks

# ----------------------------
# Swiss pairing core (2-player tables)
# ----------------------------
def swiss_make_pairs(
    players: List[str],
    scores: Dict[str, int],
    prev_opponents: Dict[str, Set[str]],
    max_attempts: int = 2000,
    rng: Optional[random.Random] = None
) -> List[Tuple[str, str]]:
    """Build 1v1 Swiss pairs; avoid rematches if possible; pair by closest scores."""
    if rng is None:
        rng = random.Random()

    if len(players) % 2 == 1:
        raise ValueError("Odd number of players. Please ensure an even number.")

    by_score = defaultdict(list)
    for p in players:
        by_score[scores.get(p, 0)].append(p)
    ordered_scores = sorted(by_score.keys(), reverse=True)

    ladder = []
    for sc in ordered_scores:
        grp = by_score[sc][:]
        rng.shuffle(grp)
        ladder.extend(grp)

    def try_build(allow_rematch: bool) -> List[Tuple[str, str]]:
        unpaired = ladder[:]
        pairs = []
        while unpaired:
            a = unpaired.pop(0)
            best_idx = None
            best_pen = None
            for i, b in enumerate(unpaired):
                gap = abs(scores.get(a, 0) - scores.get(b, 0))
                rematch = (b in prev_opponents.get(a, set()))
                if rematch and not allow_rematch:
                    continue
                pen = gap + (1000 if rematch else 0)
                if best_pen is None or pen < best_pen:
                    best_pen = pen
                    best_idx = i
            if best_idx is None:
                return []
            b = unpaired.pop(best_idx)
            pairs.append((a, b))
        return pairs

    for _ in range(max_attempts):
        shuffled = ladder[:]
        for i in range(0, len(shuffled), 4):
            rng.shuffle(shuffled[i:i+4])
        ladder = shuffled
        pairs = try_build(allow_rematch=False)
        if pairs:
            return pairs

    pairs = try_build(allow_rematch=True)
    if not pairs:
        raise RuntimeError("Could not construct Swiss pairs.")
    return pairs


def assign_tables_avoiding_repeats(
    pairs: List[Tuple[str, str]],
    prev_tables: Dict[str, Set[int]],
    num_tables: int = NUM_TABLES,
    max_attempts: int = 2000,
    rng: Optional[random.Random] = None
) -> Tuple[Dict[int, Tuple[str, str]], List[Tuple[str, int]]]:
    """Assign each pair to a table, trying to avoid repeating tables for players."""
    if rng is None:
        rng = random.Random()

    tables = list(range(1, num_tables + 1))
    if len(pairs) > len(tables):
        raise ValueError("More pairs than tables.")

    def try_assign(strict_avoid: bool) -> Tuple[Dict[int, Tuple[str, str]], List[Tuple[str, int]]]:
        forced: List[Tuple[str, int]] = []
        t2p: Dict[int, Tuple[str, str]] = {}
        free_tables = tables[:]
        rng.shuffle(free_tables)

        for (a, b) in pairs:
            best_table = None
            best_pen = None
            for t in free_tables:
                pen = 0
                if t in prev_tables.get(a, set()):
                    pen += 1
                if t in prev_tables.get(b, set()):
                    pen += 1
                if strict_avoid and pen > 0:
                    continue
                if best_pen is None or pen < best_pen:
                    best_pen = pen
                    best_table = t

            if best_table is None:
                return {}, []

            t2p[best_table] = (a, b)
            free_tables.remove(best_table)
            if best_pen and best_pen > 0:
                if best_table in prev_tables.get(a, set()):
                    forced.append((a, best_table))
                if best_table in prev_tables.get(b, set()):
                    forced.append((b, best_table))
        return t2p, forced

    for _ in range(max_attempts):
        t2p, forced = try_assign(strict_avoid=True)
        if t2p:
            return t2p, forced

    t2p, forced = try_assign(strict_avoid=False)
    if not t2p:
        raise RuntimeError("Could not assign tables to pairs.")
    return t2p, forced

# ----------------------------
# Tkinter App
# ----------------------------
class SwissApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Swiss Tournament — 12 tables × 2 players")
        self.geometry("1320x820")

        self.rng = random.Random()

        # State
        self.players: List[str] = []
        self.scores: Dict[str, int] = {}
        self.prev_opponents: Dict[str, Set[str]] = defaultdict(set)
        self.prev_tables: Dict[str, Set[int]] = defaultdict(set)
        self.round_no = 0
        self.current_table_pairs: Dict[int, Tuple[str, str]] = {}  # table -> (A,B)
        self.result_vars: Dict[int, tk.StringVar] = {}  # table -> winner strvar
        self.tables_to_decks: Dict[int, List[str]] = {}  # table -> 4 decks

        # Undo history: stack of snapshots saved BEFORE applying results
        self.history: List[Dict] = []

        # UI
        self._build_left_panel()
        self._build_right_panel()
        self._update_players_list()
        self._refresh_standings()
        self._render_empty_pairings()
        self._render_tables_decks([])

        # protocol: autosave on close
        self.protocol("WM_DELETE_WINDOW", self._on_close_autosave_then_exit)

    # --------- UI LAYOUT ---------
    def _build_left_panel(self):
        left = tk.Frame(self, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y)

        # Player management
        tk.Label(left, text="Players").pack(anchor="w")
        self.players_list = tk.Listbox(left, height=16, width=28, exportselection=False)
        self.players_list.pack(anchor="w")

        # Player count label
        self.player_count_var = tk.StringVar(value="Players: 0 / 24")
        tk.Label(left, textvariable=self.player_count_var, fg="gray").pack(anchor="w", pady=(2, 8))

        form = tk.Frame(left)
        form.pack(anchor="w", pady=(0, 0))
        tk.Label(form, text="Add player:").grid(row=0, column=0, sticky="w")
        self.player_name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.player_name_var, width=18).grid(row=0, column=1, padx=5)
        tk.Button(form, text="Add", command=self.add_player).grid(row=0, column=2)
        tk.Button(left, text="Remove selected", command=self.remove_selected).pack(anchor="w", pady=(6, 6))

        # Status + seed
        self.status_var = tk.StringVar(value="Add players, then Start Tournament.")
        tk.Label(left, textvariable=self.status_var, fg="gray").pack(anchor="w", pady=(6, 6))

        tk.Label(left, text="Random seed (optional):").pack(anchor="w")
        self.seed_var = tk.StringVar(value="")
        tk.Entry(left, textvariable=self.seed_var, width=16).pack(anchor="w")

        # Control buttons
        self.start_btn  = tk.Button(left, text="Start Tournament", command=self.start_tournament)
        self.pair_btn   = tk.Button(left, text="Pair Next Round", command=self.pair_next_round, state=tk.DISABLED)
        self.submit_btn = tk.Button(left, text="Submit Results", command=self.submit_results, state=tk.DISABLED)
        self.undo_btn   = tk.Button(left, text="Undo Last Round", command=self.undo_last_round, state=tk.DISABLED)

        # Save/Load buttons
        self.export_btn = tk.Button(left, text="Export Now…", command=self.export_now)
        self.import_btn = tk.Button(left, text="Import State…", command=self.import_state)

        self.reset_btn  = tk.Button(left, text="Reset", command=self.reset_tournament)

        self.start_btn.pack(anchor="w", fill=tk.X, pady=(10, 4))
        self.pair_btn.pack(anchor="w", fill=tk.X, pady=4)
        self.submit_btn.pack(anchor="w", fill=tk.X, pady=4)
        self.undo_btn.pack(anchor="w", fill=tk.X, pady=4)
        self.export_btn.pack(anchor="w", fill=tk.X, pady=4)
        self.import_btn.pack(anchor="w", fill=tk.X, pady=4)
        self.reset_btn.pack(anchor="w", fill=tk.X, pady=10)

    def _build_right_panel(self):
        right = tk.Frame(self, padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Round header
        head = tk.Frame(right)
        head.pack(fill=tk.X)
        self.round_label = tk.Label(head, text="Round: —", font=("TkDefaultFont", 12, "bold"))
        self.round_label.pack(side=tk.LEFT)

        # Tables & Decks (always visible)
        self.decks_frame = tk.LabelFrame(right, text="Tables & Decks (fixed for all rounds)")
        self.decks_frame.pack(fill=tk.X, pady=(8, 8))
        self.decks_tree = ttk.Treeview(
            self.decks_frame,
            columns=("Table", "Deck 1", "Deck 2", "Deck 3", "Deck 4"),
            show="headings",
            height=6
        )
        for col, w in [("Table", 70), ("Deck 1", 200), ("Deck 2", 200), ("Deck 3", 200), ("Deck 4", 200)]:
            self.decks_tree.heading(col, text=col)
            self.decks_tree.column(col, width=w, anchor="w")
        self.decks_tree.pack(fill=tk.X, expand=False)

        # Pairings area
        self.pairings_frame = tk.LabelFrame(right, text="Current Round Pairings (select winners)")
        self.pairings_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 8))

        # Standings
        self.standings_frame = tk.LabelFrame(right, text="Standings")
        self.standings_frame.pack(fill=tk.BOTH)
        self.tree = ttk.Treeview(self.standings_frame, columns=("Player", "Score"), show="headings", height=12)
        self.tree.heading("Player", text="Player")
        self.tree.heading("Score", text="Score")
        self.tree.column("Player", width=260)
        self.tree.column("Score", width=80, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

    # --------- Player management ---------
    def _update_player_count_label(self):
        self.player_count_var.set(f"Players: {len(self.players)} / {NUM_TABLES * SEATS_PER_TABLE}")

    def add_player(self):
        name = self.player_name_var.get().strip()
        if not name:
            return
        if name in self.players:
            messagebox.showerror("Error", "Player already exists.")
            return
        if len(self.players) >= NUM_TABLES * SEATS_PER_TABLE:
            messagebox.showerror("Error", f"Max {NUM_TABLES * SEATS_PER_TABLE} players.")
            return
        self.players.append(name)
        self.player_name_var.set("")
        self._update_players_list()

    def remove_selected(self):
        if self.round_no > 0:
            messagebox.showerror("Error", "Cannot remove players after start.")
            return
        sel = list(self.players_list.curselection())
        sel.reverse()
        for idx in sel:
            del self.players[idx]
        self._update_players_list()

    def _update_players_list(self):
        self.players_list.delete(0, tk.END)
        for p in self.players:
            self.players_list.insert(tk.END, p)
        self._update_player_count_label()

    # --------- Tournament flow ---------
    def start_tournament(self):
        if len(self.players) == 0:
            messagebox.showerror("Error", "Add players first.")
            return
        if len(self.players) % 2 == 1:
            messagebox.showerror("Error", "Number of players must be EVEN (2 per table).")
            return
        max_players = NUM_TABLES * SEATS_PER_TABLE
        if len(self.players) > max_players:
            messagebox.showerror("Error", f"Max {max_players} players (12 tables × 2).")
            return

        seed = self.seed_var.get().strip()
        if seed:
            try:
                self.rng.seed(int(seed))
            except ValueError:
                self.rng.seed(seed)

        # Initialize state
        self.scores = {p: 0 for p in self.players}
        self.prev_opponents = defaultdict(set)
        self.prev_tables = defaultdict(set)
        self.round_no = 0
        self.history.clear()
        self.undo_btn.config(state=tk.DISABLED)

        # Deal decks to tables ONCE and render
        try:
            self.tables_to_decks = deal_tables(DEFAULT_DECK_POOL, num_tables=NUM_TABLES, decks_per_table=4, rng=self.rng)
        except Exception as e:
            messagebox.showerror("Deck dealing failed", str(e))
            return
        self._render_tables_decks(sorted(self.tables_to_decks.items(), key=lambda x: x[0]))

        # Lock player edits
        self.start_btn.config(state=tk.DISABLED)
        self.pair_btn.config(state=tk.NORMAL)
        self.submit_btn.config(state=tk.DISABLED)

        self.status_var.set("Tournament started. Click 'Pair Next Round'.")
        self._refresh_standings()
        self._render_empty_pairings()
        self.round_label.config(text=f"Round: {self.round_no}/{ROUNDS}")

        # Autosave initial state (round 0)
        self.autosave(reason="start")

    def pair_next_round(self):
        if self.round_no >= ROUNDS:
            messagebox.showinfo("Info", "All rounds completed.")
            return

        try:
            pairs = swiss_make_pairs(self.players, self.scores, self.prev_opponents, rng=self.rng)
        except Exception as e:
            messagebox.showerror("Pairing failed", str(e))
            return

        try:
            table_pairs, forced = assign_tables_avoiding_repeats(pairs, self.prev_tables, rng=self.rng)
        except Exception as e:
            messagebox.showerror("Table assignment failed", str(e))
            return

        self.current_table_pairs = table_pairs
        self.round_no += 1
        self.round_label.config(text=f"Round: {self.round_no}/{ROUNDS}")

        if forced:
            txt = "\n".join(f"{p} @ Table {t}" for p, t in forced)
            messagebox.showwarning("Table repeats unavoidable", f"Some players revisited a table:\n{txt}")

        self._render_pairings()
        self.submit_btn.config(state=tk.NORMAL)
        self.pair_btn.config(state=tk.DISABLED)
        self.undo_btn.config(state=tk.NORMAL)
        self.status_var.set("Select winners and click 'Submit Results'.")

    def _snapshot_before_submit(self):
        """Save a deep snapshot BEFORE applying results for undo."""
        snap = {
            "round_no": self.round_no,  # this is the round being submitted
            "scores": copy.deepcopy(self.scores),
            "prev_opponents": {p: list(s) for p, s in self.prev_opponents.items()},
            "prev_tables": {p: list(s) for p, s in self.prev_tables.items()},
            "current_table_pairs": copy.deepcopy(self.current_table_pairs),
            "players": self.players[:],
            "tables_to_decks": copy.deepcopy(self.tables_to_decks),
        }
        self.history.append(snap)

    def submit_results(self):
        if not self.current_table_pairs:
            messagebox.showinfo("Info", "No active round to submit.")
            return

        # Ensure all winners selected
        winners = {}
        for t, (a, b) in self.current_table_pairs.items():
            sel = self.result_vars[t].get()
            if sel not in (a, b):
                messagebox.showerror("Missing winner", f"Select winner for Table {t}.")
                return
            winners[t] = sel

        # Save snapshot BEFORE modifying state (for Undo)
        self._snapshot_before_submit()

        # Apply results
        for t, (a, b) in self.current_table_pairs.items():
            w = winners[t]
            loser = b if w == a else a
            self.scores[w] += POINTS_FOR_WIN
            self.prev_opponents[a].add(b)
            self.prev_opponents[b].add(a)
            self.prev_tables[a].add(t)
            self.prev_tables[b].add(t)

        # Clear current round display
        self.current_table_pairs = {}
        self._render_empty_pairings()
        self._refresh_standings()

        if self.round_no < ROUNDS:
            self.pair_btn.config(state=tk.NORMAL)
            self.submit_btn.config(state=tk.DISABLED)
            self.status_var.set("Round saved. Click 'Pair Next Round' for the next round.")
        else:
            self.pair_btn.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.DISABLED)
            self.status_var.set("Tournament finished.")

        # Autosave BETWEEN rounds (after results applied)
        self.autosave(reason="between_rounds")

        # Undo remains enabled (we have snapshots)

    def undo_last_round(self):
        """Revert to the state BEFORE the last submitted round."""
        if not self.history:
            messagebox.showinfo("Info", "Nothing to undo.")
            return

        snap = self.history.pop()

        # Restore state
        self.round_no = snap["round_no"]  # back to the round being submitted
        self.scores = snap["scores"]
        self.prev_opponents = defaultdict(set, {p: set(s) for p, s in snap["prev_opponents"].items()})
        self.prev_tables = defaultdict(set, {p: set(s) for p, s in snap["prev_tables"].items()})
        self.current_table_pairs = snap["current_table_pairs"]
        self.players = snap.get("players", self.players)
        self.tables_to_decks = snap.get("tables_to_decks", self.tables_to_decks)

        # Re-render UI for that round (so user can re-enter winners)
        self._render_tables_decks(sorted(self.tables_to_decks.items(), key=lambda x: x[0]))
        self.round_label.config(text=f"Round: {self.round_no}/{ROUNDS}")
        self._render_pairings()
        self._refresh_standings()
        self._update_players_list()

        # Buttons: we are back inside an active round awaiting submission
        self.submit_btn.config(state=tk.NORMAL)
        self.pair_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.status_var.set("Undone last round. Re-select winners and Submit Results.")

        if not self.history:
            self.undo_btn.config(state=tk.DISABLED)

    def reset_tournament(self):
        if messagebox.askyesno("Reset", "Reset the tournament to an empty state?"):
            self.players = []
            self.scores.clear()
            self.prev_opponents.clear()
            self.prev_tables.clear()
            self.current_table_pairs.clear()
            self.tables_to_decks.clear()
            self.history.clear()
            self.round_no = 0
            self.start_btn.config(state=tk.NORMAL)
            self.pair_btn.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.DISABLED)
            self.undo_btn.config(state=tk.DISABLED)
            self.status_var.set("Add players, then Start Tournament.")
            self._update_players_list()
            self._refresh_standings()
            self._render_empty_pairings()
            self._render_tables_decks([])
            self.round_label.config(text="Round: —")

    # --------- Save / Load ---------
    def _serialize_state(self) -> Dict:
        """Build a JSON-serializable snapshot of the whole tournament state."""
        data = {
            "meta": {
                "version": 1,
                "timestamp": timestamp(),
                "config": {
                    "NUM_TABLES": NUM_TABLES,
                    "SEATS_PER_TABLE": SEATS_PER_TABLE,
                    "ROUNDS": ROUNDS,
                    "POINTS_FOR_WIN": POINTS_FOR_WIN,
                }
            },
            "round_no": self.round_no,
            "players": self.players[:],
            "scores": self.scores.copy(),
            "prev_opponents": {p: sorted(list(s)) for p, s in self.prev_opponents.items()},
            "prev_tables": {p: sorted(list(s)) for p, s in self.prev_tables.items()},
            "current_table_pairs": {int(t): list(pair) for t, pair in self.current_table_pairs.items()},
            "tables_to_decks": {int(t): decks[:] for t, decks in self.tables_to_decks.items()},
        }
        return data

    def _deserialize_state(self, data: Dict):
        """Restore state from a JSON snapshot."""
        self.round_no = int(data.get("round_no", 0))
        self.players = list(data.get("players", []))
        self.scores = {str(k): int(v) for k, v in data.get("scores", {}).items()}

        self.prev_opponents = defaultdict(
            set, {str(p): set(list(s)) for p, s in data.get("prev_opponents", {}).items()}
        )
        self.prev_tables = defaultdict(
            set, {str(p): set(list(s)) for p, s in data.get("prev_tables", {}).items()}
        )

        self.current_table_pairs = {
            int(t): (pair[0], pair[1]) for t, pair in data.get("current_table_pairs", {}).items()
        }
        self.tables_to_decks = {
            int(t): list(decks) for t, decks in data.get("tables_to_decks", {}).items()
        }

    def autosave(self, reason: str):
        """Automatic save to SAVE_DIR with unique filename."""
        ensure_save_dir()
        fname = f"{reason}_r{self.round_no:02d}_{timestamp()}.json"
        path = os.path.join(SAVE_DIR, fname)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._serialize_state(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showwarning("Autosave failed", str(e))

    def export_now(self):
        """Manual save via file dialog."""
        ensure_save_dir()
        default_name = f"manual_r{self.round_no:02d}_{timestamp()}.json"
        path = filedialog.asksaveasfilename(
            initialdir=SAVE_DIR,
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._serialize_state(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def import_state(self):
        """Load state from a JSON file and resume."""
        path = filedialog.askopenfilename(
            initialdir=SAVE_DIR if os.path.isdir(SAVE_DIR) else ".",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Load failed", f"Could not read file:\n{e}")
            return

        try:
            self._deserialize_state(data)
        except Exception as e:
            messagebox.showerror("Load failed", f"Invalid state structure:\n{e}")
            return

        # lock start; enable pair/submit depending on whether we are mid-round
        self.start_btn.config(state=tk.DISABLED)
        self.undo_btn.config(state=tk.NORMAL if self.history else tk.DISABLED)

        if self.current_table_pairs:
            # mid-round: awaiting results
            self.submit_btn.config(state=tk.NORMAL)
            self.pair_btn.config(state=tk.DISABLED)
            self.status_var.set("State loaded. Re-select winners and Submit Results.")
        else:
            # between rounds: ready to pair next
            self.submit_btn.config(state=tk.DISABLED)
            self.pair_btn.config(state=tk.NORMAL)
            self.status_var.set("State loaded. Click 'Pair Next Round'.")

        # refresh UI
        self._update_players_list()
        self._refresh_standings()
        self._render_tables_decks(sorted(self.tables_to_decks.items(), key=lambda x: x[0]))
        if self.current_table_pairs:
            self._render_pairings()
        else:
            self._render_empty_pairings()
        self.round_label.config(text=f"Round: {self.round_no}/{ROUNDS}")

        messagebox.showinfo("Loaded", f"Loaded:\n{os.path.basename(path)}")

    def _on_close_autosave_then_exit(self):
        """Autosave on exit and close the app."""
        try:
            self.autosave(reason="on_exit")
        finally:
            self.destroy()

    # --------- Rendering helpers ---------
    def _render_tables_decks(self, rows):
        # rows: list of (table_id, [d1,d2,d3,d4])
        for i in self.decks_tree.get_children():
            self.decks_tree.delete(i)
        for t, decks in rows:
            d = (decks + ["", "", "", ""])[:4]
            self.decks_tree.insert("", tk.END, values=(t, d[0], d[1], d[2], d[3]))

    def _render_empty_pairings(self):
        for w in self.pairings_frame.winfo_children():
            w.destroy()
        tk.Label(self.pairings_frame, text="No active round.").pack(anchor="w", padx=8, pady=6)

    def _render_pairings(self):
        for w in self.pairings_frame.winfo_children():
            w.destroy()
        self.result_vars.clear()

        rows = sorted(self.current_table_pairs.items(), key=lambda x: x[0])

        header = tk.Frame(self.pairings_frame)
        header.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(header, text="Table", width=6, anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="Player A vs Player B", anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=1, sticky="w", padx=(10, 0))
        tk.Label(header, text="Winner", width=16, anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(10, 0))

        for i, (t, (a, b)) in enumerate(rows, start=1):
            row = tk.Frame(self.pairings_frame)
            row.pack(fill=tk.X, padx=8)

            tk.Label(row, text=str(t), width=6, anchor="w").grid(row=0, column=0, sticky="w")
            tk.Label(row, text=f"{a}  vs  {b}", anchor="w").grid(row=0, column=1, sticky="w", padx=(10, 0))

            var = tk.StringVar(value="")
            self.result_vars[t] = var
            rb_frame = tk.Frame(row)
            rb_frame.grid(row=0, column=2, sticky="w", padx=(10, 0))
            tk.Radiobutton(rb_frame, text=a, variable=var, value=a).pack(side=tk.LEFT)
            tk.Radiobutton(rb_frame, text=b, variable=var, value=b).pack(side=tk.LEFT)

    def _refresh_standings(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        sorted_rows = sorted(self.scores.items(), key=lambda x: (-x[1], x[0])) if self.scores else []
        for name, sc in sorted_rows:
            self.tree.insert("", tk.END, values=(name, sc))


if __name__ == "__main__":
    app = SwissApp()

    # Optional: preload players so you don't have to type them manually.
    initial_players = [
        "Alice", "Bob", "Charlie", "Diana",
        "Eve", "Frank", "Grace", "Heidi",
        "Ivan", "Judy", "Karl", "Laura",
        "Mallory", "Niaj", "Olivia", "Peggy",
        "Quentin", "Rupert", "Sybil", "Trent",
        "Uma", "Victor", "Wendy", "Xander"
    ]
    app.players = initial_players[:]
    app._update_players_list()

    app.mainloop()
