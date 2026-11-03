"""Small synchronous cellular forest-fire simulation (no GUI dependency)."""
from random import Random

EMPTY, TREE, FIRE, ASH = range(4)


class Forest:
    def __init__(self, size=100, density=0.65, seed=None):
        self.size = size
        self.random = Random(seed)
        self.cells = [TREE if self.random.random() < density else EMPTY
                      for _ in range(size * size)]
        self.ages = [0] * len(self.cells)
        self.initial_trees = self.cells.count(TREE)
        self.steps = 0

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
                            and self.random.random() < 0.22):
                        cells[neighbor], ages[neighbor] = FIRE, 7
                        changed.add(neighbor)
            ages[index] -= 1
            if ages[index] == 0:
                cells[index] = ASH
            changed.add(index)
        self.cells, self.ages = cells, ages
        self.steps += 1
        return changed

    def counts(self):
        return {state: self.cells.count(state) for state in (EMPTY, TREE, FIRE, ASH)}
