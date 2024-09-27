"""
Base class of components
"""
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from ..model import Model, Field, json
from ..client import MQTTClient


class Base(Model):
    """
    This class define common behaviors of a component
    """
    hass_prefix = "homeassistant"
    default_component_name = "component"

    name = Field("name")
    device = Field("device")
    unique_id = Field("unique_id")
    state_topic = Field("state_topic")
    command_topic = Field("command_topic")
    command_template = Field("command_template")
    value_template = Field("value_template")

    availability_template = Field("availability_template")
    availability_topic = Field("availability_topic")
    default_sleep_time = 10

    @classmethod
    def value_cast(cls, x):
        """default value cast"""
        return x

    def __init__(self, data=None, *, mqtt_client: MQTTClient = None, component_name=None,
                 node_id=None, obj_id=None):
        super().__init__(data)
        self.mqtt_client = mqtt_client
        if component_name is None:
            component_name = self.default_component_name
        self.component_name = component_name
        self.node_id = node_id
        self.obj_id = obj_id

        self.value_path = None
        self.raw_value = None
        self.availability_payload = 'online'
        self.__post_init__()

    def __post_init__(self):
        pass

    def set_name(self, name):
        """set name"""
        self.name = name
        return self

    def set_device(self, device):
        """set device"""
        self.device = device.data

    def default_name(self):
        """generate a correct name based on info of self"""
        return self.component_name

    def make_unique_id(self):
        """generate a correct unique_id based on info of self"""
        unique_id = self.unique_id
        if unique_id is None:
            unique_id = self.name
            self.unique_id = unique_id
        return self

    def make_availability(self):
        """generate a correct availability based on info of self"""
        unique_id = self.unique_id
        if self.availability_topic is None:
            self.availability_topic = f'{self.default_component_name}/{unique_id}/state'
        if self.availability_template is None:
            self.availability_template = '{{ value_json }}'
        return self

    def make_state_topic(self):
        """generate a correct state_topic based on info of self"""
        unique_id = self.unique_id
        if self.state_topic is None:
            self.state_topic = f'{self.default_component_name}/{unique_id}/get'
        return self

    def make_command_topic(self):
        """generate a correct command_topic based on info of self"""
        unique_id = self.unique_id
        if self.command_topic is None:
            self.command_topic = f'{self.default_component_name}/{unique_id}/set'
        return self

    def make_value_source(self):
        """build the value based on path"""
        if self.value_path is None:
            return "value"
        return f"value_json.{self.value_path}"

    def make_value_template(self):
        """generate a correct value_template based on info of self"""
        if self.value_template is None:
            value = self.value_cast(self.make_value_source())
            self.value_template = '{{ %s }}' % value
        return self

    def make_config_data(self):
        """generate the json data used for MQTT discovery"""
        if self.name is None:
            self.name = self.default_name()
        self.make_unique_id()
        self.make_state_topic()
        self.make_command_topic()
        self.make_value_template()
        return self.data

    def publish(self, topic, msg, retain=False, qos=0):
        """publish a message"""
        if not isinstance(msg, bytes):
            msg = json.dumps(msg)
            msg = msg.encode()
        self.mqtt_client.publish(topic, msg, retain, qos)

    def send_config(self, retain=False, qos=0):
        """send MQTT discovery config"""
        topic = f"{self.hass_prefix}/{self.component_name}"
        node_id = self.node_id
        obj_id = self.obj_id
        if node_id is not None:
            topic += f'/{node_id}'
        if obj_id is None:
            obj_id = self.unique_id
        topic += f'/{obj_id}'
        topic += '/config'
        data = self.make_config_data()
        data['object_id'] = obj_id
        self.publish(topic, data, retain, qos)

    def online(self, is_online=True):
        """push availability"""
        payload = 'offline'
        if is_online:
            payload = 'online'
        if isinstance(self.availability_payload, dict):
            self.availability_payload[self.value_path] = payload
        else:
            self.availability_payload = payload
        self.publish(self.availability_topic, self.availability_payload)

    def push_availability(self, state):
        """push availability"""
        self.publish(self.availability_topic, state)

    def set_value(self, value):
        """set the value based on value_path"""
        if self.value_path is None:
            self.raw_value = value
        else:
            self.raw_value[self.value_path] = value
        return self

    def get_value(self):
        """get the value based on value_path"""
        if self.value_path is None:
            return self.raw_value
        return self.raw_value[self.value_path]

    @property
    def value(self):
        """value based on value_path"""
        return self.get_value()

    @value.setter
    def value(self, new_value):
        self.set_value(new_value)

    def push_state(self, retain=False, qos=0):
        """send the state"""
        self.publish(self.state_topic, self.raw_value, retain, qos)

    async def read(self):
        """how to read the value"""
        await asyncio.sleep(self.default_sleep_time)

    def set_reader(self, func):
        """set reader"""
        setattr(self, 'read', func)
        return func

    async def loop(self, push=True):
        """read loop"""
        while True:
            await self.read()
            if push:
                self.push_state()

    def write(self, msg):
        """write msg"""

    def set_writer(self, func):
        """set write"""
        setattr(self, 'write', func)
        return func

    def on_command(self, func):
        """This will trigger an MQTT subscribe"""
        setattr(self, 'write', func)
        self.mqtt_client.subscribe(self.command_topic, self.write)
        return func
