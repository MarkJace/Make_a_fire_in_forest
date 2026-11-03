import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from weather import (Location, WeatherError, fetch_weather, format_weather,
                     location_from, request_json, search_cities)


class WeatherTests(unittest.TestCase):
    def test_bad_coordinates(self):
        for lat in (None, 'NaN', 91):
            with self.assertRaises(WeatherError):
                location_from({'latitude': lat, 'longitude': 20})

    @patch('weather.request_json')
    def test_empty_and_multiple_search_results(self, request):
        request.return_value = {}
        self.assertEqual(search_cities('Beijing'), [])
        request.return_value = {'results': [
            {'name': 'Paris', 'country': 'France', 'latitude': 48, 'longitude': 2},
            {'name': 'Paris', 'country': 'USA', 'latitude': 33, 'longitude': -95}]}
        result = search_cities('Paris')
        self.assertEqual(len(result), 2)
        self.assertNotEqual(result[0].name, result[1].name)

    @patch('weather.request_json')
    def test_weather_null_fields_and_units(self, request):
        request.return_value = {'current': {'time': '2026-11-03T12:00',
            'temperature_2m': None, 'wind_direction_10m': 0}, 'timezone': 'Asia/Shanghai'}
        result = fetch_weather(Location('Beijing', 39.9, 116.4))
        self.assertIn('wind_speed_unit=ms', request.call_args.args[0])
        self.assertIn('N/A', format_weather(result))
        self.assertIn('N wind', format_weather(result))
        request.return_value = {}
        with self.assertRaises(WeatherError):
            fetch_weather(Location('Beijing', 39.9, 116.4))

    @patch('weather.urlopen')
    def test_network_errors(self, open_url):
        for error in (URLError('offline'), HTTPError('url', 429, '', {}, None)):
            open_url.side_effect = error
            with self.assertRaises(WeatherError):
                request_json('https://example.com')


if __name__ == '__main__':
    unittest.main()
