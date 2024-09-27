"""
HomeAssistant MQTT components. See https://www.home-assistant.io/integrations/mqtt#discovery-topic.
"""
from .base import *
from . import sensor
Sensor = sensor.Sensor
