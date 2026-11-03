import unittest
from forest import Forest, FIRE, ASH
from weather import precipitation_rate, simulation_weather


class EffectsTests(unittest.TestCase):
    def test_wind_spreads_faster_and_downwind(self):
        f = Forest(size=5, density=1)
        f.random.random = lambda: 0.3
        f.ignite(2, 2)
        f.step()
        self.assertEqual(f.cells.count(FIRE), 1)
        f.set_weather(wind_speed=10, wind_direction=0)
        f.step()
        self.assertGreater(f.cells.count(FIRE), 1)
        self.assertEqual(f.cells[3 * 5 + 2], FIRE)  # North wind blows south.
        for angle, down, up in [(0, (1, 0), (-1, 0)), (90, (0, -1), (0, 1)),
                                (180, (-1, 0), (1, 0)), (270, (0, 1), (0, -1))]:
            f.set_weather(wind_speed=10, wind_direction=angle)
            self.assertGreater(f.spread_probability(*down), f.spread_probability(*up))

    def test_more_precipitation_means_shorter_fire_and_less_spread(self):
        durations, probabilities = [], []
        for rate in (0, 1, 4, 10):
            f = Forest(size=1, density=1)
            f.set_weather(precipitation_rate=rate)
            probabilities.append(f.spread_probability(1, 0))
            f.ignite(0, 0)
            while FIRE in f.cells:
                f.step()
            durations.append(f.steps)
        self.assertEqual(durations, sorted(durations, reverse=True))
        self.assertEqual(len(set(durations)), 4)
        self.assertEqual(probabilities, sorted(probabilities, reverse=True))

    def test_extinguished_fire_does_not_spread_even_in_wind(self):
        f = Forest(size=3, density=1)
        f.set_weather(wind_speed=50, precipitation_rate=20)
        f.random.random = lambda: 0
        f.ignite(1, 1)
        f.step()
        self.assertNotIn(FIRE, f.cells)
        self.assertEqual(f.cells.count(ASH), 1)

    def test_interval_snow_conversion_and_no_double_counting(self):
        self.assertEqual(precipitation_rate({'interval': 900, 'precipitation': 1, 'snowfall': 0.7}), 4)
        self.assertEqual(precipitation_rate({'interval': 3600, 'snowfall': 0.7}), 1)
        self.assertEqual(precipitation_rate({'interval': 900, 'rain': 1, 'showers': 1}), 8)
        self.assertIsNone(precipitation_rate({'interval': 0, 'precipitation': 1}))
        self.assertIsNone(precipitation_rate({'interval': 900}))
        for key, quantity in [('rain', 1), ('snowfall', 0.7)]:
            f = Forest(size=1, density=1)
            f.set_weather(**simulation_weather({'interval': 3600, key: quantity}))
            f.ignite(0, 0)
            for _ in range(5):
                f.step()
            self.assertNotIn(FIRE, f.cells)

    def test_weather_can_change_during_fire_and_clear(self):
        f = Forest(size=1, density=1)
        f.ignite(0, 0)
        f.step()
        f.set_weather(precipitation_rate=4)
        f.step()
        self.assertLess(f.ages[0], 5)
        f.set_weather(**simulation_weather(None))
        self.assertAlmostEqual(f.spread_probability(1, 0), 0.22)
        self.assertEqual(f.precipitation_rate, 0)


if __name__ == '__main__':
    unittest.main()
