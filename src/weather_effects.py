"""Lightweight decorative precipitation, independent of the fire simulation."""
import math
import random
import time


def precipitation_components(data):
    """Return rain mm/h and snow cm/h using the API accumulation interval."""
    data = data or {}
    def positive(value):
        return max(0.0, value) if isinstance(value, (int, float)) and math.isfinite(value) else 0.0
    interval = positive(data.get('interval'))
    if not interval:
        return 0.0, 0.0
    snow = positive(data.get('snowfall'))
    rain = positive(data.get('rain')) + positive(data.get('showers'))
    if data.get('rain') is None and data.get('showers') is None:
        rain = max(0.0, positive(data.get('precipitation')) - snow / 0.7)
    return min(100.0, rain * 3600 / interval), min(70.0, snow * 3600 / interval)


class WeatherEffects:
    def __init__(self, canvas):
        self.canvas = canvas
        self.random = random.Random()  # Never consume the simulation's random stream.
        self.quality = 'Full'
        self.rates = (0.0, 0.0)
        self.drift = 0.0
        self.bounds = None
        self.particles = []
        self.last_time = time.monotonic()
        self.timer = None
        canvas.bind('<Destroy>', self.close, add='+')
        self.animate()

    def close(self, event):
        if event.widget is self.canvas and self.timer is not None:
            self.canvas.after_cancel(self.timer)
            self.timer = None

    def set_quality(self, quality):
        if quality not in ('Off', 'Light', 'Full'):
            raise ValueError('Unknown weather effect quality')
        self.quality = quality
        self.rebuild()

    def set_weather(self, data):
        self.rates = precipitation_components(data)
        data = data or {}
        speed, direction = data.get('wind_speed_10m'), data.get('wind_direction_10m')
        self.drift = 0.0
        if all(isinstance(v, (int, float)) and math.isfinite(v) for v in (speed, direction)):
            self.drift = -math.sin(math.radians(direction)) * min(60, max(0, speed)) * 3
        self.rebuild()

    def set_bounds(self, bounds):
        # Called after map redraw, which also deletes the old canvas items.
        self.bounds = bounds
        self.rebuild()

    def rebuild(self):
        self.canvas.delete('precipitation')
        self.particles.clear()
        if self.bounds is None or self.quality == 'Off':
            return
        _, _, side = self.bounds
        if side < 10:
            return
        area = min(2.0, (side / 600) ** 2)
        for kind, rate in zip(('rain', 'snow'), self.rates):
            if rate <= 0:
                continue
            # Snow is normalized to liquid equivalent for comparable visual density.
            intensity = min(1.0, math.log1p(rate if kind == 'rain' else rate / 0.7) / math.log(21))
            count = max(4, min(260, round((12 + 180 * intensity) * area)))
            if self.quality == 'Light':
                count = max(1, count // 4)
            for _ in range(count):
                if kind == 'rain':
                    item = self.canvas.create_line(0, 0, 0, 0, fill='#9bc5de',
                                                   width=1 if intensity < .6 else 2, tags='precipitation')
                else:
                    item = self.canvas.create_oval(0, 0, 0, 0, fill='#edf5fa', outline='', tags='precipitation')
                self.particles.append(dict(item=item, kind=kind, x=self.random.random()*side,
                                           y=self.random.random()*side, phase=self.random.random()*math.tau,
                                           scale=self.random.uniform(.7, 1.3), intensity=intensity))
        self.draw(0)
        self.canvas.tag_raise('overlay')

    def draw(self, dt):
        if self.bounds is None:
            return
        ox, oy, side = self.bounds
        for p in self.particles:
            rain = p['kind'] == 'rain'
            strength = p['intensity']
            speed = ((190 + 260*strength) if rain else (22 + 40*strength)) * p['scale']
            p['phase'] += dt * 1.7
            drift = self.drift + (0 if rain else math.sin(p['phase'])*16)
            p['x'] = (p['x'] + drift*dt) % side
            p['y'] = (p['y'] + speed*dt) % side
            x, y = p['x'], p['y']
            if rain:
                length = 7 + 13*strength
                x2 = max(0, min(side, x + drift/speed*length))
                y2 = min(side, y+length)
                coords = (ox+x, oy+y, ox+x2, oy+y2)
            else:
                radius = (1.2 + 1.5*strength)*p['scale']
                coords = (ox+max(0, x-radius), oy+max(0, y-radius),
                          ox+min(side, x+radius), oy+min(side, y+radius))
            self.canvas.coords(p['item'], *coords)

    def animate(self):
        now = time.monotonic()
        self.draw(min(.1, now-self.last_time))
        self.last_time = now
        self.timer = self.canvas.after(250 if self.quality == 'Off' else (66 if self.quality == 'Light' else 33), self.animate)
