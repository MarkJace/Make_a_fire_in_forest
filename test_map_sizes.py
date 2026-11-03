import unittest
from unittest.mock import patch
import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from landcover import region_bounds, fetch_coverage, terrain_votes, terrain_from_votes
from map_config import GRID_SIZE, MAP_SIZES_KM
from forest import Forest, TREE, WATER, CITY, EMPTY
from map_renderer import map_ppm

class MapSizeTests(unittest.TestCase):
    def tearDown(self):
        fetch_coverage.cache_clear()

    def test_extents_and_full_grid_orientation(self):
        for km in MAP_SIZES_KM:
            bounds=region_bounds(0,0,km)[0]
            w,s,e,n=bounds
            self.assertAlmostEqual((n-s)*111.195,km)
            lats=n-(np.arange(400)+.5)*(n-s)/400
            lons=w+(np.arange(400)+.5)*(e-w)/400
            raw=np.full((400,400),10)
            raw[:,200:]=80
            terrain=terrain_from_votes(terrain_votes(raw,lats,lons,0,0,side_km=km))
            self.assertEqual(len(terrain),160000)
            self.assertEqual(terrain[:400],(TREE,)*200+(WATER,)*200)
            self.assertEqual(terrain[-400:],terrain[:400])
    def test_range_is_part_of_cache_and_metadata(self):
        with MemoryFile() as mem:
            with mem.open(driver='GTiff',width=1000,height=1000,count=1,dtype='uint8',
                          crs='EPSG:4326',transform=from_origin(0,3,.003,.003),nodata=0) as dst:
                dst.write(np.full((1000,1000),10,dtype='uint8'),1)
            with patch('rasterio.open',side_effect=lambda url:mem.open()) as opened:
                counts=[]
                for km in MAP_SIZES_KM:
                    result=fetch_coverage(1.5,1.5,km)
                    self.assertEqual((result.size,result.side_km),(400,km))
                    self.assertEqual(len(result.terrain),160000)
                    counts.append(result.pixels)
                    self.assertEqual(fetch_coverage(1.5,1.5,km),result)
                self.assertEqual(opened.call_count,4)
                self.assertEqual(counts,sorted(set(counts)))

    def test_raster_render_keeps_orientation_and_colors(self):
        f=Forest(size=2,terrain=(TREE,WATER,CITY,EMPTY))
        ppm=map_ppm(f,4)
        header=b'P6\n4 4\n255\n'
        self.assertTrue(ppm.startswith(header))
        pixels=np.frombuffer(ppm[len(header):],dtype=np.uint8).reshape(4,4,3)
        self.assertEqual(tuple(pixels[0,3]),(41,127,186))
        self.assertEqual(tuple(pixels[3,0]),(165,172,185))
        self.assertEqual(tuple(pixels[3,3]),(169,149,107))
        f.ignite(0,0)
        self.assertNotEqual(ppm,map_ppm(f,4))

if __name__=='__main__':
    unittest.main()
