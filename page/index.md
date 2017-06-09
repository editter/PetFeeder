---
layout: default
title: Pet Feeder
permalink: /
---


<!--# PetFeeder-->

A simple python class that controls a petfeeder.
Features include:
* Running on a schedule
* Running via a button press
* Re-ordering food from Amazon Dash Service
* Interactions with an Amazon Alexa app
* Website interface to view the status of the feeder

See the full writeup at [Hackster.io](https://www.hackster.io/editter/smart-pet-feeder-b226d8)

If you want to use Alexa app or view data via the web site sign up here <https://onlineservicehub.azurewebsites.net/> *(beta)*

<https://github.com/editter/PetFeeder/>

```
TOKEN = "<Token>"
DEVICE_ID = "<Device-Id>"
DEVICE_KEY = "<Device-Key>"
FEEDER = PetFeeder(TOKEN,
           {"SERVO": 18,
            "BUTTON": 19,
            "DISTANCE_IN": 23,
            "DISTANCE_OUT": 24})

FEEDER.init_schedule()
FEEDER.init_listener(DEVICE_ID, DEVICE_KEY)
FEEDER.loop_forever()
```

## API


### \_\_init__
Default constructor
* **token** - `string`
Used for authentication to post data to the website
* **options** - `json` [Default: `None`]
Options that are used in the class. Use get_config() to view view available options and their defaults
  * **options**.SERVO `number` - Pin for connecting to a servo
  * **options**.BUTTON `number` - Pin for connecting to a button
  * **options**.DISTANCE_IN `number` - Pin for connecting to a distance sensor (in)
  * **options**.DISTANCE_IN `number` - Pin for connecting to a distance sensor (out)
  * **options**.FULL_DISH_IMAGE `string` - Location of the file that will be used as a comparison for a full dish
  * **options**.COMPARE_DISH_IMAGE `string` - Location of the file that will be taken when CHECK_DISH is run
  * **options**.LOG_FILES `string` - Location where log files will be stored reletave to running directory
  * **options**.LOGGING_ENABLED `boolean` - Allows logging to be enabled/disabled
  * **options**.FEED_DURATION `number` - The number of seconds that a servo will run when feeding occurs


### get_config
Gets the current configuration information


### path

* **folder** - `string`
Folder relative to running directory


### run_servo
Runs a servo for a specified amount of time

* **interval** - `number` [Default: `5`]
Time the servo will run (default) = 5


### check_dish
Check"s how full the dish is. Comparison is done by looking at config["FULL_DISH_IMAGE"] and config["COMPARE_DISH_IMAGE"]

Returns - `number`
Percent of how full the dish is


### update_hopper
Check the hoppers current percent full

Returns - `number`
Percent of how full the hopper is


### update_server
Sends an update to the server

* **data** - `json`
Arguments that will be passed to the server

* **image** - `file` [Default: `None`]
Image of the dish that will be uploaded


### receive_message_callback
Callback from IOT Hub event trigger

* **message** - `object`
JSON string containing command instructions

* **counter** - `number`
Time the servo will run (default) = 5


### init_listener
Initiates a connection to receive messages from the web site

* **device_id** - `string`
Device Id that was created via the web site sign up

* **device_key** - `string`
Device Key that was created via the web site sign up


### init_schedule
Initiates a the schedule that the feeder will automatically feed

* **times_to_feed** - `array<string>` [Default: `["08:00", "20:00"]`]
The times that the feeder will call run_servo()


### run_events
Check if anything is happening such as button presses, schedules, etc. and run those features


### loop_forever
Will keep the application running indefinately and call run_events()
