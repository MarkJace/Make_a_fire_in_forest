"""Run with ./proj_env/bin/python src/main.py."""
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from map_config import GRID_SIZE, MAP_SIZES_KM, DEFAULT_SIDE_KM
from map_renderer import map_ppm
from weather_effects import WeatherEffects

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
        self.root.title('Make A Fire In Forest')
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
        self.city_text = tk.StringVar(value='Locating your forest…')
        self.weather_text = tk.StringVar(value='Waiting for local weather')
        self.overlay_bounds = []
        self.effect_text = tk.StringVar(value='Weather unavailable: using calm, dry conditions')
        self.status = tk.StringVar()
        self.stats = tk.StringVar()
        self.burn_stats = tk.StringVar()
        self.effect_quality = tk.StringVar(value='Full')
        self.speed_label = tk.StringVar()
        self.cell_size = 6
        self.offset = (0, 0)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=10, font=('', 11), background=PANEL, foreground=TEXT,
                        borderwidth=0)
        style.map('TButton', background=[('active', '#345443')],
                  foreground=[('disabled', '#718579')])
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', background=PANEL, foreground=MUTED, padding=(12, 10))
        style.map('TNotebook.Tab', background=[('selected', '#345443')],
                  foreground=[('selected', TEXT)])

        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=24, pady=(20, 12))
        tk.Label(header, text='Make A Fire In Forest', font=('', 26, 'bold'),
                 bg=BG, fg=TEXT).pack(anchor='w')
        tk.Frame(header, bg='#d9a65d', height=3, width=56).pack(anchor='w', pady=(10, 12))
        summary = tk.Frame(header, bg=PANEL, padx=14, pady=10)
        summary.pack(fill='x')
        city_label = tk.Label(summary, textvariable=self.city_text, font=('', 13, 'bold'),
                             bg=PANEL, fg=TEXT, anchor='w', justify='left')
        city_label.pack(fill='x')
        weather_label = tk.Label(summary, textvariable=self.weather_text, font=('', 11),
                                bg=PANEL, fg=MUTED, anchor='w', justify='left')
        weather_label.pack(fill='x', pady=(5, 0))
        summary.bind('<Configure>', lambda event: [widget.configure(wraplength=max(100, event.width-28))
                                                   for widget in (city_label, weather_label)])

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
                                            on_coverage=self.apply_coverage, on_location=self.apply_location)
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
        self.weather_effects = WeatherEffects(self.canvas)

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
        label(variable=self.effect_text, font=('', 10), wraplength=270)
        label('Rain / snow effects')
        quality = ttk.Combobox(controls, textvariable=self.effect_quality, state='readonly',
                               values=('Off', 'Light', 'Full'))
        quality.pack(fill='x', padx=18)
        quality.bind('<<ComboboxSelected>>', lambda event: self.weather_effects.set_quality(self.effect_quality.get()))
        label(variable=self.speed_label)
        self.scale(controls, self.speed, 0.25, 4, 0.25,
                   lambda value: self.speed_label.set(f'Simulation speed · {float(value):g}×'))
        self.speed_label.set('Simulation speed · 1×')
        self.pause_button = ttk.Button(controls, text='Pause', command=self.toggle_pause)
        self.pause_button.pack(fill='x', padx=18, pady=(22, 8))
        self.reset_button = ttk.Button(controls, text='Reset Map', command=self.reset, state='disabled')
        self.reset_button.pack(fill='x', padx=18)
        self.screenshot_button = ttk.Button(controls, text='Save Screenshot', command=self.save_screenshot,
                                             state='disabled')
        self.screenshot_button.pack(fill='x', padx=18, pady=(8, 0))
        label('Forest Statistics', font=('', 14, 'bold'))
        label(variable=self.stats, font=('', 11))
        label('● Green: forest · burns\n● Tan: ground · nonflammable\n● Blue: water · nonflammable\n● Silver: city · nonflammable\n● Orange: fire · dark gray: ash\n● Blue-gray: unknown data', font=('', 10))
        label('Click or drag to ignite\nSpace: pause / resume\nR: reset this map', font=('', 10))
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill='x', padx=24, pady=(10, 14))
        status_label = tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED,
                               anchor='w', justify='left', font=('', 10))
        status_label.pack(fill='x')
        burn_label = tk.Label(footer, textvariable=self.burn_stats, bg=BG, fg='#f1bc72',
                             anchor='w', justify='left', font=('', 11, 'bold'))
        burn_label.pack(fill='x', pady=(6, 0))
        footer.bind('<Configure>', lambda event: [w.configure(wraplength=max(100, event.width))
                                                  for w in (status_label, burn_label)])
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

    def apply_location(self, location):
        self.city_text.set(location.name if location else 'No city selected · Auto-locate or search')

    def update_weather_summary(self):
        data = self.weather_data
        if data is None:
            self.weather_text.set('Weather loading or unavailable · Calm, dry simulation')
            return
        def value(key, unit):
            number = data.get(key)
            return '—' if number is None else f'{number:g}{unit}'
        rate = precipitation_rate(data)
        wet = '—' if rate is None else f'{rate:g} mm/h'
        self.weather_text.set(f"Temperature {value('temperature_2m', ' °C')}   ·   "
                              f"Humidity {value('relative_humidity_2m', '%')}   ·   "
                              f"Wind {value('wind_speed_10m', ' m/s')}   ·   Rain / snow {wet}")

    def apply_weather(self, data):
        self.weather_data = data
        self.weather_effects.set_weather(data)
        self.update_weather_summary()
        if hasattr(self, 'map_item'):
            self.draw_overlays()
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
        self.weather_effects.set_bounds((*self.offset, self.render_side) if self.coverage is not None else None)
        self.draw_overlays()
        if self.coverage is None:
            self.canvas.create_text(width/2, height/2, text=self.coverage_status.get(),
                                    fill=TEXT, font=('', 16), width=max(100, width-40))

    def draw_overlays(self):
        canvas = self.canvas
        canvas.delete('overlay')
        self.overlay_bounds = []
        if self.render_side < 280:
            return
        ox, oy = self.offset
        def card(x, y, w, h):
            self.overlay_bounds.append((x, y, x+w, y+h))
            canvas.create_rectangle(x, y, x+w, y+h, fill=BG, outline='#476452',
                                    width=1, tags='overlay')
        def text(x, y, label, color=TEXT, size=10, anchor='center'):
            canvas.create_text(x, y, text=label, fill=color, font=('', size, 'bold'),
                               anchor=anchor, tags='overlay')
        x, y = ox+12, oy+12
        card(x, y, 146, 98)
        text(x+12, y+15, 'WIND', MUTED, 9, 'w')
        data = self.weather_data or {}
        speed, direction = data.get('wind_speed_10m'), data.get('wind_direction_10m')
        text(x+61, y+43, '— m/s' if speed is None else f'{speed:g} m/s', anchor='w', size=12)
        cx, cy = x+30, y+48
        if speed is not None and speed > 0 and direction is not None:
            angle = math.radians(direction)
            dx, dy = -math.sin(angle)*19, math.cos(angle)*19
            canvas.create_line(cx-dx, cy-dy, cx+dx, cy+dy, arrow=tk.LAST,
                               arrowshape=(10, 12, 5), fill='#f1bc72', width=3, tags='overlay')
            text(x+73, y+81, 'Arrow: wind blows to', MUTED, 9)
        else:
            canvas.create_oval(cx-7, cy-7, cx+7, cy+7, outline=MUTED, width=2, tags='overlay')
            label = 'Wind unavailable' if speed is None else ('Calm' if speed == 0 else 'Direction unavailable')
            text(x+73, y+81, label, MUTED, 9)
        x, y = ox+self.render_side-110, oy+12
        card(x, y, 98, 98)
        cx, cy = x+49, y+49
        for dx, dy, letter in ((0, -1, 'N'), (1, 0, 'E'), (0, 1, 'S'), (-1, 0, 'W')):
            color = '#f1bc72' if letter == 'N' else MUTED
            canvas.create_line(cx, cy, cx+dx*25, cy+dy*25, arrow=tk.LAST,
                               arrowshape=(6, 8, 3), fill=color, width=2, tags='overlay')
            text(cx+dx*37, cy+dy*37, letter, color)
        canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=TEXT, outline='', tags='overlay')

    def reset(self):
        terrain = self.coverage.terrain if self.coverage else (UNKNOWN,) * (GRID_SIZE * GRID_SIZE)
        self.forest = Forest(size=GRID_SIZE, terrain=terrain)
        self.reset_button.configure(state='normal' if self.coverage else 'disabled')
        self.screenshot_button.configure(state='normal' if self.coverage else 'disabled')
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
        if any(x0 <= event.x <= x1 and y0 <= event.y <= y1
               for x0, y0, x1, y1 in self.overlay_bounds):
            return
        ox, oy = self.offset
        col = int((event.x - ox) // self.cell_size)
        row = int((event.y - oy) // self.cell_size)
        if self.forest.ignite(row, col):
            self.has_ignited = True
            self.paint_map()
            self.update_stats()

    def update_stats(self):
        counts = self.forest.counts()
        affected = counts[FIRE] + counts[ASH]
        if self.coverage is None:
            self.burn_stats.set('Fire-affected area: — · Load a map to begin')
        else:
            area = affected * (self.coverage.side_km / self.forest.size) ** 2
            self.burn_stats.set(f'Fire-affected: {affected:,} cells · {area * 100:,.2f} ha ({area:.4f} km²)'
                                f'   |   Burning: {counts[FIRE]:,} · Ash: {counts[ASH]:,}')
        ratio = 100 * counts[ASH] / max(1, self.forest.initial_trees)
        self.stats.set(f'Forest cells   {counts[TREE]:,}\nBurning      {counts[FIRE]:,}'
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

    def save_screenshot(self):
        if self.coverage is None:
            return
        # Freeze the exported image before opening a native dialog; timers may
        # continue while the user chooses a destination.
        try:
            from screenshot import capture_map
            image = capture_map(self)
        except Exception as exc:
            messagebox.showerror('Screenshot failed', f'Could not create screenshot: {exc}', parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title='Save map screenshot',
                   defaultextension='.png', filetypes=[('PNG image', '*.png')],
                   initialfile=datetime.now().strftime('forest-fire-%Y%m%d-%H%M%S.png'))
        if not path:
            return
        try:
            image.save(path, format='PNG')
        except Exception as exc:
            messagebox.showerror('Screenshot failed', f'Could not save screenshot: {exc}', parent=self.root)
            return
        messagebox.showinfo('Screenshot saved', f'Saved to:\n{path}', parent=self.root)

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
