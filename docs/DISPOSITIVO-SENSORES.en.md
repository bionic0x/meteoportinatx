# Phone sensors and haptics — experimental

**Language / Idioma:** [Español](DISPOSITIVO-SENSORES.md) · English

The `/dispositivo/` view uses the same `core.json` as the consoles and only works while the page is open and visible. It is not a warning service and does not change thresholds, models or sources. It has not been tested on real phones; compatibility and permissions depend on the device and browser. Sensors that require it need HTTPS or localhost.

Vibration is enabled with a button. Once a baseline is established, it signals an increase in level or loss of an earlier diagnosis (the latter no more than once a minute). The baseline resets when changing domain, hiding the page or showing it again. No vibration does not mean there is no danger; check official warnings.

The page checks cycle age (60 minutes in Portinatx, 360 in the Pyrenees) and shows “No diagnosis” when the cycle is old, invalid or missing. The cycle can contain older measurements. Portinatx uses the maximum available verified official warning, public observed channels and precaution if coverage is not insufficient; the Pyrenees uses the status of current warnings if the source is available. The summary is not an official warning and does not guarantee all sources are available.

## Readings

| Channel | Source | Expiry |
|---|---|---|
| Pressure, temperature, humidity | External native bridge | 5 minutes |
| Light, magnetic field, motion, heading | Browser APIs, if available and authorised | 15 seconds |
| Altitude | Geolocation, enabled separately | 2 minutes |

The page does not include a native app. An external wrapper could provide a reading through `MeteoDeviceBridge.push('presion', 1013.2, Date.now())`, which returns `{ok, reason}`. Values are validated and held in page memory. Sensor readings do not generate network requests; the page does request weather data. Geolocation is requested only when enabled and the code retains altitude only, not coordinates. The browser or geolocation provider may process data under its own policies.

A missing reading is `UNKNOWN`; an expired reading is shown as `STALE` with no value. Non-numeric, out-of-range, old, future or out-of-order readings are rejected; series memory is bounded. Pressure trend requires at least six readings, 30 minutes, gaps of no more than 20 minutes and a recent reading. An altitude variation greater than 25 m returns `NO_COMPARABLE`; without enough altitude data, vertical stability is `UNKNOWN`. This is guidance based on uncalibrated pressure and does not alter warnings or levels.

Vibration, sensors, compass and Wake Lock may be unavailable; test on real Android and iOS devices before claiming compatibility. Once sensors are stopped, retained readings expire normally.

## Verification

`node tests/test_device_sensors.cjs` verifies the pure validation, expiry, trend and haptics contracts with synthetic data. Integration tests check local routes and static output. They do not amount to a physical sensor test or guarantee that a phone will warn during an episode.
