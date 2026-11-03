import unittest
import numpy as np
from forest import Forest, EMPTY, TREE, FIRE, ASH, WATER, CITY, UNKNOWN
from landcover import terrain_votes, terrain_from_votes

class TerrainTests(unittest.TestCase):
    def coordinates(self, lat=0, lon=0, size=4):
        dy = 10 / (2*111.195)
        dx = dy / np.cos(np.radians(lat))
        return (lat + dy - (np.arange(size)+.5)*2*dy/size,
                lon - dx + (np.arange(size)+.5)*2*dx/size)

    def test_spatial_layout_and_class_mapping(self):
        raw = np.array([[10,95,80,50], [60,20,30,40], [70,90,100,0], [50,80,10,255]])
        lats, lons = self.coordinates()
        terrain = terrain_from_votes(terrain_votes(raw, lats, lons, 0, 0, size=4))
        self.assertEqual(terrain, (TREE,TREE,WATER,CITY, EMPTY,EMPTY,EMPTY,EMPTY,
                                   EMPTY,EMPTY,EMPTY,UNKNOWN, CITY,WATER,TREE,UNKNOWN))

    def test_stitching_and_antimeridian_keep_orientation(self):
        raw = np.array([[10,10,80,80]]*4)
        lats, lons = self.coordinates(lon=180)
        east = (lons[2:]+180)%360-180
        votes = terrain_votes(raw[:,:2], lats, lons[:2], 0, 180, size=4)
        votes += terrain_votes(raw[:,2:], lats, east, 0, 180, size=4)
        self.assertEqual(terrain_from_votes(votes), (TREE,TREE,WATER,WATER)*4)

    def test_majority_aggregation_and_missing_cells(self):
        lats,lons = self.coordinates(size=4)
        votes = terrain_votes(np.array([[10,10,50,50],[80,10,50,60],
                                         [80,80,0,0],[80,60,0,0]]), lats,lons,0,0,size=2)
        self.assertEqual(terrain_from_votes(votes), (TREE,CITY,WATER,UNKNOWN))

    def test_water_and_city_are_nonflammable_barriers(self):
        for barrier in (WATER, CITY, UNKNOWN, EMPTY):
            terrain = [TREE,barrier,TREE]*3
            f = Forest(size=3, terrain=terrain)
            f.random.random = lambda: 0
            self.assertFalse(f.ignite(1,1))
            f.ignite(1,0)
            for _ in range(20):
                f.step()
            self.assertEqual(f.cells[1::3], [barrier]*3)
            self.assertEqual(f.cells[2::3], [TREE]*3)
            self.assertEqual(f.initial_terrain, tuple(terrain))
            reset = Forest(size=3, terrain=f.initial_terrain)
            self.assertEqual(reset.cells, terrain)
            self.assertNotIn(FIRE, reset.cells)
            self.assertNotIn(ASH, reset.cells)

    def test_invalid_terrain_is_rejected(self):
        for terrain in ([TREE], [FIRE]*4, [999]*4):
            with self.assertRaises(ValueError):
                Forest(size=2, terrain=terrain)

if __name__ == '__main__':
    unittest.main()
