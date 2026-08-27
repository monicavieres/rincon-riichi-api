"""Table simulation: deal hands, wall, dead wall, dora, discards, honba, winds.

Deals a full four-player riichi table from a 136-tile wall (or a 108-tile
wall without honors) and exposes the wall face, dead wall, dora indicators,
discard pools, honba counters, and round/seat winds.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .hand import get_waits
from .tiles import NUMBERED_SUITS, TILE_TYPES, WINDS, sort_tiles

#: Full 136-tile wall.
FULL_WALL = [t for t in TILE_TYPES for _ in range(4)] + [
    "0m",
    "0m",
    "0m",
    "0p",
    "0p",
    "0p",
    "0s",
    "0s",
    "0s",
]

#: 108-tile wall (no honors, number tiles only).
SIMPLE_WALL = [f"{n}{s}" for s in NUMBERED_SUITS for n in range(1, 10) for _ in range(4)]


@dataclass
class Player:
    """One player's seat with their hand and discards."""

    seat: str
    wind: str
    hand: list[str] = field(default_factory=list)
    discards: list[str] = field(default_factory=list)
    is_dealer: bool = False
    riichi: bool = False


@dataclass
class Table:
    """A simulated riichi table state."""

    players: list[Player] = field(default_factory=list)
    wall: list[str] = field(default_factory=list)
    dead_wall: list[str] = field(default_factory=list)
    dora_indicators: list[str] = field(default_factory=list)
    round_wind: str = "East"
    honba: int = 0
    turn_index: int = 0

    def draw(self) -> str | None:
        """Draw a tile from the live wall (returns None when empty)."""
        if not self.wall:
            return None
        return self.wall.pop(0)

    def discard(self, player_idx: int, tile: str) -> str:
        """Discard a tile from a player's hand to their pond."""
        player = self.players[player_idx]
        player.hand.remove(tile)
        player.discards.append(tile)
        return tile

    def dealer_won(self) -> None:
        """Register honba logic: +1 honba on a drawn round; reset on dealer win."""
        self.honba += 1


def build_wall(with_honors: bool = True, seed: int | None = None) -> list[str]:
    """Build a shuffled wall."""
    rng = random.Random(seed)
    wall = list(FULL_WALL if with_honors else SIMPLE_WALL)
    rng.shuffle(wall)
    return wall


def deal_table(
    with_honors: bool = True,
    seed: int | None = None,
    start_wind: str = "East",
) -> Table:
    """Deal a fresh table: 4 x 13 tiles, dead wall (14), dora, wall face."""
    rng = random.Random(seed)
    wall = build_wall(with_honors=with_honors, seed=seed)
    table = Table(round_wind=start_wind)

    # Dead wall (14 tiles at the end of the wall).
    dead_wall = wall[-14:]
    wall = wall[:-14]
    # Dora indicators: the 4th tile from the end of the dead wall, plus 1.
    dora_indicators = [dead_wall[4]]
    if len(dead_wall) > 10:
        dora_indicators.append(dead_wall[10])

    winds = WINDS
    east_idx = 0  # East is the dealer (first player)
    for i, wind in enumerate(winds):
        table.players.append(
            Player(seat=f"P{i+1}", wind=wind, is_dealer=(i == east_idx))
        )

    for _ in range(13):
        for player in table.players:
            player.hand.append(wall.pop(0))

    table.wall = wall
    table.dead_wall = dead_wall
    table.dora_indicators = dora_indicators
    table.honba = 0
    table.turn_index = 0
    return table


def simulate_discards(table: Table, turns: int = 6, seed: int | None = None) -> dict:
    """Simulate a few turns of discards, returning an observation snapshot."""
    rng = random.Random(seed)
    snapshots = []
    for t in range(turns):
        idx = (table.turn_index + t) % len(table.players)
        player = table.players[idx]
        drawn = table.draw()
        if drawn is not None:
            player.hand.append(drawn)
        # Random discard from hand.
        discard = rng.choice(player.hand)
        table.discard(idx, discard)
        snapshots.append(
            {"player": idx + 1, "wind": player.wind, "drawn": drawn, "discarded": discard}
        )
    return {"turns": snapshots, "honba": table.honba}


def status(table: Table) -> dict:
    """Return a serializable snapshot of the table state."""
    return {
        "round_wind": table.round_wind,
        "honba": table.honba,
        "turn_index": table.turn_index,
        "wall_remaining": len(table.wall),
        "dead_wall": sort_tiles(table.dead_wall),
        "dora_indicators": table.dora_indicators,
        "players": [
            {
                "seat": p.seat,
                "wind": p.wind,
                "dealer": p.is_dealer,
                "riichi": p.riichi,
                "hand": sort_tiles(p.hand),
                "hand_tenpai": len(get_waits(p.hand)) > 0 if len(p.hand) == 13 else False,
                "waits": get_waits(p.hand) if len(p.hand) == 13 else [],
                "discards": p.discards,
            }
            for p in table.players
        ],
    }
