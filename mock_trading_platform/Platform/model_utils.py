import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    static_check_init_args = dataclass
else:

    def static_check_init_args(cls):
        return cls


def uuid_hex(name=None):
    if name:
        return uuid.uuid5(uuid.uuid4(), name).hex

    return uuid.uuid4().hex
