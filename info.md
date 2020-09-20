Async integration for ebeco thermostats

[Buy me a coffee :)](paypal.me/jorgenbergstrom)


{%- if selected_tag == "master" %}
## This is a development version!
This is **only** intended for test by developers!
{% endif %}

{%- if prerelease %}
## This is a beta version
Please be careful and do NOT install this on production systems. Also make sure to take a backup/snapshot before installing.
{% endif %}

# Features
- Support for Ebeco thermostats
- See temperature and set temperature
- Change set temperature and turn on/off


## Install
In configuration.yaml:

```
climate:
  - platform: ebeco
    username: "xxxx"  # replace with your Ebeco connect username or email address. Required
    password: "yyyy"  # replace with your Ebeco connect password. Required
    main_sensor: "zzzz" # floor or room. Optional. Default: floor
```
