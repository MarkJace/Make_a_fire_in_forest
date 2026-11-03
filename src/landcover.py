"""Area-weighted tree cover from native ESA WorldCover 2021 raster pixels."""
import math
from dataclasses import dataclass
from functools import lru_cache
from map_config import GRID_SIZE, MAP_SIZES_KM, DEFAULT_SIDE_KM
from forest import EMPTY, TREE, WATER, CITY, UNKNOWN

SOURCE = 'ESA WorldCover 2021 v200 (10 m)'
BASE_URL = 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/'
CLASSES = (10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100)

class LandCoverError(Exception):
    pass

@dataclass(frozen=True)
class Coverage:
    fraction: float
    valid_fraction: float
    pixels: int
    terrain: tuple = ()
    latitude: float = 0
    longitude: float = 0
    size: int = GRID_SIZE
    side_km: float = DEFAULT_SIDE_KM
    source: str = SOURCE


def region_bounds(latitude, longitude, side_km=DEFAULT_SIDE_KM):
    if not (math.isfinite(latitude) and math.isfinite(longitude)
            and -80 <= latitude <= 80 and -180 <= longitude <= 180):
        raise LandCoverError('Coverage supports locations between 80°S and 80°N.')
    if side_km not in MAP_SIZES_KM:
        raise LandCoverError('Unsupported sampling size.')
    dy = side_km / (2 * 111.195)
    dx = dy / math.cos(math.radians(latitude))
    w, e, s, n = longitude-dx, longitude+dx, latitude-dy, latitude+dy
    if w < -180:
        return [(w+360, s, 180, n), (-180, s, e, n)]
    if e > 180:
        return [(w, s, 180, n), (-180, s, e-360, n)]
    return [(w, s, e, n)]


def tile_regions(bounds):
    w, s, e, n = bounds
    for lat in range(math.floor(s/3)*3, math.ceil(n/3)*3, 3):
        for lon in range(math.floor(w/3)*3, math.ceil(e/3)*3, 3):
            tile = f'{"N" if lat >= 0 else "S"}{abs(lat):02d}{"E" if lon >= 0 else "W"}{abs(lon):03d}'
            url = BASE_URL + f'ESA_WorldCover_10m_2021_v200_{tile}_Map.tif'
            yield url, (max(w, lon), max(s, lat), min(e, lon+3), min(n, lat+3))


def weighted_counts(values, row_latitudes):
    import numpy as np
    weights = np.cos(np.radians(row_latitudes))[:, None]
    valid = (~np.ma.getmaskarray(values)) & np.isin(np.ma.getdata(values), CLASSES)
    trees = valid & np.isin(np.ma.getdata(values), (10, 95))
    return (float((trees*weights).sum()), float((valid*weights).sum()),
            float(weights.sum()*values.shape[1]), int(valid.sum()))


def terrain_votes(values, latitudes, longitudes, latitude, longitude, size=GRID_SIZE, side_km=DEFAULT_SIDE_KM):
    """Assign every native pixel to a north-up game cell, then vote by area."""
    import numpy as np
    dy = side_km / (2 * 111.195)
    dx = dy / math.cos(math.radians(latitude))
    longitudes = longitude + (np.asarray(longitudes) - longitude + 180) % 360 - 180
    rows = np.floor((latitude + dy - np.asarray(latitudes)) / (2*dy) * size).astype(int)
    cols = np.floor((longitudes - (longitude - dx)) / (2*dx) * size).astype(int)
    inside = (rows[:, None] >= 0) & (rows[:, None] < size) & (cols[None, :] >= 0) & (cols[None, :] < size)
    raw = np.ma.getdata(values)
    valid = (~np.ma.getmaskarray(values)) & np.isin(raw, CLASSES)
    categories = np.full(values.shape, 4, dtype=int)  # unknown is not ordinary land
    categories[valid] = 0
    categories[valid & np.isin(raw, (10, 95))] = 1
    categories[valid & (raw == 80)] = 2
    categories[valid & (raw == 50)] = 3
    indices = ((rows[:, None] * size + cols[None, :]) * 5 + categories)[inside]
    weights = np.broadcast_to(np.cos(np.radians(latitudes))[:, None], values.shape)[inside]
    return np.bincount(indices, weights=weights, minlength=size*size*5).reshape(size*size, 5)


def terrain_from_votes(votes):
    import numpy as np
    kinds = np.array([EMPTY, TREE, WATER, CITY, UNKNOWN])
    cells = kinds[votes.argmax(axis=1)]
    cells[votes.sum(axis=1) == 0] = UNKNOWN
    return tuple(int(cell) for cell in cells)


@lru_cache(maxsize=16)
def fetch_coverage(latitude, longitude, side_km=DEFAULT_SIDE_KM):
    bounds_list = region_bounds(latitude, longitude, side_km)
    try:
        import numpy as np
        import rasterio
        from rasterio.windows import Window, from_bounds
    except ImportError as error:
        raise LandCoverError('Install requirements.txt in proj_env to load land cover.') from error
    votes = np.zeros((GRID_SIZE * GRID_SIZE, 5), dtype=float)
    tree_area = valid_area = total_area = 0.0
    pixel_count = 0
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                          CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',
                          GDAL_HTTP_CONNECTTIMEOUT='10', GDAL_HTTP_TIMEOUT='30',
                          GDAL_HTTP_MAX_RETRY='1', GDAL_HTTP_RETRY_DELAY='1'):
            for bounds in bounds_list:
                for url, intersection in tile_regions(bounds):
                    with rasterio.open(url) as src:
                        raw = from_bounds(*intersection, transform=src.transform)
                        # Select pixels by their centers; neighboring tiles cannot overlap.
                        x0 = max(0, math.ceil(raw.col_off-0.5))
                        y0 = max(0, math.ceil(raw.row_off-0.5))
                        x1 = min(src.width, math.ceil(raw.col_off+raw.width-0.5))
                        y1 = min(src.height, math.ceil(raw.row_off+raw.height-0.5))
                        if x1 <= x0 or y1 <= y0:
                            continue
                        # Bounded native-raster chunks avoid huge arrays for 40 km maps.
                        for by in range(y0, y1, 512):
                            for bx in range(x0, x1, 1024):
                                ex, ey = min(x1, bx+1024), min(y1, by+512)
                                values = src.read(1, window=Window(bx, by, ex-bx, ey-by), masked=True)
                                latitudes = src.transform.f + (np.arange(by, ey)+0.5)*src.transform.e
                                longitudes = src.transform.c + (np.arange(bx, ex)+0.5)*src.transform.a
                                votes += terrain_votes(values, latitudes, longitudes, latitude, longitude,
                                                       size=GRID_SIZE, side_km=side_km)
                                trees, valid, total, pixels = weighted_counts(values, latitudes)
                                tree_area += trees
                                valid_area += valid
                                total_area += total
                                pixel_count += pixels
    except Exception as error:
        raise LandCoverError('Land-cover data unavailable. Check your connection and retry; choose another location or retry.') from error
    if total_area <= 0 or valid_area / total_area < 0.95:
        raise LandCoverError('Insufficient land-cover data here. Please choose another location or retry.')
    return Coverage(min(1.0, tree_area / valid_area), min(1.0, valid_area / total_area), pixel_count,
                    terrain=terrain_from_votes(votes), latitude=latitude, longitude=longitude, size=GRID_SIZE, side_km=side_km)
