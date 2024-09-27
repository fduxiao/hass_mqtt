"""
Sensor Components. See https://www.home-assistant.io/integrations/sensor.mqtt/
"""
from .base import Base, MQTTClient, Field


class Sensor(Base):
    """Sensor class"""
    default_device_class = "None"
    default_unit_of_measurement = "u"

    device_class = Field('device_class')
    unit_of_measurement = Field('unit_of_measurement')

    def __init__(self, data=None, *, mqtt_client: MQTTClient = None,
                 node_id=None, obj_id=None):
        super().__init__(data, mqtt_client=mqtt_client,
                         component_name="sensor",
                         node_id=node_id, obj_id=obj_id)
        self.value = 0

    def default_name(self):
        return self.default_device_class

    def make_config_data(self):
        if self.device_class is None:
            self.device_class = self.default_device_class
        if self.unit_of_measurement is None:
            self.unit_of_measurement = self.default_unit_of_measurement
        return super().make_config_data()


class Temperature(Sensor):
    """Temperature sensor"""
    default_device_class = "temperature"
    default_unit_of_measurement = "°C"


class Humidity(Sensor):
    """Temperature sensor"""
    default_device_class = "humidity"
    default_unit_of_measurement = "%"


class Battery(Sensor):
    """Temperature sensor"""
    default_device_class = "battery"
    default_unit_of_measurement = "%"
