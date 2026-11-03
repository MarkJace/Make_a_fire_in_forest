"""Independent background land-cover requests with stale-result protection."""
import queue
import threading
import tkinter as tk
from tkinter import ttk
from landcover import LandCoverError, fetch_coverage
from map_config import GRID_SIZE, MAP_SIZES_KM, DEFAULT_SIDE_KM
from forest import TREE, WATER, CITY, EMPTY

class CoveragePanel(tk.Frame):
    def __init__(self, parent, on_result):
        super().__init__(parent, bg='#1b2b24')
        self.on_result = on_result
        self.location = None
        self.side_km = DEFAULT_SIDE_KM
        self.area_text = tk.StringVar()
        self.update_area_text()
        self.generation = 0
        self.results = queue.Queue()
        self.workers = threading.BoundedSemaphore(2)
        self.message = tk.StringVar(value='Select a location to load its terrain map.')
        tk.Label(self, text='Local Terrain Map', bg=self['bg'], fg='#e4eee5',
                 font=('', 12, 'bold')).pack(anchor='w', pady=(10, 4))
        tk.Label(self, textvariable=self.message, bg=self['bg'], fg='#e4eee5',
                 wraplength=270, justify='left', anchor='w').pack(fill='x')
        self.retry = ttk.Button(self, text='Reload Terrain Map', command=self.load, state='disabled')
        self.retry.pack(fill='x', pady=8)
        tk.Label(self, textvariable=self.area_text, bg=self['bg'], fg='#a5bcad',
                 justify='left', wraplength=270).pack(fill='x')
        self.poll_id = self.after(100, self.poll)
        self.bind('<Destroy>', self.on_destroy, add='+')

    def on_destroy(self, event):
        if event.widget is self:
            self.after_cancel(self.poll_id)
            self.generation += 1

    def update_area_text(self):
        self.area_text.set(f'ESA WorldCover 2021 v200 · 10 m\n'
                           f'Area: {self.side_km} × {self.side_km} km\n'
                           f'{GRID_SIZE} × {GRID_SIZE} cells · {self.side_km*1000/GRID_SIZE:g} m/cell\n'
                           'Forest / ground / water / city')

    def set_extent(self, side_km):
        if side_km not in MAP_SIZES_KM:
            raise ValueError('Unsupported map extent')
        if self.side_km != side_km:
            self.side_km = side_km
            self.update_area_text()
            self.load()

    def set_location(self, location):
        self.location = location
        self.load()

    def load(self):
        self.generation += 1
        self.on_result(None)
        location, token, side_km = self.location, self.generation, self.side_km
        if location is None:
            self.message.set('Waiting for a location. The map is unavailable until real data loads.')
            self.retry.configure(state='disabled')
            return
        self.retry.configure(state='disabled')
        self.message.set('Loading satellite land cover…\nThe map will appear when loading completes.')
        def worker():
            with self.workers:
                if token != self.generation:
                    return
                try:
                    result, error = fetch_coverage(location.latitude, location.longitude, side_km), None
                except LandCoverError as exc:
                    result, error = None, str(exc)
                except Exception:
                    result, error = None, 'Land-cover request failed. Please retry.'
                self.results.put((token, result, error))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                token, result, error = self.results.get_nowait()
                if token != self.generation:
                    continue
                self.retry.configure(state='normal' if self.location else 'disabled')
                if error:
                    self.message.set(error)
                    self.on_result(None, error)
                else:
                    counts = {kind: result.terrain.count(kind) for kind in (TREE, EMPTY, WATER, CITY)}
                    total = len(result.terrain)
                    self.message.set(f"Forest {counts[TREE]/total:.1%} · ground {counts[EMPTY]/total:.1%}\n"
                                     f"Water {counts[WATER]/total:.1%} · city {counts[CITY]/total:.1%}\n"
                                     'Map loaded. Only forest cells can burn.')
                    self.on_result(result)
        except queue.Empty:
            pass
        self.poll_id = self.after(100, self.poll)
