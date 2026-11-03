import unittest
from unittest.mock import patch
import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from landcover import (LandCoverError, fetch_coverage, region_bounds,
                       tile_regions, weighted_counts)

class LandCoverTests(unittest.TestCase):
    def tearDown(self):
        fetch_coverage.cache_clear()

    def test_area_weighting_and_no_data(self):
        values = np.ma.array([[10, 95, 80], [60, 0, 255]], mask=False)
        trees, valid, total, count = weighted_counts(values, np.array([60., 0.]))
        self.assertAlmostEqual(trees, 1)
        self.assertAlmostEqual(valid, 2.5)
        self.assertAlmostEqual(total, 4.5)
        self.assertEqual(count, 4)
        values.mask[0, 0] = True
        self.assertEqual(weighted_counts(values, np.array([60., 0.]))[-1], 3)

    def test_boundaries_and_antimeridian(self):
        tiles = list(tile_regions(region_bounds(0, 0)[0]))
        self.assertEqual(len(tiles), 4)
        self.assertTrue(any('S03W003' in url for url, _ in tiles))
        for longitude in (-180, 180, 179.99, -179.99):
            bounds = region_bounds(0, longitude)
            self.assertEqual(len(bounds), 2)
            self.assertTrue(all(-180 <= w < e <= 180 for w, s, e, n in bounds))
            self.assertAlmostEqual(sum(e-w for w,s,e,n in bounds), 10/111.195)
        with self.assertRaises(LandCoverError):
            region_bounds(89, 0)

    def test_native_window_fraction_and_cache(self):
        values = np.full((300, 300), 60, dtype='uint8')
        values[:, :150] = 10
        with MemoryFile() as mem:
            with mem.open(driver='GTiff', width=300, height=300, count=1,
                          dtype='uint8', crs='EPSG:4326', transform=from_origin(0,3,.01,.01), nodata=0) as dst:
                dst.write(values, 1)
            with patch('rasterio.open', side_effect=lambda url: mem.open()) as opened:
                result = fetch_coverage(1.5, 1.5)
                self.assertAlmostEqual(result.fraction, .5)
                self.assertAlmostEqual(result.valid_fraction, 1)
                self.assertLess(result.pixels, values.size)
                self.assertEqual(fetch_coverage(1.5, 1.5), result)
                self.assertEqual(opened.call_count, 1)

    def test_missing_data_is_not_desert(self):
        with MemoryFile() as mem:
            with mem.open(driver='GTiff', width=300, height=300, count=1,
                          dtype='uint8', crs='EPSG:4326', transform=from_origin(0,3,.01,.01), nodata=0) as dst:
                dst.write(np.zeros((300,300), dtype='uint8'), 1)
            with patch('rasterio.open', side_effect=lambda url: mem.open()):
                with self.assertRaisesRegex(LandCoverError, 'Insufficient'):
                    fetch_coverage(1.5, 1.5)
        with patch('rasterio.open', side_effect=OSError('offline')):
            with self.assertRaisesRegex(LandCoverError, 'unavailable'):
                fetch_coverage(1.5, 1.5)

if __name__ == '__main__':
    unittest.main()
