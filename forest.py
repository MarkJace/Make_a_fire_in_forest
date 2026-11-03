"""Small synchronous cellular forest-fire simulation (no GUI dependency)."""
from random import Random
import math

EMPTY, TREE, FIRE, ASH, WATER, CITY, UNKNOWN = range(7)


class Forest:
    def __init__(self, size=100, density=0.65, seed=None, terrain=None):
        self.size = size
        self.random = Random(seed)
        self.cells = ([TREE if self.random.random() < density else EMPTY
                       for _ in range(size * size)] if terrain is None else [])
        if terrain is not None:
            if len(terrain) != size * size or any(cell not in (EMPTY, TREE, WATER, CITY, UNKNOWN) for cell in terrain):
                raise ValueError('Terrain must contain exactly size² valid terrain cells.')
            self.cells = list(terrain)
        self.initial_terrain = tuple(self.cells)
        self.ages = [0] * len(self.cells)
        self.initial_trees = self.cells.count(TREE)
        self.steps = 0
        self.set_weather()

    def set_weather(self, wind_speed=0, wind_direction=None, precipitation_rate=0):
        """Game parameters: m/s, meteorological degrees, liquid-equivalent mm/h."""
        def bounded(value, upper):
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                return 0.0
            return max(0.0, min(upper, value))
        self.wind_speed = bounded(wind_speed, 60)
        self.wind_direction = (wind_direction % 360 if isinstance(wind_direction, (int, float))
                               and math.isfinite(wind_direction) else None)
        self.precipitation_rate = bounded(precipitation_rate, 100)
        self.spread_chances = {(dr, dc): self.spread_probability(dr, dc)
                               for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc}

    def spread_probability(self, dr, dc):
        alignment = 0.0
        if self.wind_direction is not None:
            angle = math.radians(self.wind_direction)
            # Rows grow southward. A north wind blows towards positive rows.
            alignment = (dr * math.cos(angle) - dc * math.sin(angle)) / math.hypot(dr, dc)
        wind_factor = 1 + 0.12 * self.wind_speed * (1 + 0.8 * alignment)
        wet_factor = 1 + 0.7 * self.precipitation_rate
        return 1 - (1 - 0.22) ** (wind_factor / wet_factor)

    def ignite(self, row, col):
        if not (0 <= row < self.size and 0 <= col < self.size):
            return False
        index = row * self.size + col
        if self.cells[index] != TREE:
            return False
        self.cells[index] = FIRE
        self.ages[index] = 7
        return True

    def step(self):
        """Old fires spread to eight neighbors; new fires wait until next tick."""
        cells, ages = self.cells[:], self.ages[:]
        changed = set()
        for index, state in enumerate(self.cells):
            if state != FIRE:
                continue
            # Rain/snow act before spread, so extinguished cells cannot ignite neighbors.
            ages[index] -= 0.7 * self.precipitation_rate
            if ages[index] <= 0:
                cells[index], ages[index] = ASH, 0
                changed.add(index)
                continue
            row, col = divmod(index, self.size)
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    r, c = row + dr, col + dc
                    if not (0 <= r < self.size and 0 <= c < self.size):
                        continue
                    neighbor = r * self.size + c
                    if (self.cells[neighbor] == TREE and cells[neighbor] == TREE
                            and self.random.random() < self.spread_chances[dr, dc]):
                        cells[neighbor], ages[neighbor] = FIRE, 7
                        changed.add(neighbor)
            ages[index] -= 1
            if ages[index] <= 0:
                cells[index], ages[index] = ASH, 0
            changed.add(index)
        self.cells, self.ages = cells, ages
        self.steps += 1
        return changed

    def counts(self):
        return {state: self.cells.count(state) for state in (EMPTY, TREE, FIRE, ASH, WATER, CITY, UNKNOWN)}
