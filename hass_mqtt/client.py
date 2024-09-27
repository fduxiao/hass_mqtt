"""
This provides MQTT client with a registry map which can assign message to correct
callback functions correspondingly to the topic.
"""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import ujson as json
except ImportError:
    import json


try:
    from umqtt.robust import MQTTClient as _MQTTClient
except ImportError as err:
    raise ImportError("Please refer to https://github.com/fduxiao/umqtt_python") from err


from .model import Model, Field


class MQTTInfo(Model):
    """
    MQTT configuration
    """
    default_field_name = "mqtt"

    addr = Field('addr')
    port = Field('port')
    client_id = Field('client_id')
    username = Field('username')
    password = Field('password')


class MQTTClient:
    """
    This class wraps an MQTT client with an extra :py:class:`dict` called map.
    On receiving a subscribed message, the class will search for a call list
    in map using MQTT topic as the key. A decorator is provided to register
    a callback easily.
    """
    client: _MQTTClient

    def __init__(self, info: MQTTInfo = None, debug=False, keepalive=0, ssl=None) -> None:
        if info is not None:
            self.set_mqtt(info, debug, keepalive, ssl)

        self.map = {}  # dict literal

    def set_mqtt(self, info: MQTTInfo, debug=False, keepalive=0, ssl=None):
        """
        Set the mqtt client

        :param info: :py:class:`MQTTInfo`
        :param debug: debug all not
        :param keepalive: keepalive seconds. 0 for always.
        :param ssl: ssl
        :return:
        """
        self.client = _MQTTClient(
            info.client_id,
            info.addr,
            info.port,
            info.username,
            info.password,
            keepalive=keepalive,
            ssl=ssl
        )
        self.client.DEBUG = debug
        self.client.set_callback(self.sub_cb)
        return self

    def connect(self, clean_session=False, return_result=False):
        """
        Connect to the MQTT broker

        :param clean_session: MQTT clean session
        :param return_result: return the result of connect or self
        :return: By default, this returns self. If you want to check the result,
            set return_result to True.
        """
        r = self.client.connect(clean_session=clean_session)
        if return_result:
            return r
        return self

    def disconnect(self):
        """disconnect"""
        return self.client.disconnect()

    def wildcard_cb(self, topic, msg):
        """receive all messages regardless of topic"""

    def sub_cb(self, topic, msg):
        """callback of subscription"""
        self.wildcard_cb(topic, msg)
        cbs = self.map.get(topic, [])
        for one in cbs:
            one(msg)

    def subscribe(self, topic, func=None):
        """
        Register a callback under some topic. If you provide func,
        then it is just registered. Otherwise, a decorator is return,
        which receives the callback and registers it.

        :param topic: target MQTT topic
        :param func: callback function
        :return: self or a decorator
        """
        # always register self
        if isinstance(topic, str):
            topic = topic.encode()
        self.client.subscribe(topic)

        def decorator(real_f=None):
            """
            This is the decorator registering the callback.

            :param real_f: received callback
            :return: the callback itself
            """
            # called as a decorator
            # then register real_f
            if real_f is not None:
                cbs: list = self.map.setdefault(topic, [])
                cbs.append(real_f)
            return real_f

        if func is None:
            return decorator
        decorator(func)
        return self

    def publish(self, topic, msg, retain=False, qos=0):
        """publish a message"""
        if not isinstance(msg, bytes):
            msg = json.dumps(msg)
            msg = msg.encode()
        self.client.publish(topic, msg, retain, qos)

    def check_msg(self):
        """Check whether we have a msg or not. This is non-blocking"""
        return self.client.check_msg()

    def wait_msg(self):
        """Check whether we have a msg or not. This is blocking"""
        return self.client.wait_msg()

    async def loop(self, sleep=0):
        """
        In order to call the callbacks, you have to run this background
        to check the status

        :param sleep: duration between two call of check_msg
        :return:
        """
        while True:
            await asyncio.sleep(sleep)
            self.client.check_msg()
