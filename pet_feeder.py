"""
 PetFeeder Class
"""
import datetime
import os
import time
import math
import json
import logging
import requests
import schedule
from gpiozero import Button, Servo, DistanceSensor
from PIL import Image, ImageChops
from iothub_client import IoTHubClient, IoTHubMessageDispositionResult, IoTHubTransportProvider
from logging.handlers import RotatingFileHandler


class PetFeeder(object):
    """
    A class that allows automation for feeding pets and triggering
    a backend to re-order food
    """

    def __init__(self, token, options=None):
        """
        Constructor
        Args:
            token (string): Used for authentication to post data to the website
            options (json): Options that are used in the class. Use get_config()
                            to view view available options and their defaults
        """
        self.config = {
            "SERVO": None,
            "BUTTON": None,
            "DISTANCE_IN": None,
            "DISTANCE_OUT": None,
            "FULL_DISH_IMAGE": "/images/full.jpg",
            "COMPARE_DISH_IMAGE": "/images/compare.jpg",
            "LOG_FILES": "/logs/",
            "LOGGING_ENABLED": True,
            "FEED_DURATION": 5
        }
        if options != None:
            self.config.update(options)
        self.token = token
        self.url = "https://onlineservicehub.azurewebsites.net"
        # self.url = "http://192.168.1.5:8080"

        init_logger(self.config["LOG_FILES"], self.config["LOGGING_ENABLED"])

        self.button = None if self.config["BUTTON"] is None else Button(
            self.config["BUTTON"], hold_time=0)

        self.servo = None if self.config["SERVO"] is None else Servo(
            self.config["SERVO"], None)

        if self.config["DISTANCE_IN"] is None or self.config["DISTANCE_OUT"] is None:
            self.distance_sensor = None
        else:
            self.distance_sensor = DistanceSensor(self.config["DISTANCE_IN"],
                                                  self.config["DISTANCE_OUT"])

        self.client = None

    def get_config(self):
        """
        Gets the current configuration information
        """
        return self.config

    def path(self, folder):
        return os.path.dirname(__file__) + folder

    def init_logger(self, logs_directory, is_enabled):
        '''
        Initialize the logger with an output directory, if
        the directory doesn't exist it will be created
        Args:
            logs_directory (string): Directory where logs will be stored
            is_enabled (boolean): If the logger is enabled
        '''
        logs_directory = self.path(logs_directory)
        if not os.path.exists(logs_directory) and is_enabled:
            os.makedirs(logs_directory)

        logger = logging.getLogger()
        logger.disabled = not is_enabled
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s, %(name)s %(levelname)s %(message)s")

        # create console handler and set level to info
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # create error file handler and set level to error
        handler = logging.FileHandler(
            os.path.join(output_dir, "error.log"),
            "w",
            encoding=None,
            delay="true")
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # create debug file handler and set level to debug

        # handler = logging.FileHandler(os.path.join(output_dir, "all.log"), "w")
        # 5,242,880 bytes / 5.24288 mb
        handler = RotatingFileHandler(
            os.path.join(output_dir, "all.log"),
            maxBytes=(1048576 * 5),
            backupCount=7)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger

    def run_servo(self, interval=5):
        """
        Runs a servo for a specified amount of time
        Args:
            interval (number): Time the servo will run (default) = 5
        """
        if self.servo is None:
            return
        try:
            self.logger.info("Running for " + str(interval) + " seconds")
            self.servo.min()
            time.sleep(interval)

            self.logger.debug("done spinning")
        except Exception as ex:
            self.logger.error("Error running servo\n" + str(ex))
        self.servo.detach()
        self.update_server({
            "LastFillTimeUtc": str(datetime.datetime.utcnow()),
            "PercentHopperFull": str(self.update_hopper()),
            "PercentDishFull": str(self.check_dish())
        })

    def check_dish(self):
        """
        Check"s how full the dish is.
        Comparison is done by looking at config["FULL_DISH_IMAGE"]
        and config["COMPARE_DISH_IMAGE"]

        Returns:
            number: Percent of how full the dish is
        """

        self.logger.info("Checking dish")
        full_path = self.path(self.config["FULL_DISH_IMAGE"])
        compare_path = self.path(self.config["COMPARE_DISH_IMAGE"])
        if not os.path.exists(full_path):
            os.system("fswebcam --no-banner " + full_path)
        if os.path.exists(compare_path):
            os.remove(compare_path)
        # Take Photo
        os.system("fswebcam --no-banner " + compare_path)
        start_time = time.time()
        while (time.time() -
               start_time) <= 10 and not os.path.exists(compare_path):
            time.sleep(1)
        if (not os.path.exists(compare_path) or not os.path.exists(full_path)):
            return
        # Calculate the root-mean-square difference between two images
        im1 = Image.open(full_path)
        im2 = Image.open(compare_path)
        diff = ImageChops.difference(im1, im2)
        sqs = (value * (idx**2) for idx, value in enumerate(diff.histogram()))
        sum_of_squares = sum(sqs)
        rms = math.sqrt(sum_of_squares / float(im1.size[0] * im1.size[1]))
        amount = 0
        # Determine if bowl is full (100) or empty (0)
        if rms < 580:
            amount = 100
        elif rms < 610:
            amount = 75
        elif rms < 660:
            amount = 50
        elif rms < 680:
            amount = 25
        elif rms > 680:
            amount = 0

        self.logger.info("rms: {:f}, Amount: {:d}%".format(rms, amount))

        return amount

    def update_hopper(self):
        """
        Check the hoppers current percent full

        Returns:
            number: Percent of how full the hopper is
        """
        if self.distance_sensor is None:
            return
        self.logger.info("Distance Measurement In Progress")
        distance = self.distance_sensor.distance * 100
        full_oz = 112
        height = 20.0
        """
        full_oz      height
        -------  =  --------
           x        distance
        """

        amount = (full_oz * distance) / height
        # if distance > 20:
        #     amount = 0.0
        # elif distance > 18:
        #     amount = 3.0
        # elif distance > 16.24:
        #     amount = 3.9
        # elif distance > 14.55:
        #     amount = 5.0
        # elif distance > 12.87:
        #     amount = 6.1
        # elif distance > 11.23:
        #     amount = 7.2
        # elif distance > 9.66:
        #     amount = 8.3
        # elif distance > 8.09:
        #     amount = 9.4
        # elif distance > 7.39:
        #     amount = 10.6
        # elif distance > 5.84:
        #     amount = 11.7
        # elif distance > 4.7:
        #     amount = 12.8
        # elif distance > 3.9:
        #     amount = 13.9
        # elif distance > 2.81:
        #     amount = 15.0

        self.logger.info(
            "Distance: {:f}cm, Amount: {:f}oz".format(distance, amount))
        return amount

    def update_server(self, data, image=None):
        """
        Sends an update to the server

        Args:
            data (object): Arguments that will be passed to the server
            image (file): Image of the dish that will be uploaded
        """
        try:
            if self.token is None:
                return
            self.logger.info("Updating web site")
            headers = {"Authorization": "Bearer " + self.token}
            self.logger.info(data)

            response = requests.post(
                self.url + "/api/PetFeeder",
                json=data,
                files=image,
                headers=headers)
            self.logger.info("Posted status: {:d}, Info: {:s}".format(
                response.status_code, response.content))
        except Exception as ex:
            self.logger.error("Error posting data\n" + str(ex))

    def receive_message_callback(self, message, counter):
        """
        Callback from IOT Hub event trigger

        Args:
            message (object): JSON string containing command instructions
            counter (number): Counter from init method
        """
        message_buffer = message.get_bytearray()
        size = len(message_buffer)
        message_data = message_buffer[:size].decode('utf-8')
        if len(message_data) > 0:
            data = json.loads(message_data)
            command = data["command"].lower().strip()

            self.logger.info("Feeder command received" + command)
            if command == "feed":
                self.run_servo(self.config["FEED_DURATION"])
                # self.run_servo(self.config["FEED_DURATION"])
            elif command == "image":
                self.check_dish(),
                self.update_server(None, {
                    "FeederImage":
                    open(self.config["COMPARE_DISH_IMAGE"], "rb")
                })
        self.logger.info("Sending response to IOT")
        return IoTHubMessageDispositionResult.ACCEPTED

    def init_listener(self, device_id, device_key):
        """
        Initiates a connection to receive messages from the web site
        Args:
            device_id (string): Device Id that was created via the web site sign up
            device_key (string): Device Key that was created via the web site sign up
        """
        connection_root = "HostName=OnlineServiceHub.azure-devices.net;DeviceId={:s};SharedAccessKey={:s}"
        receive_context = 0

        self.client = IoTHubClient(
            connection_root.format(device_id, device_key),
            IoTHubTransportProvider.MQTT)
        self.client.set_option("messageTimeout", 10000)
        self.client.set_option("logtrace", 0)
        self.client.set_message_callback(self.receive_message_callback,
                                         receive_context)

    def init_schedule(self, times_to_feed=None):
        """
        Initiates a the schedule that the feeder will automatically feed

        Args:
            times_to_feed (string[]): the times that the feeder will call
                run_servo() automatically (default) = ["08:00","20:00"]
        """
        feed_duration = self.config["FEED_DURATION"]
        if times_to_feed is None:
            times_to_feed = ["08:00", "20:00"]
        for run_time in times_to_feed:
            schedule.every().day.at(run_time).do(self.run_servo,
                                                 self.config["FEED_DURATION"])
        schedule.every(1).hour.do(self.update_server,
                                  {"PercentDishFull": self.check_dish()})

    def run_events(self):
        """
        Check if anything is happening such as button presses, schedules, etc.
        and run those features
        """
        if self.button is not None and self.button.is_pressed:
            self.logger.debug("Button click " +
                              time.asctime(time.localtime(time.time())))
            self.run_servo(self.config["FEED_DURATION"])
        # added a timeout so that we can ctrl+c to quit
        schedule.run_pending()

    def loop_forever(self):
        """
        Will keep the application running indefinately and call run_events()
        """
        self.logger.info("Starting application")
        while True:
            try:
                self.run_events()
            except Exception as ex:
                self.logger.error(str(ex))
            finally:
                time.sleep(.5)


# while True:
#     FEEDER.update_hopper()
#     time.sleep(2)
#     print("test")
