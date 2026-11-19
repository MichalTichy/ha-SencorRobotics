# Home assistant Sencor vacuum integration

The purpose of this integration is to provide an integration of Sencor vacuum.
It allow home assistant to:
- start cleaning
- pause cleaning
- go to dock
- retrieve vacuum informations (battery, state)
- clean specific rooms
- set volume
- locate robot
- clean specific rooms

![screenshot](./doc/screen.png)

This integration was tested on Sencor SRV 9200BK.
It should work on many other models (and brand) of vacuums developed by  [Clouds Robot Co.Ltd](https://play.google.com/store/apps/developer?id=Clouds+Robot++Co.Ltd) (Sencor, Cleanmate, Proscenic, ...)


## Installation

### HACS installation

You can use [HACS](https://hacs.xyz/) to install this component. Search for the Integration "Sencor Vacuum"

### Manual installation

1. Go to [releases page](https://github.com/MichalTichy/ha-SencorRobotics/releases)
2. download the last release zip
3. unzip it on `custom_components` directory
4. see next chapter for configuration

## Configuration

Add your device via the Integration menu.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sencor)


### Get authentifications data

device id, token, user id and authentication code can be retrieved using the SENCOR robotic application :
1. On your android smartphone (no solution for iphone), install [Packet capture](https://play.google.com/store/apps/details?id=app.greyshirts.sslcapture)
2. Open Packet capture and start a capture ![screenshot](./doc/packet_capture_button.png) select SENCOR  Robotic app
3. Open the SENCOR application, and open the vacuum view
4. Reopen  Packet capture
    1. Click on the first line
    2. Click on the line with local IP ![screenshot](./doc/flowSelection.jpg)
    3. Get you informations ![screenshot](./doc/packet_with_info.jpg)
5. You can now enter your informations on home assistant
6. You can add your vacuum on lovelace ui entities
    1. You can simply add it as an entity
    2. You can use the [vacuum-card](https://github.com/denysdovhan/vacuum-card)


## Available attributes

Theses attributes are available to be displayed on lovelace-ui:
- `battery_level`: current battery level
- `fan_speed`: last used fan speed
- `charger_position`: possition of charger
- `robot_position`: possition of robot
- `rooms`: List of known rooms

## Available additional services
- sencor.clean_rooms
    - Sends vacuum to clean selected room/s.
    ```
    service: sencor.clean_rooms
    data:
        rooms:
            - room_id: 4
            clean_num: 1
    target:
        entity_id: vacuum.vacuum
    ```


This integration is heavily based on [Cleanmate integration by Albinmedoc](https://github.com/albinmedoc/ha-cleanmate) and [Proscenic 790T integration by Deblockt](https://github.com/deblockt/hass-proscenic-790T-vacuum)
## Compatibility and troubleshooting

This version requires Home Assistant 2025.1 or newer. It uses the
`VacuumActivity` API introduced in that release and preserves `battery_level`
as a vacuum attribute for existing cards and automations.

After updating the integration, restart Home Assistant and try the
`vacuum.start` action in Developer Tools > Actions. Existing configuration
entries do not need to be recreated.

If state updates work but cleaning does not start:

1. Check whether cleaning starts in the SENCOR Robotics app.
2. Check the Home Assistant log for the error from `vacuum.start`.
   The HA host must be able to connect to the robot on TCP port 8888.
3. Report the robot model, firmware version, Home Assistant version, integration
   version, and whether pause / return to dock work. If the robot IP or app
   credentials changed, check the configured IP, device ID and authentication
   code against a fresh capture from the app.
4. For protocol investigation, enable debug logging for `custom_components.sencor`
   in the Home Assistant logger configuration, reproduce one failed start, and
   attach the relevant log excerpt to an issue. Do not publish authentication
   codes or unredacted packet captures.

The transport fixes are covered by a simulated TCP robot. A successful TCP write
alone does not confirm that a real robot accepted a command; hardware validation
is still required, particularly if firmware changed the command protocol.

## Development tests

Protocol tests use only the Python standard library (Python 3.11 or newer):

```sh
python -W error -m unittest discover -s tests -v
```

CI also runs entity contract tests against Home Assistant 2025.1 and the latest
available release. These checks are skipped when Home Assistant is not installed.
