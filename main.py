'''
Main entry point for PetFeeder
'''
from pet_feeder import PetFeeder

TOKEN = "<Token>"
DEVICE_ID = "<Device-Id>"
DEVICE_KEY = "<Device-Key>"
OPTIONS = {
    "SERVO": 18,
    "BUTTON": 19,
    "DISTANCE_IN": 23,
    "DISTANCE_OUT": 24
    }
FEEDER = PetFeeder(TOKEN, OPTIONS)

FEEDER.init_schedule()
FEEDER.init_listener(DEVICE_ID, DEVICE_KEY)
FEEDER.loop_forever()
