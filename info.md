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
- Track power & energy usage


## Install

Use hacs or copy the files to the custom_components folder in Home Assistant config.

Add the integration as usual, and follow the prompts. Each device can have the main sensor either in the floor or the room.

API details: https://www.ebeco.se/support/ebeco-open-api
