# Ebeco thermostats for Home Assistant

[![GitHub release][releases-shield]][releases]
[![HACS default][hacs-shield]][hacs]
[![Tests][tests-shield]][tests]
[![Validate with hassfest][hassfest-shield]][hassfest]

Control your [Ebeco](https://www.ebeco.com/) wifi thermostats (EB-Therm 500 and others
that work with the Ebeco Connect app) from Home Assistant, through Ebeco's cloud API.

[Support the developer](https://paypal.me/jorgenbergstrom)

## What you get

One device per thermostat with these entities:

| Entity | What it shows |
| --- | --- |
| `climate` | Thermostat: current and target temperature, heat/off, presets *Manual*, *Home* (the week program) and *Timer* |
| `sensor … Floor Temperature` | Floor sensor, °C |
| `sensor … Room Temperature` | Room sensor, °C |
| `sensor … Relay` | Whether the heating relay is on |
| `sensor … Power` | Current power draw: installed effect when the relay is on, otherwise 0 W |
| `sensor … Installed Power` | Installed effect of the heating element, W |
| `sensor … Energy Usage` | Energy used today, kWh (minutes on today × installed effect) |

Programs and advanced settings are still made in the Ebeco app or on the thermostat itself.

## Install

1. Install the Ebeco Connect app, create an account and make sure you can control the
   thermostat from the app.
2. Install this integration with [HACS](https://hacs.xyz/) (search for *Ebeco*), or copy
   `custom_components/ebeco` into your Home Assistant `config/custom_components/` folder.
3. Restart Home Assistant.
4. Go to *Settings → Devices & services → Add integration* and pick **Ebeco**.
5. Log in with the same e-mail and password as in the Ebeco app, then choose the thermostat
   and which sensor (floor or room) the thermostat should show as its current temperature.

Repeat step 4–5 for each thermostat.

## How it works

The integration polls Ebeco's cloud once a minute per thermostat. Changes you make in
Home Assistant are sent to the cloud immediately and shown right away; the thermostat
itself picks them up within a minute or so.

If the cloud does not answer, the entities become `unavailable` and come back on the next
successful poll. The log then has one line that says why, for example
`Error fetching Ebeco data: TimeoutError` or `… HTTP 503 from https://ebecoconnect.com/…`.
That is Ebeco's cloud (or the way to it) not responding; the integration never talks to the
thermostat directly.

Ebeco limits the API to 10 requests per 10 seconds and 30 per minute per IP address. The
integration stays well within that, also when the cloud is flaky.

## Troubleshooting

To see exactly what the API returns for your thermostat, add this to `configuration.yaml`,
restart, and look for `Received data:` in the log (it contains no credentials):

```yaml
logger:
  logs:
    custom_components.ebeco: debug
```

Please include that line when you open an [issue](https://github.com/joggs/home_assistant_ebeco/issues).

## Development

The test suite runs without an Ebeco account and without a full Home Assistant install:

```bash
pip install -r requirements.test.txt
python -m pytest tests
```

It covers the API client against a fake server (errors, timeouts, rate limiting, logins)
and the integration in a Home Assistant test core with the API mocked (set-up, polling,
unavailable/recovery, climate services, sensors, config flow). GitHub Actions runs it on
every push and pull request, together with hassfest and the HACS validation.

Ebeco's API documentation: https://www.ebeco.se/support/ebeco-open-api

## License

[MIT](LICENSE)

[releases]: https://github.com/joggs/home_assistant_ebeco/releases
[releases-shield]: https://img.shields.io/github/v/release/joggs/home_assistant_ebeco
[hacs]: https://hacs.xyz/docs/default_repositories
[hacs-shield]: https://img.shields.io/badge/HACS-Default-41BDF5.svg
[tests]: https://github.com/joggs/home_assistant_ebeco/actions/workflows/tests.yml
[tests-shield]: https://github.com/joggs/home_assistant_ebeco/actions/workflows/tests.yml/badge.svg
[hassfest]: https://github.com/joggs/home_assistant_ebeco/actions/workflows/hassfest.yml
[hassfest-shield]: https://github.com/joggs/home_assistant_ebeco/actions/workflows/hassfest.yml/badge.svg
