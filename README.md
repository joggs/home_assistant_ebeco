# Ebeco thermostats
![Validate with hassfest](https://github.com/joggs/home_assistant_ebeco/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge][hacs-shield]][hacs]

Custom component for using [Ebeco](https://www.ebeco.com/) thermostats in Home Assistant.

[Support the developer](http://paypal.me/jorgenbergstrom)


## Install
Use [hacs](https://hacs.xyz/) or copy the files to the custom_components folder in Home Assistant config.

In configuration.yaml:

```
climate:
  - platform: ebeco
    username: "xxxx"  # replace with your Ebeco connect username or email address. Required
    password: "yyyy"  # replace with your Ebeco connect password. Required
    main_sensor: "zzzz" # floor or room. Optional. Default: floor
```

API details: https://www.ebeco.se/support/ebeco-open-api


[releases]: https://github.com/joggs/home_assistant_ebeco/releases
[releases-shield]: https://img.shields.io/github/release/joggs/home_assistant_ebeco.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/joggs/home_assistant_ebeco/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories
