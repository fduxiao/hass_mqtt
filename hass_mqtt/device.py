"""
This specifies what an MQTT device looks like
"""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import ujson as json
except ImportError:
    import json


from .model import Model, Field, DefaultFactory
from .client import MQTTClient
from . import components


class Device(Model):
    """device class"""
    hass_prefix = "homeassistant"

    name: str = Field('name')
    configuration_url: str = Field('configuration_url')
    connections: list = Field('connections', DefaultFactory(list))
    hw_version: str = Field('hw_version')
    identifiers: list = Field('identifiers', DefaultFactory(list))
    manufacturer: str = Field('manufacturer')
    model: str = Field('model')
    model_id: str = Field('model_id')
    serial_number: str = Field('serial_number')
    suggested_area: str = Field('suggested_area')
    sw_version: str = Field('sw_version')
    via_device: str = Field('via_device')

    def configure(self, name=None, url=None, connections=None, hw_version=None, identifiers=None,
                  manufacturer=None, model=None, model_id=None, serial_number=None,
                  suggested_area=None, sw_version=None, via_device=None):
        """A convenient way to set properties"""
        self.update_data(None, name=name, configuration_url=url, connections=connections,
                         hw_version=hw_version, identifiers=identifiers, manufacturer=manufacturer,
                         model=model, model_id=model_id, serial_number=serial_number,
                         suggested_area=suggested_area, sw_version=sw_version, via_device=via_device)
        if self.node_id is None:
            self.node_id = serial_number
        if self.state_topic is None:
            self.state_topic = f'device/{self.serial_number}/get'
        if self.command_topic is None:
            self.command_topic = f'device/{self.serial_number}/set'
        if self.availability_topic is None:
            self.availability_topic = f'device/{self.serial_number}/status'
        return self

    def __init__(self, data=None, *, mqtt_client: MQTTClient = None, node_id=None):
        super().__init__(data)
        self.mqtt_client = mqtt_client
        self.node_id = node_id
        self.counter = 0
        self.components = {}
        self.setdefault('serial_number', 'serial')
        # the value shared by all
        self.value = {}
        self.state_topic = None
        self.command_topic = None
        self.availability_topic = None
        self.availability_payload = {}

    def on_command(self, msg):
        """callback of MQTT subscription"""
        key, msg = msg.split(b';')
        key = key.decode()
        target: components.Base = self.components.get(key)
        if target is not None:
            target.write(msg)

    def subscribe(self):
        """subscribe to mqtt"""
        self.mqtt_client.subscribe(self.command_topic, self.on_command)

    def yield_name(self, prefix):
        """make new names"""
        self.counter += 1
        return f'{self.serial_number}_{prefix}_{self.counter}'

    def add_component(self, key: str, target: components.Base):
        """add component"""
        target.mqtt_client = self.mqtt_client
        if target.node_id is None:
            target.node_id = self.node_id
        if target.unique_id is None:
            unique_id = f'{self.serial_number}_{key}'
            target.unique_id = unique_id.lower()
        if key in self.components:
            raise KeyError(f'duplicated key: {key}')
        self.components[key] = target
        # set device info
        target.set_device(self)
        # set value
        self.value[key] = target.value
        target.raw_value = self.value
        target.value_path = key
        # set topics
        target.state_topic = self.state_topic
        target.command_topic = self.command_topic
        target.command_template = '%s;{{ value }}' % key
        return target

    def set_availability(self):
        """set availability"""
        target: components.Base
        for key, target in self.components.items():
            target.availability_topic = self.availability_topic
            target.availability_template = '{{ value_json.%s }}' % key
            target.availability_payload = self.availability_payload

    def send_config(self, retain=True, qos=0):
        """send config"""
        target: components.Base
        for target in self.components.values():
            target.send_config(retain, qos)
        return self

    def online(self, is_online=True, retain=True, qos=0):
        """push availability"""
        payload = 'offline'
        if is_online:
            payload = 'online'
        for key in self.components:
            self.availability_payload[key] = payload
        self.mqtt_client.publish(self.availability_topic, self.availability_payload, retain, qos)

    def push_state(self, retain=False, qos=0):
        """push state"""
        msg = json.dumps(self.value)
        msg = msg.encode()
        self.mqtt_client.publish(self.state_topic, msg, retain, qos)

    async def push_loop(self, sleep=1):
        """push loop"""
        while True:
            self.push_state()
            await asyncio.sleep(sleep)

    async def loop(self, sleep=1):
        """loop"""
        awaitable = [x.loop(push=False) for x in self.components.values()]
        awaitable.append(self.push_loop(sleep))
        await asyncio.gather(*awaitable)
