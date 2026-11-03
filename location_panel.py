"""Tk widgets stay on the main thread; daemon workers return via a queue."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from coverage_panel import CoveragePanel

from weather import WeatherError, fetch_weather, format_weather, locate_ip, search_cities


class LocationPanel(tk.Frame):
    def __init__(self, parent, auto_start=True, on_weather=None, on_coverage=None):
        super().__init__(parent, bg='#1b2b24')
        self.on_weather = on_weather or (lambda data: None)
        self.results = queue.Queue()
        self.generation = 0
        self.search_generation = 0
        self.location = None
        self.candidates = []
        self.query = tk.StringVar()
        self.place_text = tk.StringVar(value='No location selected')
        self.notice = tk.StringVar(value='Auto-locate or search for a city.')
        self.search_notice = tk.StringVar(value='Enter a city name, then click Search.')
        self.weather_text = tk.StringVar(value='No weather data')
        self._label('Location & Weather', font=('', 14, 'bold'))
        self.auto_button = ttk.Button(self, text='Auto-locate (IP)', command=self.auto_locate)
        self.auto_button.pack(fill='x', padx=14, pady=5)
        row = tk.Frame(self, bg=self['bg'])
        row.pack(fill='x', padx=14, pady=8)
        self.entry = ttk.Entry(row, textvariable=self.query, width=15)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', lambda event: self.search())
        self.search_button = ttk.Button(row, text='Search', command=self.search)
        self.search_button.pack(side='right', padx=(5, 0))
        self._label(variable=self.search_notice)
        self.city_list = tk.Listbox(self, height=4, exportselection=False,
                                   bg='#111d19', fg='#e4eee5', selectbackground='#467656')
        self.city_list.pack(fill='x', padx=14, pady=5)
        self.city_list.bind('<Double-Button-1>', lambda event: self.select_city())
        ttk.Button(self, text='Use Selected City', command=self.select_city).pack(fill='x', padx=14)
        self._label(variable=self.place_text, font=('', 11, 'bold'))
        self._label(variable=self.notice)
        self._label(variable=self.weather_text, font=('', 10))
        self.refresh_button = ttk.Button(self, text='Refresh Weather', command=self.refresh, state='disabled')
        self.refresh_button.pack(fill='x', padx=14, pady=8)
        self._label('IP location is approximate.\nWind spreads fire; rain/snow suppress it.\nData: ipapi / Open-Meteo\nCities: GeoNames via Open-Meteo')
        self.coverage_panel = CoveragePanel(self, on_coverage or (lambda result, error=None: None))
        self.coverage_panel.pack(fill='x', padx=14, pady=10)
        self.poll_id = self.after(80, self.poll)
        self.auto_id = self.after(200, self.auto_locate) if auto_start else None
        self.bind('<Destroy>', self.on_destroy, add='+')

    def _label(self, text=None, variable=None, **kwargs):
        tk.Label(self, text=text, textvariable=variable, bg=self['bg'], fg='#e4eee5',
                 anchor='w', justify='left', wraplength=275, **kwargs).pack(
                     fill='x', padx=14, pady=(8, 3))

    def on_destroy(self, event):
        if event.widget is self:
            self.after_cancel(self.poll_id)
            if self.auto_id:
                self.after_cancel(self.auto_id)

    def submit(self, kind, token, work):
        def worker():
            try:
                result, error = work(), None
            except WeatherError as exc:
                result, error = None, str(exc)
            except Exception:
                result, error = None, 'Request failed. Please try again later.'
            self.results.put((kind, token, result, error))
        threading.Thread(target=worker, daemon=True).start()

    def auto_locate(self):
        if self.auto_id:
            self.after_cancel(self.auto_id)
        self.auto_id = None
        self.on_weather(None)
        self.coverage_panel.set_location(None)
        self.generation += 1
        self.auto_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.weather_text.set('Waiting for location and weather…')
        self.notice.set('Locating… You can also search for a city.')
        self.submit('location', self.generation, locate_ip)

    def search(self):
        query = self.query.get().strip()
        if len(query) < 2:
            self.search_notice.set('Enter at least two characters.')
            return
        self.search_generation += 1
        self.search_button.configure(state='disabled')
        self.candidates = []
        self.city_list.delete(0, 'end')
        self.search_notice.set('Searching for cities…')
        self.submit('search', self.search_generation, lambda: search_cities(query))

    def select_city(self):
        selection = self.city_list.curselection()
        if not selection or not self.candidates:
            self.search_notice.set('Search for a city and select a result first.')
            return
        if self.auto_id:
            self.after_cancel(self.auto_id)
            self.auto_id = None
        # Manual selection invalidates outstanding automatic location/weather results.
        self.generation += 1
        self.set_location(self.candidates[selection[0]], 'Manual selection')

    def set_location(self, location, source):
        self.location = location
        self.coverage_panel.set_location(location)
        self.place_text.set(f'{location.name}\n{location.latitude:.4f}, {location.longitude:.4f} · {source}')
        self.auto_button.configure(state='normal')
        self.load_weather()

    def refresh(self):
        if self.location is not None:
            self.generation += 1
            self.load_weather()

    def load_weather(self):
        self.on_weather(None)
        location = self.location
        # Clear previous city's values before making a new request.
        self.weather_text.set('Fetching weather…')
        self.notice.set('Loading weather for the selected location.')
        self.refresh_button.configure(state='disabled')
        self.submit('weather', self.generation, lambda: fetch_weather(location))

    def poll(self):
        try:
            while True:
                kind, token, result, error = self.results.get_nowait()
                if kind == 'search':
                    if token != self.search_generation:
                        continue
                    self.search_button.configure(state='normal')
                    self.candidates = result or []
                    self.city_list.delete(0, 'end')
                    for location in self.candidates:
                        self.city_list.insert('end', f'{location.name} ({location.latitude:.2f}, {location.longitude:.2f})')
                    self.search_notice.set(error or ('Select a city, then click Use Selected City.' if result
                                                     else 'No cities found. Try another name or spelling.'))
                elif token == self.generation:
                    if error:
                        self.notice.set(error + (' You can search for a city manually.' if kind == 'location' else ' Click Refresh Weather to retry.'))
                        self.weather_text.set('No weather data')
                        self.on_weather(None)
                        self.auto_button.configure(state='normal')
                        self.refresh_button.configure(state='normal' if self.location else 'disabled')
                    elif kind == 'location':
                        self.set_location(result, 'IP location')
                    else:
                        self.weather_text.set(format_weather(result))
                        self.on_weather(result)
                        self.notice.set('Weather updated.')
                        self.refresh_button.configure(state='normal')
        except queue.Empty:
            pass
        self.poll_id = self.after(80, self.poll)
