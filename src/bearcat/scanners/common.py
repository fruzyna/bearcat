"""Defines functions available to most Uniden scanners."""
from enum import Enum
from typing import Tuple

from bearcat import Bearcat


class KeyAction(Enum):
    """Enumeration of possible keypad actions."""
    PRESS = 'P'
    LONG_PRESS = 'L'
    HOLD = 'H'
    RELEASE = 'R'

#
# Getters
#

def get_volume(self: Bearcat) -> int:
    """
    Sends the get volume (VOL) command.

    Returns:
        volume level, 0 - 15
    """
    return self.get_number('VOL')


def get_squelch(self: Bearcat) -> int:
    """
    Sends the get squelch (SQL) command.

    Returns:
        squelch level, 0 - 15
    """
    return self.get_number('SQL')


def get_window_voltage(self: Bearcat) -> Tuple[float, int]:
    """
    Sends the get window voltage (WIN) command. This is an unofficial command for many scanners.

    Returns:
        window potential as a percent of the A/D value, 0 - 1
        window frequency in Hz
    """
    response = self.execute_command('WIN')
    self.check_response(response, 2)
    # TODO: determine scaling factor of voltage A/D and return voltage
    return int(response[0]) / self.AD_SCALING_FACTOR, int(response[1]) * self.FREQUENCY_SCALE

#
# Setters
#

def set_volume(self: Bearcat, level: int):
    """
    Sends the set volume (VOL) command.

    Args:
        level: volume level, 0 - 15
    """
    assert 0 <= level <= 15, f'Unexpected volume level {level}, expected 0 - 15'
    self.set_value('VOL', level)


def set_squelch(self: Bearcat, level: int):
    """
    Sends the set squelch (SQL) command.

    Args:
        level: volume level, 0 - 15
    """
    assert 0 <= level <= 15, f'Unexpected squelch level {level}, expected 0 - 15'
    self.set_value('SQL', level)

#
# Program Mode Setters
#

def delete_channel(self: Bearcat, channel: int):
    """
    Sends the delete channel (DCH) command. Requires program mode.

    Args:
        channel: channel number to delete
    """
    assert 1 <= channel <= self.TOTAL_CHANNELS
    self.set_program_mode_value('DCH', channel)

#
# Key Pushers
#

def key_action(self: Bearcat, key: str, action: KeyAction):
    """
    Sends the key (KEY) command. This is an unofficial command for many scanners.

    Args:
        key: desired key to press
        action: enumeration of the desired action to perform on the given key
    """
    key = key.upper()
    assert len(key) == 1, 'Key must be a single character'
    assert key in self.AVAILABLE_KEYS, f'Unrecognized key, {key}'
    self.check_ok(self.execute_command('KEY', key, action.value))


def press_key(self: Bearcat, key: str):
    """
    Simulates a key press.

    Args:
        key: desired key to press
    """
    key_action(self, key, KeyAction.PRESS)


def press_key_sequence(self: Bearcat, keys: str):
    """
    Simulates a sequence of key presses.

    Args:
        keys: desired keys to press in sequence
    """
    for k in keys:
        press_key(self, k)


def long_press_key(self: Bearcat, key: str):
    """
    Simulates a long key press.

    Args:
        key: desired key to long press
    """
    key_action(self, key, KeyAction.LONG_PRESS)


def hold_key(self: Bearcat, key: str):
    """
    Simulates a held key.

    Args:
        key: desired key to hold
    """
    key_action(self, key, KeyAction.HOLD)


def release_key(self: Bearcat, key: str):
    """
    Simulates a released key.

    Args:
        key: desired key to release
    """
    key_action(self, key, KeyAction.RELEASE)

#
# Program Mode Getters
#

def get_contrast(self: Bearcat) -> int:
    """
    Sends the get contrast (CNT) command. Requires program mode.

    Returns:
        display contrast level, 1 - 15
    """
    return self.get_program_mode_number('CNT')

#
# Program Mode Setters
#

def set_contrast(self: Bearcat, level: int):
    """
    Sends the set contrast (CNT) command. Requires program mode.

    Args:
        level: desired contrast level, 1 - 15
    """
    assert 1 <= level <= 15, f'Unexpected contrast level {level}, expected 0 - 15'
    self.set_program_mode_value('CNT', level)
