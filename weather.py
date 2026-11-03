"""Network adapters using only the Python standard library."""
import json
import math
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WeatherError(Exception):
    pass


def request_json(url):
    try:
        request = Request(url, headers={'User-Agent': 'ForestFire/1.0', 'Accept': 'application/json'})
        with urlopen(request, timeout=10) as response:
            data = json.load(response)
    except HTTPError as error:
        message = 'Too many requests. Please try again later.' if error.code == 429 else f'Service unavailable (HTTP {error.code})'
        raise WeatherError(message) from error
    except (URLError, OSError) as error:
        raise WeatherError('Connection failed or timed out. Check your network and retry.') from error
    except (ValueError, UnicodeError) as error:
        raise WeatherError('The service returned unreadable data.') from error
    if not isinstance(data, dict):
        raise WeatherError('Unexpected response format.')
    if data.get('error'):
        raise WeatherError('The service could not complete the request. Please retry later.')
    return data


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float


def location_from(data, ip=False):
    try:
        lat, lon = float(data['latitude']), float(data['longitude'])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError()
        fields = ('city', 'region', 'country_name') if ip else ('name', 'admin1', 'country')
        name = ' · '.join(dict.fromkeys(str(data[k]) for k in fields if data.get(k)))
        return Location(name or 'Unknown location', lat, lon)
    except (KeyError, TypeError, ValueError) as error:
        raise WeatherError('The location service did not return valid coordinates.') from error


def locate_ip():
    return location_from(request_json('https://ipapi.co/json/'), ip=True)


def search_cities(query):
    params = urlencode({'name': query.strip(), 'count': 10, 'language': 'en'})
    data = request_json('https://geocoding-api.open-meteo.com/v1/search?' + params)
    results = data.get('results', [])
    if not isinstance(results, list):
        raise WeatherError('Unexpected city search response.')
    locations = []
    for item in results:
        try:
            locations.append(location_from(item))
        except WeatherError:
            continue
    return locations


def fetch_weather(location):
    fields = ('temperature_2m', 'relative_humidity_2m', 'wind_speed_10m',
              'wind_direction_10m', 'precipitation', 'rain', 'showers', 'snowfall')
    params = urlencode({'latitude': location.latitude, 'longitude': location.longitude,
                        'current': ','.join(fields), 'wind_speed_unit': 'ms', 'timezone': 'auto'})
    data = request_json('https://api.open-meteo.com/v1/forecast?' + params)
    current = data.get('current')
    if not isinstance(current, dict) or not current.get('time'):
        raise WeatherError('Current weather was not returned by the service.')
    result = {'time': current['time'], 'timezone': data.get('timezone', ''),
              'interval': current.get('interval')}
    for field in fields:
        value = current.get(field)
        result[field] = value if isinstance(value, (int, float)) and math.isfinite(value) else None
    return result


def precipitation_rate(data):
    """Normalize the API accumulation interval; never double-count total + snow."""
    interval = data.get('interval')
    if not isinstance(interval, (int, float)) or not math.isfinite(interval) or interval <= 0:
        return None
    total = data.get('precipitation')
    if total is None:
        rain, showers, snow = (data.get(k) for k in ('rain', 'showers', 'snowfall'))
        if all(value is None for value in (rain, showers, snow)):
            return None
        # API snowfall is cm: 0.7 cm snow is approximately 1 mm water equivalent.
        total = max(0, rain or 0) + max(0, showers or 0) + max(0, snow or 0) / 0.7
    return max(0, total) * 3600 / interval


def simulation_weather(data):
    data = data or {}
    return {'wind_speed': data.get('wind_speed_10m') or 0,
            'wind_direction': data.get('wind_direction_10m'),
            'precipitation_rate': precipitation_rate(data) or 0}


def format_weather(data):
    def value(key, unit):
        number = data.get(key)
        return 'N/A' if number is None else f'{number:g} {unit}'
    direction = data.get('wind_direction_10m')
    wind = 'N/A' if direction is None else (
        ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')[int((direction + 22.5) // 45) % 8]
        + f' wind (from {direction:g}°)')
    rate = precipitation_rate(data)
    intensity = 'N/A' if rate is None else f'{rate:g} mm/h'
    interval = data.get('interval')
    period = f'{interval / 60:g} min' if isinstance(interval, (int, float)) and interval > 0 else 'unknown interval'
    return (f"Temperature   {value('temperature_2m', '°C')}\n"
            f"Humidity   {value('relative_humidity_2m', '%')}\n"
            f"Wind speed   {value('wind_speed_10m', 'm/s')}\n"
            f"Wind direction   {wind}\n"
            f"Precipitation rate   {intensity}\n"
            f"Rain {value('rain', 'mm')} / Showers {value('showers', 'mm')}\n"
            f"Snow {value('snowfall', 'cm')} (past {period})\n"
            f"Weather time: {data['time'].replace('T', ' ')}\n{data['timezone']}")
