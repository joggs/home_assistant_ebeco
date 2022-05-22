# Ebeco thermostats
![Validate with hassfest](https://github.com/joggs/home_assistant_ebeco/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge][hacs-shield]][hacs]

Control your [Ebeco](https://www.ebeco.com/) thermostats from Home Assistant.

[Support the developer](http://paypal.me/jorgenbergstrom)

## Functionality

This component will give you the following:
* Room temperature
* Floor temperature
* A Home Assistant thermostat for setting the temperature
* Current power (W)
* Energy used last 24 hours (kWh)

To make advanced settings, you need to use Ebeco app or use the physical thermostat

## Install
1. Download the Ebeco app and create an account.
2. Make sure you can manage the thermostat via the Ebeco app
3. Install this Ebeco component via [HACS](https://hacs.xyz/) or copy the files to the custom_components folder in Home Assistant config.
4. Restart Home Assistant and add this integration
5. Login with the same user/pass as you've used for the Ebeco app
6. Enjoy!

## Ebeco's API
Ebeco's API details: https://www.ebeco.se/support/ebeco-open-api

[releases]: https://github.com/joggs/home_assistant_ebeco/releases
[releases-shield]: https://img.shields.io/github/release/joggs/home_assistant_ebeco.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/joggs/home_assistant_ebeco/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories
