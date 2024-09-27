"""Switch"""
from .base import Base, Field


class Switch(Base):
    """Switch"""
    default_component_name = "switch"
    payload_on = Field("payload_on")
    payload_off = Field("payload_off")

    def __post_init__(self):
        self.value = "ON"

    def write(self, msg):
        self.value = msg
