# Make A Fire In Forest

English | [简体中文](docs/README-ZH.md)

A small desktop game for relaxation and curiosity: choose a city, load its surrounding landscape, light a spark in the forest, and watch the fire spread under local weather conditions.

The game combines real land-cover data with a simple grid-based fire simulation. Wind steers the spread, rain and snow suppress it, and animated weather brings the map to life.

> Designed for entertainment, not for predicting real wildfires or making fire-safety decisions.

## Features

- **Location selection:** automatic IP-based location or manual city search.
- **Local terrain:** forests, water, built-up areas, and other ground derived from ESA WorldCover 2021.
- **Adjustable map area:** 5 × 5, 10 × 10, 20 × 20, or 40 × 40 km.
- **Interactive fire:** click or drag to ignite forests; pause, adjust simulation speed, or reset the map.
- **Weather-driven spread:** faster downwind spread, slower upwind spread, and stronger suppression from rain and snow.
- **Map indicators:** wind direction and speed in the upper-left corner, with an N/E/S/W compass in the upper-right corner.
- **Animated precipitation:** rain, snow, or both, with Off / Light / Full display modes.
- **Fire statistics:** affected cell count and estimated area in hectares and square kilometres.
- **PNG export:** save the map together with weather, indicators, and fire statistics.

## Getting Started

### Run a packaged Windows build

If you have a packaged build:

1. Extract the downloaded archive, if applicable.
2. Double-click `MakeAFireInForest.exe`.
3. Wait for location and terrain loading, or search for a city manually.

For a folder-based build, keep the executable and its accompanying `_internal` folder together. Python does not need to be installed on the computer running a correctly packaged build.

An internet connection is required to retrieve location, weather, and terrain data. Packaging does not bundle worldwide maps or provide an offline weather service.

### Run from source

Use Python 3.12 as the suggested development and build environment. The application requires a graphical desktop and Tkinter, plus the packages listed in `requirements.txt`:

- NumPy
- Rasterio
- Pillow

Run the following commands from the project root.

**Windows — PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/main.py
```

**Linux**

```bash
python3 -m venv proj_env
./proj_env/bin/python -m pip install --upgrade pip
./proj_env/bin/python -m pip install -r requirements.txt
./proj_env/bin/python src/main.py
```

If `proj_env` already exists, reuse it. On Linux, Tkinter may need to be installed separately through your distribution's package manager; for example, `python3-tk` on Debian or Ubuntu.

**The executable package is also provided, see the release.**

## How to Play

1. Open **Location & Weather**. Let automatic location finish, or enter a city name, click **Search**, select a result, and click **Use Selected City**.
2. Wait for the terrain map to appear. If loading fails, use **Reload Terrain Map** to retry.
3. Click or drag across green forest cells to start a fire.
4. Watch the fire spread. Use the speed slider to change playback speed, or pause to inspect the map.
5. Use **Reset Map** to restore the original terrain and clear fire damage.

In **Forest Settings → Map area**, choose a different geographic range. The default is 10 × 10 km.

Changing the city or reloading the terrain starts a new scene and clears existing fires. **Refresh Weather** updates the weather without resetting the terrain. While terrain is loading or unavailable, the game does not substitute a randomly generated map.

### Controls

| Action | Control |
| --- | --- |
| Ignite forest | Left-click or drag on green cells |
| Pause / resume | Space or the Pause / Resume button |
| Restore terrain | R or Reset Map |
| Change simulation speed | Simulation speed slider |
| Change map area | Map area selector |
| Change weather visuals | Rain / snow effects selector |
| Export an image | Save Screenshot |

Keyboard shortcuts do not trigger while typing into city-search or other text-entry controls. You can place ignition points while the simulation is paused.

### Map legend

| Colour | Meaning | Flammable? |
| --- | --- | --- |
| Green | Forest | Yes |
| Tan | Other ground | No |
| Blue | Permanent water | No |
| Silver | Built-up land | No |
| Orange / yellow | Burning forest | Already burning |
| Dark grey | Ash / fire-damaged forest | No |
| Blue-grey | Missing or unknown terrain | No |

North is up and east is right. The wind arrow shows **where the wind blows toward**: a north wind points south on the map.

## Weather and Fire Behaviour

Each simulation step, a burning cell attempts to ignite its eight neighbouring forest cells. Newly ignited cells begin spreading on the following step.

### Wind

In calm, dry conditions, the ignition probability for each neighbouring forest cell is **22% per attempt**.

- Downwind spread becomes more likely as wind speed increases.
- Upwind spread becomes less likely as wind speed increases.
- An opposing wind component of **8 m/s or more** blocks spread in that direction.
- Oblique spread uses the wind component along the attempted direction, rather than the full wind speed.
- Direct crosswind spread uses the calm baseline.
- If wind direction is unavailable, the simulation uses the calm baseline for directional spread.

These probabilities influence how quickly a fire advances through the grid; wind does not change the simulation clock or allow fire to jump over cells.

### Rain and snow

Rain and snow both reduce ignition probability and shorten the lifetime of burning cells. Snow is converted to liquid-water equivalent for the fire model.

| Precipitation rate | Ignition probability relative to the same wind conditions without precipitation |
| --- | --- |
| 0 mm/h | 100% |
| 1 mm/h | About 45% |
| 2 mm/h | About 20% |
| 5 mm/h | About 1.8% |

Each newly ignited cell starts with a lifetime of 7 units. Every step, precipitation first removes `1.5 × precipitation_rate` units. A cell extinguished at this point cannot spread. Surviving cells attempt ignition and then lose another 1 unit.

At 5 mm/h, a newly ignited cell is extinguished before it can spread on the next step. Manual ignition remains possible, and extinguished cells become ash.

The model uses the API's precipitation accumulation interval to calculate hourly intensity. Total precipitation is used when available; otherwise, rain, showers, and snowfall are combined without counting snow twice.

Temperature and humidity are displayed but currently do not affect fire behaviour. Weather is fetched when a location is selected and can be updated with **Refresh Weather**. While weather is loading or unavailable, the simulation uses calm, dry conditions.

### Model formula

Let `u` be the wind component along the attempted spread direction, in m/s: positive downwind and negative upwind. Let `r` be liquid-equivalent precipitation intensity in mm/h.

```text
For u >= 0:
    wind_factor = 1 + 0.20 * u

For u < 0:
    wind_factor = max(0, 1 + u / 8) ** 2

ignition_probability = (1 - 0.78 ** wind_factor) * exp(-0.8 * r)
```

Simulation inputs are capped at 60 m/s for wind and 100 mm/h for precipitation. These are gameplay rules, not calibrated physical fire equations.

## Rain and Snow Effects

Rain appears as blue streaks and snow as drifting white particles. Higher precipitation intensity increases particle density and falling speed. Mixed rain and snow can appear together.

Use **Forest Settings → Rain / snow effects**:

| Mode | Visual behaviour |
| --- | --- |
| Off | No rain or snow particles |
| Light | Approximately one quarter of the particles, targeting about 15 frames per second |
| Full | Full particle density, targeting about 30 frames per second |

Actual frame rates depend on hardware and simulation load. Particle counts are capped to limit rendering cost.

This setting affects appearance only: **turning effects off does not disable the influence of weather on fire**. Weather animation continues while fire simulation is paused. Particles stay within the map and below the wind and compass cards.

## Fire Statistics and Screenshots

The footer below the map instructions shows:

- Total fire-affected cells: **currently burning cells + ash cells**.
- Approximate affected area in hectares and square kilometres.
- Separate counts for burning cells and ash cells.

Area is calculated from the loaded map:

```text
cell_area_km2 = (map_side_km / grid_size) ** 2
fire_affected_area_km2 = (burning_cells + ash_cells) * cell_area_km2
```

A cell represents a patch of land, not an individual tree. Resetting or replacing the map clears the affected-area statistics.

Click **Save Screenshot** to choose a destination and export a PNG. The image includes the current terrain and fire, visible rain/snow, wind and compass indicators, city and weather information, map range, and affected-area statistics. The image is captured before the save dialog opens.

Export renders the map directly rather than capturing other desktop windows. Screenshot export is available after a terrain map has loaded.

## Terrain Data and Map Scale

The map uses **ESA WorldCover 2021 v200**, a historical land-cover classification with approximately 10 m source resolution. All map ranges use a **400 × 400** simulation grid.

| Map area | Approximate cell width |
| --- | --- |
| 5 × 5 km | 12.5 m |
| 10 × 10 km | 25 m |
| 20 × 20 km | 50 m |
| 40 × 40 km | 100 m |

Source pixels are aggregated into game cells using latitude-weighted terrain votes. Forest includes tree cover and mangroves; built-up land becomes city terrain; permanent water becomes water; other valid classes become ground.

The game preserves the geographic arrangement of terrain rather than randomly placing trees. Small forests, narrow rivers, and other fine features may disappear during aggregation, especially at larger map ranges.

Maps cover a square around the selected coordinates, not an entire administrative region. Supported centre latitudes are between 80°S and 80°N. Insufficient valid source coverage or an unavailable source tile causes a loading error.

Successful maps are cached for up to 16 location/range combinations during the current session. The application does not currently maintain a persistent offline map cache.


## Project Structure

```text
Make_a_fire_in_forest/
├── src/
│   ├── main.py              # Application window, controls, and simulation loop
│   ├── forest.py            # Fire states and spread rules
│   ├── weather.py           # Location, city search, and weather adapters
│   ├── landcover.py         # Terrain retrieval and aggregation
│   ├── location_panel.py    # Location and weather controls
│   ├── coverage_panel.py    # Background terrain loading
│   ├── map_config.py        # Grid and map-range settings
│   ├── map_renderer.py      # Raster map rendering
│   ├── weather_effects.py   # Animated rain and snow
│   └── screenshot.py        # PNG map export
├── docs/                    # Additional documentation
├── requirements.txt
└── README.md
```


## Troubleshooting and Limitations

- **Automatic location is incorrect:** IP location is approximate and may reflect a VPN or proxy. Search for a city manually.
- **Terrain does not load:** check the connection, retry loading, or try a smaller map range or another location. Larger ranges require more source data.
- **No forest is visible:** the selected square may contain mostly built-up land, water, or other ground. Try another location or a larger map area.
- **Weather is unavailable:** use Refresh Weather to retry. Calm, dry fallback conditions apply while weather is unavailable.
- **Animation is slow:** select Light or Off for rain/snow effects and reduce simulation speed.
- **Screenshot text is missing or displayed as boxes:** font availability affects export. The current exporter first tries Linux `fc-match`, then DejaVu Sans, then Pillow's default font. Windows and non-Latin text may need platform-specific font configuration; Chinese font support is not bundled.
- **Different map ranges appear to spread at similar speeds:** the rules operate on grid steps. Changing map range changes metres per cell without recalibrating propagation time.

The model does not simulate terrain slope, fuel differences, soil moisture, snow accumulation, urban fires, or grass fires. Land cover is historical rather than a live street or satellite map. Location, weather, and terrain retrieval depend on third-party services and their availability.

## Data Sources and Attribution

- **Land cover:** [ESA WorldCover data access](https://esa-worldcover.org/en/data-access) and the [WorldCover 2021 dataset](https://doi.org/10.5281/zenodo.7254221), distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **IP location:** [ipapi](https://ipapi.co/api/).
- **City search:** GeoNames through the [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api).
- **Weather:** [Open-Meteo](https://open-meteo.com/en/docs). See its [terms and usage information](https://open-meteo.com/en/pricing).

Terrain is retrieved from public Cloud Optimized GeoTIFFs hosted on AWS using partial reads; no worldwide dataset download is required.

© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
