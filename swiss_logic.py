import random
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Optional

from config import NUM_TABLES


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


def deal_maps(
    maps: List[str],
    num_tables: int = NUM_TABLES,
    rng: Optional[random.Random] = None
) -> Dict[int, str]:
    """Assign exactly one random UNIQUE map to each table."""
    if rng is None:
        rng = random.Random()

    if len(maps) < num_tables:
        raise ValueError(f"Need at least {num_tables} maps, got {len(maps)}.")

    maps_shuffled = maps[:]
    rng.shuffle(maps_shuffled)
    return {t: maps_shuffled[t-1] for t in range(1, num_tables + 1)}


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


def compute_wins_losses_from_log(players: List[str], match_log: List[Dict]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Count wins and losses for each player based on match_log."""
    wins = {p: 0 for p in players}
    losses = {p: 0 for p in players}
    for m in match_log:
        a, b, w = m["a"], m["b"], m["winner"]
        wins[w] += 1
        loser = b if w == a else a
        losses[loser] += 1
    return wins, losses


def compute_buchholz_wl(players: List[str], match_log: List[Dict]) -> Dict[str, int]:
    """
    New Buchholz: for each player, sum over unique opponents of (opponent_wins - opponent_losses).
    Uses match_log to derive opponents and each opponent's W/L.
    """
    opponents = defaultdict(set)
    for m in match_log:
        a, b = m["a"], m["b"]
        opponents[a].add(b)
        opponents[b].add(a)

    wins, losses = compute_wins_losses_from_log(players, match_log)
    out: Dict[str, int] = {p: 0 for p in players}
    for p in players:
        total = 0
        for opp in opponents.get(p, []):
            total += wins.get(opp, 0) - losses.get(opp, 0)
        out[p] = total
    return out


def head_to_head(a: str, b: str, match_log: List[Dict]) -> Optional[str]:
    """
    Return 'a' if a beat b; 'b' if b beat a; None if they didn't play.
    If multiple meetings exist, the LAST result is used.
    """
    res = None
    for m in match_log:
        if (m["a"] == a and m["b"] == b) or (m["a"] == b and m["b"] == a):
            res = m["winner"]
    return res 