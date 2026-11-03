"""One raster image instead of 160,000 individual Tk canvas rectangles."""
import numpy as np
from forest import TREE, FIRE

PALETTE = np.array([[169,149,107], [79,153,91], [255,152,63], [75,71,66],
                    [41,127,186], [165,172,185], [38,50,59]], dtype=np.uint8)
FLAMES = np.array([[255,204,103], [255,152,63], [235,97,53]], dtype=np.uint8)
TREES = np.array([[71,127,80], [85,150,94], [101,161,104]], dtype=np.uint8)


def map_ppm(forest, side):
    cells = np.asarray(forest.cells, dtype=np.uint8)
    rgb = PALETTE[cells]
    tree_indices = np.flatnonzero(cells == TREE)
    rgb[tree_indices] = TREES[tree_indices % 3]
    fire_indices = np.flatnonzero(cells == FIRE)
    if fire_indices.size:
        ages = np.fromiter((int(forest.ages[i]) for i in fire_indices), dtype=int)
        rgb[fire_indices] = FLAMES[(ages + fire_indices) % 3]
    rgb = rgb.reshape(forest.size, forest.size, 3)
    indices = np.arange(side) * forest.size // side
    scaled = rgb[indices[:, None], indices[None, :]]
    return f'P6\n{side} {side}\n255\n'.encode('ascii') + scaled.tobytes()
