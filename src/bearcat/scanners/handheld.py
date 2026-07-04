"""Defines functions that are applicable to most if not all known handheld Uniden scanners."""
from enum import Enum

from bearcat import Bearcat
from bearcat.classes import Screen
from bearcat.exceptions import UnexpectedResultError


class OperationMode(Enum):
    """Enumeration of operation modes of the scanner."""
    SCAN = 'SCN_MODE'
    SERVICE_SEARCH = 'SVC_MODE'
    CUSTOM_SEARCH = 'CTM_MODE'
    CLOSE_CALL = 'CC_MODE'
    WEATHER = 'WX_MODE'
    TONE_OUT = 'FTO_MODE'


class PriorityMode(Enum):
    """Enumeration of priority modes supported by these scanners."""
    OFF = '0'
    ON = '1'
    PLUS = '2'
    DND = '3'

#
# Actions
#

def power_off(self: Bearcat):
    """Sends the power off (POF) command. This is an unofficial command for many scanners."""
    self.execute_action('POF')

#
# Getters
#

def get_battery_voltage(self: Bearcat) -> float:
    """
    Sends the get battery voltage (BAV) command. This is an unofficial command for many scanners.

    Returns:
        battery potential in volts
    """
    return self.get_number('BAV') * 6.4 / 1023


def memory_read(self: Bearcat, location: int) -> tuple[list[int], int]:
    """
    Sends the memory read (MRD) command. This appears to be an unofficial and undocumented command for all
    scanners. There is a corresponding memory write (MWR) command that I am too afraid to investigate right now.

    Args:
        32-bit value, likely register number

    Returns:
        16 bytes likely starting at the given memory location
        32-bit value
    """
    assert 0 <= location <= 0xFFFFFFFF
    response = self.execute_command('MRD', str(location))
    self.check_response(response, 18)
    assert int(response[0], 16) == location
    return [int(b, 16) for b in response[1:17]], int(response[17], 16)

#
# Setters
#

def jump_mode(self: Bearcat, mode: OperationMode):
    """Jump mode (JPM) command. This is an unofficial command for these scanners."""
    self.set_value('JPM', mode.value)

#
# Program Mode Getters
#

def get_band_plan(self: Bearcat) -> bool:
    """
    Sends the get band plan (BPL) command. Requires program mode.

    Returns:
        whether the Canadian (True) or American (False) band plan is selected
    """
    return bool(self.get_program_mode_number('BPL'))


def get_custom_search_settings(self: Bearcat, group: int) -> tuple[int, int, int]:
    """
    Sends the get custom search settings (CSP) command. Requires program mode.

    Returns:
        search group number, 1 - 10
        search upper limit in Hz
        search lower limit in Hz
    """
    assert 1 <= group <= 10
    response = self.execute_program_mode_command('CSP', str(group))
    self.check_response(response, 3)
    return int(response[0]), int(response[1]) * self.FREQUENCY_SCALE, int(response[2]) * self.FREQUENCY_SCALE


def get_priority_mode(self: Bearcat) -> PriorityMode:
    """
    Sends the get priority mode (PRI) command. Requires program mode.

    Returns:
        priority mode as an enumeration
    """
    return PriorityMode(self.get_program_mode_string('PRI'))


def get_scan_channel_group(self: Bearcat) -> list[bool]:
    """
    Sends the get scan channel group (SCG) command. Requires program mode.

    Returns:
        a list of 10 bools representing whether scanning is enabled for each of the 10 channel groups
    """
    return self.get_program_mode_group('SCG', self.NUM_SCAN_GROUPS)

#
# Program Mode Setters
#

def set_band_plan(self: Bearcat, canada: bool):
    """
    Sends the set band plan (BPL) command. Requires program mode.

    Args:
        canada: whether Canadian (True) or American (False) band plan should be used
    """
    self.set_program_mode_value('BPL', int(canada))


def set_custom_search_settings(self: Bearcat, index: int, lower_limit: int, upper_limit: int):
    """
    Sends the set custom search settings (CSP) command. Requires program mode.

    Args:
        index: custom search number
        lower_limit: desired custom search lower frequency limit in Hz
        upper_limit: desired custom search upper frequency limit in Hz
    """
    assert 1 <= index <= 10, f'Unexpected search index {index}, expected 1 - 10'
    assert self.MIN_FREQUENCY_HZ <= lower_limit <= self.MAX_FREQUENCY_HZ,\
        f'Unexpected lower limit {lower_limit}, expected 25 - 512 MHz'
    assert self.MIN_FREQUENCY_HZ <= upper_limit <= self.MAX_FREQUENCY_HZ,\
        f'Unexpected upper limit {upper_limit}, expected 25 - 512 MHz'
    self.check_ok(self.execute_program_mode_command('CSP', str(index),
                                                        str(lower_limit // self.FREQUENCY_SCALE),
                                                        str(upper_limit // self.FREQUENCY_SCALE)))


def set_priority_mode(self: Bearcat, mode: PriorityMode):
    """
    Sends the set priority mode (PRI) command. Requires program mode.

    Args:
        mode: enumeration of the desired priority
    """
    self.set_program_mode_value('PRI', mode.value)


def go_to_quick_search_hold_mode(self: Bearcat, frequency: int, delay: str = ''):
    """
    Go to quick search hold mode (QSH) command. This is an unofficial command for these scanners.

    Args:
        frequency: channel frequency in Hz
        delay: optional delay, default TWO
    """
    if not delay:
        delay = '0'

    assert self.MIN_FREQUENCY_HZ <= frequency <= self.MAX_FREQUENCY_HZ,\
        f'Unexpected frequency {frequency}, expected {self.MIN_FREQUENCY_HZ} - {self.MAX_FREQUENCY_HZ}'
    self.check_ok(self.execute_command('QSH', str(int(frequency / self.FREQUENCY_SCALE)), '', '', '', '',
                                         delay, '', '', '', '', '', '', ''))


def set_scan_channel_group(self: Bearcat, states: list[bool]):
    """
    Sends the set scan channel group (SCG) command. Requires program mode.

    Args:
        states: list of 10 bools representing which of the 10 channel groups should have scanning enabled
    """
    self.set_program_mode_group('SCG', states, self.NUM_SCAN_GROUPS)


def enter_test_mode(self: Bearcat, mode: str):
    """Enter test mode (TST) command. This appears to be an unofficial and undocumented command for all scanners."""
    assert self.in_program_mode, 'Scanner must be manually put into program mode to use test mode'
    try:
        self.execute_command('TST', mode, 'UNIDEN_TEST_MODE')
    except UnexpectedResultError:
        pass

    self.in_program_mode = False

#
# Combo Commands
#

def scan_groups(self: Bearcat, *groups: int):
    """Applies a set of scan channel groups and switches to scan mode."""
    band_selection = [i + 1 in groups for i in range(10)]
    set_scan_channel_group(self, band_selection)
    jump_mode(self, OperationMode.SCAN)


def frequency(self: Bearcat, frequency_mhz: float):
    """Shortcut to jump to a given frequency."""
    go_to_quick_search_hold_mode(self, frequency=int(frequency_mhz * 1e6))


def get_status(self: Bearcat) -> tuple[Screen, bool, bool]:
    """DO NOT USE. Placeholder function that is implemented by all handhelds."""
    self.execute_command('STS')
    return Screen(), False, False


def print_screen(self: Bearcat):
    """Fetches and prints the current screen state."""
    screen, _, _ = get_status(self)
    print(screen)
