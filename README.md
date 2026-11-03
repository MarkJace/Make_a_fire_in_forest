# Make a Fire in Forest

An English-language desktop game that turns real land-cover data around a selected city into a playable map. Forests, ground, water and built-up areas retain their geographic arrangement. There is no density slider or randomly generated replacement map.

## Run

```bash
cd ~/repositories/Make_a_fire_in_forest
./proj_env/bin/python -m pip install -r requirements.txt
./proj_env/bin/python main.py
```

Use the existing `proj_env` environment. A graphical desktop is required. Rasterio and NumPy read satellite raster data.

## Play

1. Let automatic IP location finish, or search for a city and choose **Use Selected City** in Location & Weather.
2. The game loads a selectable **5 × 5, 10 × 10, 20 × 20, or 40 × 40 km** area centered on the selected coordinates and automatically displays its terrain. Switching locations starts a new scene. In **Forest Settings → Map area**, choose a range to reload the scene around the same center. The default is 10 × 10 km.
3. Click or drag over green forest cells to ignite them. Space pauses/resumes the simulation; the speed slider changes playback speed.
4. **Reset Map** or R restores the exact original terrain for that location, including forests damaged by fire.
5. Scroll Location & Weather to **Local Terrain Map** to see the class proportions and use **Reload Terrain Map** to retry.

Legend:
- Green: forest (flammable).
- Tan: other ground (nonflammable in this game).
- Blue: permanent water (nonflammable).
- Silver: city / built-up areas (nonflammable).
- Orange: fire; dark gray: ash.
- Blue-gray: missing or unknown data (nonflammable).

While the map is loading or unavailable, ignition and simulation are unavailable. Failures show a retry message; the game does not invent terrain or use a default forest density. Existing fires are cleared on changing or reloading the map. Refreshing weather alone does not reset the map.

## Geographic map generation

Source: **ESA WorldCover 2021 v200**, historical 10 m satellite land-cover classification. Every map uses **400 × 400 game cells** (160,000 cells). Select a local square of 5, 10, 20 or 40 km per side. Cell sizes are approximately 12.5, 25, 50 and 100 m respectively. North is up and east is right.

For each game cell, the native satellite pixels in that geographic area vote for the dominant terrain type, weighted by cosine of latitude. Votes are combined across source-tile boundaries and the antimeridian before selecting a terrain type. No random placement is used.

| ESA class | Game terrain |
| --- | --- |
| 10: tree cover; 95: mangroves | Forest |
| 80: permanent water bodies | Water |
| 50: built-up | City |
| Other valid classes (grass, crops, shrubland, bare ground, snow/ice, wetlands, moss/lichen) | Ground |
| Missing or invalid data | Unknown |

Ties use the fixed order ground, forest, water, city, unknown. Cells without samples remain unknown. Less than 95% valid source coverage or an unavailable tile produces an error. Sampling supports latitudes between 80°S and 80°N.

This is a generalized historical map, not a live street map: narrow rivers and small urban or forest patches can disappear when aggregated to game cells, particularly at the larger map ranges. City cells represent built-up land, not individual buildings or administrative boundaries. Only forests burn; urban fires and grass fires are outside the current model. The area covers a city center and its immediate surroundings, not its entire administrative boundary.

Public AWS Cloud Optimized GeoTIFFs are read using HTTP Range requests without an account or a global download. Connection/transfer timeouts are 10/30 seconds per request, with one retry. Successful maps are cached for up to 16 location/range combinations during the session, so reloading the same place can reuse its map. Old query results cannot replace a newer location or map range. Native rasters are read in bounded chunks to limit memory use on large maps. Larger areas require more data and may load more slowly.

## Location and weather

Startup contacts ipapi to estimate your location from the public network IP. A VPN or proxy can change this estimate. You can always search and select a city manually; manual selection takes priority over a pending automatic request. City search requests English place names when available and still accepts names in other languages.

Open-Meteo supplies city search and weather data. Weather queries run independently in background threads with a 10-second timeout. The weather panel displays temperature, humidity, wind, rain, showers, snow, and the location's weather time/time zone. Refresh Weather updates weather without regenerating the terrain.

## Weather effects

- Higher wind speeds increase the probability of igniting neighboring trees, especially downwind. North is at the top of the map: a north wind blows fire southward. If wind direction is missing, the increase applies uniformly.
- Heavier rain or snow reduces ignition probability and shortens the remaining lifetime of burning cells. Cells extinguished by precipitation cannot ignite neighbors in that step.
- Total precipitation already includes rain, showers, and the water equivalent of snow. The game converts the API accumulation interval (`current.interval`) into mm/h without counting snow twice. If the total is missing, it estimates it as rain + showers + snowfall in cm / 0.7.
- While weather is unavailable, refreshing, or changing cities, the simulation uses calm, dry conditions. Missing fields are indicated above the map.
- Extinguished cells remain ash, representing fire damage. Temperature and humidity are currently displayed but do not affect the simulation.

The base ignition probability is 0.22. The wind factor is `1 + 0.12 * wind_speed * (1 + 0.8 * downwind_alignment)` and the wetness factor is `1 + 0.7 * precipitation_rate`.

Ignition probability is `1 - 0.78 ** (wind_factor / wetness_factor)`. Burning cells begin with a lifetime of 7 steps. Each step, precipitation first removes `0.7 * precipitation_rate` from the remaining lifetime, followed by the usual decrease of 1. Simulation inputs are capped at 60 m/s wind and 100 mm/h precipitation.

These simplified rules are designed for gameplay, not real-world fire prediction.

## Tests

```bash
./proj_env/bin/python -B -m unittest -v
```

Tests cover geographic orientation, class mapping, aggregation, tile/dateline stitching, missing data, nonflammable barriers, reset behavior, weather effects, and network error handling.

## Data sources and attribution

- [ESA WorldCover data access](https://esa-worldcover.org/en/data-access)
- [WorldCover 2021 dataset DOI](https://doi.org/10.5281/zenodo.7254221), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- [IP location: ipapi](https://ipapi.co/api/)
- [City search: GeoNames via Open-Meteo](https://open-meteo.com/en/docs/geocoding-api)
- [Weather model data: Open-Meteo](https://open-meteo.com/en/docs)
- [Open-Meteo terms and usage limits](https://open-meteo.com/en/pricing)

© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.

## Grid and display performance

The 400 × 400 simulation grid is drawn as a single raster image, scaled with nearest-neighbor sampling, rather than 160,000 canvas rectangles. Mouse coordinates map to the same grid used for rendering. The Forest Settings and Location & Weather panels can both be scrolled in smaller windows.

The fire rules still operate per grid step. Changing geographic range changes the meters represented by one cell; these are gameplay rules, not a calibrated physical spread speed in meters per second.
