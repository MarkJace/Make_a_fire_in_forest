import unittest
from forest import ASH, EMPTY, FIRE, TREE, Forest


class ForestTests(unittest.TestCase):
    def test_density_and_bounds(self):
        empty = Forest(size=3, density=0)
        self.assertEqual(empty.cells, [EMPTY] * 9)
        self.assertFalse(empty.ignite(0, 0))
        full = Forest(size=3, density=1)
        self.assertFalse(full.ignite(-1, 0))
        self.assertFalse(full.ignite(3, 0))
        self.assertTrue(full.ignite(1, 1))
        self.assertFalse(full.ignite(1, 1))

    def test_synchronous_spread_and_no_edge_wrap(self):
        forest = Forest(size=5, density=1)
        forest.random.random = lambda: 0
        forest.ignite(0, 0)
        forest.step()
        burning = {i for i, cell in enumerate(forest.cells) if cell == FIRE}
        self.assertEqual(burning, {0, 1, 5, 6})
        self.assertEqual(forest.cells[2], TREE)

    def test_burnout_and_conservation(self):
        forest = Forest(size=10, density=0.7, seed=42)
        index = forest.cells.index(TREE)
        forest.ignite(*divmod(index, forest.size))
        for _ in range(1000):
            if FIRE not in forest.cells:
                break
            forest.step()
        self.assertNotIn(FIRE, forest.cells)
        self.assertGreater(forest.cells.count(ASH), 0)
        self.assertEqual(forest.cells.count(TREE) + forest.cells.count(ASH),
                         forest.initial_trees)


if __name__ == '__main__':
    unittest.main()
