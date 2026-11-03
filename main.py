"""Run with ./proj_env/bin/python main.py."""
import tkinter as tk
from tkinter import ttk
from map_config import GRID_SIZE, MAP_SIZES_KM, DEFAULT_SIDE_KM
from map_renderer import map_ppm

from forest import ASH, EMPTY, FIRE, TREE, WATER, CITY, UNKNOWN, Forest
from location_panel import LocationPanel
from weather import simulation_weather, precipitation_rate

BG = '#111d19'
PANEL = '#1b2b24'
TEXT = '#e4eee5'
MUTED = '#a5bcad'
COLORS = {EMPTY: '#a9956b', TREE: '#4f995b', ASH: '#4b4742',
          WATER: '#297fba', CITY: '#a5acb9', UNKNOWN: '#26323b'}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('Forest Fire')
        self.root.geometry('1050x810')
        self.root.minsize(800, 640)
        self.root.configure(bg=BG)
        self.paused = False
        self.has_ignited = False
        self.coverage = None
        self.map_extent = tk.StringVar(value=f'{DEFAULT_SIDE_KM} × {DEFAULT_SIDE_KM} km')
        self.grid_text = tk.StringVar(value=f'{GRID_SIZE} × {GRID_SIZE} cells · 25 m/cell\nNorth ↑ · East →')
        self.coverage_status = tk.StringVar(value='Waiting for a real terrain map.')
        self.speed = tk.DoubleVar(value=1)
        self.weather_data = None
        self.effect_text = tk.StringVar(value='Weather unavailable: using calm, dry conditions')
        self.status = tk.StringVar()
        self.stats = tk.StringVar()
        self.speed_label = tk.StringVar()
        self.cell_size = 6
        self.offset = (0, 0)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=10, font=('', 11))

        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=24, pady=(20, 12))
        tk.Label(header, text='Forest Fire', font=('', 25, 'bold'),
                 bg=BG, fg=TEXT).pack(anchor='w')
        tk.Label(header, text='Grow a forest, light a spark, and watch it spread.',
                 bg=BG, fg=MUTED, font=('', 11)).pack(anchor='w', pady=(6, 0))

        tk.Label(header, textvariable=self.effect_text, bg=BG, fg='#e7bb73',
                 font=('', 10), wraplength=950, justify='left').pack(anchor='w', pady=(7, 0))

        body = tk.Frame(root, bg=BG)
        body.pack(fill='both', expand=True, padx=24)
        tabs = ttk.Notebook(body, width=310)
        tabs.pack(side='right', fill='y', padx=(18, 0))
        self.settings_tab = tk.Frame(tabs, bg=PANEL)
        settings_view = tk.Canvas(self.settings_tab, bg=PANEL, highlightthickness=0, width=310)
        settings_scroll = ttk.Scrollbar(self.settings_tab, orient='vertical', command=settings_view.yview)
        settings_scroll.pack(side='right', fill='y')
        settings_view.pack(side='left', fill='both', expand=True)
        settings_view.configure(yscrollcommand=settings_scroll.set)
        controls = tk.Frame(settings_view, bg=PANEL)
        controls_window = settings_view.create_window((0, 0), window=controls, anchor='nw')
        controls.bind('<Configure>', lambda event: settings_view.configure(scrollregion=settings_view.bbox('all')))
        settings_view.bind('<Configure>', lambda event: settings_view.itemconfigure(controls_window, width=event.width))
        tabs.add(self.settings_tab, text='Forest Settings')
        location_tab = tk.Frame(tabs, bg=PANEL)
        self.weather_view = tk.Canvas(location_tab, bg=PANEL, highlightthickness=0, width=310)
        weather_scroll = ttk.Scrollbar(location_tab, orient='vertical', command=self.weather_view.yview)
        weather_scroll.pack(side='right', fill='y')
        self.weather_view.pack(side='left', fill='both', expand=True)
        self.weather_view.configure(yscrollcommand=weather_scroll.set)
        self.location_panel = LocationPanel(self.weather_view, on_weather=self.apply_weather,
                                            on_coverage=self.apply_coverage)
        panel_window = self.weather_view.create_window((0, 0), window=self.location_panel, anchor='nw')
        self.location_panel.bind('<Configure>', lambda event: self.weather_view.configure(
            scrollregion=self.weather_view.bbox('all')), add='+')
        self.weather_view.bind('<Configure>', lambda event: self.weather_view.itemconfigure(
            panel_window, width=event.width))
        tabs.add(location_tab, text='Location & Weather')
        tabs.select(location_tab)
        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda event: self.draw_all())
        self.canvas.bind('<Button-1>', self.ignite)
        self.canvas.bind('<B1-Motion>', self.ignite)

        def label(text=None, variable=None, **kwargs):
            widget = tk.Label(controls, text=text, textvariable=variable,
                              bg=PANEL, fg=TEXT, anchor='w', justify='left', **kwargs)
            widget.pack(fill='x', padx=18, pady=(8, 3))
            return widget

        label('Forest Settings', font=('', 14, 'bold'))
        label(variable=self.coverage_status, font=('', 10), wraplength=270)
        label('Map area (changes reload the scene)', font=('', 10))
        self.extent_select = ttk.Combobox(controls, textvariable=self.map_extent, state='readonly',
                                         values=[f'{km} × {km} km' for km in MAP_SIZES_KM])
        self.extent_select.pack(fill='x', padx=18)
        self.extent_select.bind('<<ComboboxSelected>>', self.change_extent)
        label(variable=self.grid_text, font=('', 10))
        label(variable=self.speed_label)
        self.scale(controls, self.speed, 0.25, 4, 0.25,
                   lambda value: self.speed_label.set(f'Simulation speed · {float(value):g}×'))
        self.speed_label.set('Simulation speed · 1×')
        self.pause_button = ttk.Button(controls, text='Pause', command=self.toggle_pause)
        self.pause_button.pack(fill='x', padx=18, pady=(22, 8))
        self.reset_button = ttk.Button(controls, text='Reset Map', command=self.reset, state='disabled')
        self.reset_button.pack(fill='x', padx=18)
        label('Forest Statistics', font=('', 14, 'bold'))
        label(variable=self.stats, font=('', 11))
        label('● Green: forest · burns\n● Tan: ground · nonflammable\n● Blue: water · nonflammable\n● Silver: city · nonflammable\n● Orange: fire · dark gray: ash\n● Blue-gray: unknown data', font=('', 10))
        label('Click or drag to ignite\nSpace: pause / resume\nR: reset this map', font=('', 10))
        tk.Label(root, textvariable=self.status, bg=BG, fg=MUTED,
                 anchor='w', font=('', 11)).pack(fill='x', padx=24, pady=16)
        root.bind('<space>', lambda event: self.shortcut(event, self.toggle_pause))
        root.bind('<Key-r>', lambda event: self.shortcut(event, self.reset))
        root.bind('<Key-R>', lambda event: self.shortcut(event, self.reset))
        self.reset()
        self.tick()

    def change_extent(self, event=None):
        side_km = int(self.map_extent.get().split()[0])
        self.grid_text.set(f'{GRID_SIZE} × {GRID_SIZE} cells · {side_km*1000/GRID_SIZE:g} m/cell\nNorth ↑ · East →')
        self.location_panel.coverage_panel.set_extent(side_km)

    def apply_coverage(self, result, error=None):
        self.coverage = result
        if result is None:
            self.coverage_status.set(error or 'Loading terrain for the selected location…')
        else:
            self.coverage_status.set(f'Terrain center: {result.latitude:.4f}, {result.longitude:.4f}\n'
                                     'ESA WorldCover 2021 · real land-cover layout')
        self.reset()

    def apply_weather(self, data):
        self.weather_data = data
        parameters = simulation_weather(data)
        if hasattr(self, 'forest'):
            self.forest.set_weather(**parameters)
        if data is None:
            self.effect_text.set('Weather unavailable: using calm, dry conditions')
            return
        speed, rate = parameters['wind_speed'], parameters['precipitation_rate']
        missing = []
        if data.get('wind_speed_10m') is None:
            missing.append('wind speed missing: calm')
        if data.get('wind_direction_10m') is None:
            missing.append('wind direction missing: uniform spread')
        if precipitation_rate(data) is None:
            missing.append('precipitation missing: dry')
        self.effect_text.set(f'Weather active: wind {speed:g} m/s · rain/snow equivalent {rate:g} mm/h'
                             + (' · ' + '; '.join(missing) if missing else ' · north is up'))

    def shortcut(self, event, action):
        # Typing city names must not pause or reset the forest.
        if event.widget.winfo_class() not in ('Entry', 'TEntry', 'Text', 'TCombobox'):
            action()

    @staticmethod
    def scale(parent, variable, start, end, resolution, command):
        slider = tk.Scale(parent, variable=variable, from_=start, to=end, resolution=resolution,
                 orient='horizontal', showvalue=False, command=command,
                 bg=PANEL, fg=TEXT, troughcolor=BG, highlightthickness=0,
                 activebackground='#87bb81')
        slider.pack(fill='x', padx=18)
        return slider

    def color(self, index):
        state = self.forest.cells[index]
        if state == FIRE:
            return ('#ffcc67', '#ff983f', '#eb6135')[(int(self.forest.ages[index]) + index) % 3]
        if state == TREE:
            return ('#477f50', '#55965e', '#65a168')[index % 3]
        return COLORS[state]

    def paint_map(self):
        self.map_image = tk.PhotoImage(data=map_ppm(self.forest, self.render_side), format='PPM')
        self.canvas.itemconfigure(self.map_item, image=self.map_image)

    def draw_all(self):
        self.canvas.delete('all')
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.render_side = max(1, min(width, height) - 4)
        self.cell_size = self.render_side / self.forest.size
        self.offset = ((width - self.render_side) / 2, (height - self.render_side) / 2)
        self.map_item = self.canvas.create_image(*self.offset, anchor='nw')
        self.paint_map()
        if self.coverage is None:
            self.canvas.create_text(width/2, height/2, text=self.coverage_status.get(),
                                    fill=TEXT, font=('', 16), width=max(100, width-40))

    def reset(self):
        terrain = self.coverage.terrain if self.coverage else (UNKNOWN,) * (GRID_SIZE * GRID_SIZE)
        self.forest = Forest(size=GRID_SIZE, terrain=terrain)
        self.reset_button.configure(state='normal' if self.coverage else 'disabled')
        self.forest.set_weather(**simulation_weather(self.weather_data))
        self.has_ignited = False
        self.paused = False
        self.pause_button.configure(text='Pause', state='normal' if self.coverage else 'disabled')
        self.draw_all()
        self.update_stats()

    def toggle_pause(self):
        if self.coverage is None:
            return
        self.paused = not self.paused
        self.pause_button.configure(text='Resume' if self.paused else 'Pause')
        self.update_stats()

    def ignite(self, event):
        ox, oy = self.offset
        col = int((event.x - ox) // self.cell_size)
        row = int((event.y - oy) // self.cell_size)
        if self.forest.ignite(row, col):
            self.has_ignited = True
            self.paint_map()
            self.update_stats()

    def update_stats(self):
        counts = self.forest.counts()
        ratio = 100 * counts[ASH] / max(1, self.forest.initial_trees)
        self.stats.set(f'Living trees   {counts[TREE]:,}\nBurning      {counts[FIRE]:,}'
                       f'\nBurned      {counts[ASH]:,}({ratio:.1f}%)'
                       f'\nWater cells   {counts[WATER]:,} · City cells   {counts[CITY]:,}'
                       f'\nSimulation steps   {self.forest.steps}')
        if self.coverage is None:
            message = 'Map unavailable · Select a city or retry Reload Terrain Map. No synthetic terrain is used.'
        elif self.paused:
            message = 'Paused · Click trees to ignite, then Resume to spread the fire.'
        elif counts[FIRE]:
            message = 'Fire is spreading · Click more trees to add ignition points.'
        elif self.has_ignited:
            message = 'Fire is out · Ignite remaining trees or reset this map.'
        elif not self.forest.initial_trees:
            message = 'No forest cells in this area · Select another city to find forests.'
        else:
            message = 'Click green forest cells to ignite · Ground, water and cities do not burn.'
        self.status.set(message)

    def tick(self):
        if not self.paused and FIRE in self.forest.cells:
            self.forest.step()
            self.paint_map()
            self.update_stats()
        self.root.after(max(15, int(120 / self.speed.get())), self.tick)


if __name__ == '__main__':
    window = tk.Tk()
    App(window)
    window.mainloop()
