"""Defines functions used exclusively by the Uniden BC75XLT scanner."""
from enum import Enum

from bearcat import Bearcat
from bearcat.exceptions import UnexpectedResultError
from bearcat.classes import Modulation, Screen, RadioState, Channel
from bearcat.scanners import common, handheld
from bearcat.values import BASE_BYTE_MAP, HANDHELD_KEYS

class BC75XLT_CloseCallMode(Enum):
    """Enumeration of close call modes supported by the BC75XLT."""
    OFF = '0'
    PRIORITY = '1'
    DND = '2'


class BC75XLT_DelayTime(Enum):
    """Enumeration of allowed delay times."""
    ZERO = '0'
    TWO = '1'


class BC75XLT_TestMode(Enum):
    """Enumeration of various hardware test modes available on the BC75XLT."""
    SOFTWARE = '1'
    CLOSE_CALL = '2'
    KEYPAD = '4'
    DISPLAY = '5'


def compare_channels(a: Channel, b: Channel) -> bool:
    return a.frequency == b.frequency and a.delay == b.delay and a.lockout == b.lockout and a.priority == b.priority


def determine_modulation(frequency_hz: int):
    if frequency_hz < 28e6 or 108 <= frequency_hz < 137:
        return Modulation.AM
    else:
        return Modulation.NFM


class BC75XLT(Bearcat):
    """Uniden Bearcat BC75XLT, a 300 channel analog scanner."""
    MODEL = 'BC75XLT'
    AD_SCALING_FACTOR = 255
    TOTAL_CHANNELS = 300
    DISPLAY_WIDTH = 14
    BAUD_RATES = [57600]
    FREQUENCY_SCALE = 100
    MIN_FREQUENCY_HZ = int(25e6)
    MAX_FREQUENCY_HZ = int(512e6)
    NUM_SCAN_GROUPS = 10
    NUM_CUSTOM_SEARCH_GROUPS = 10
    NUM_SERVICE_SEARCH_GROUPS = 0
    NUM_FREQUENCY_BANDS = 4
    TONE_MAP = {}
    AVAILABLE_KEYS = HANDHELD_KEYS
    BYTE_MAP = BASE_BYTE_MAP

    #
    # External Functions
    #

    get_volume = common.get_volume
    get_squelch = common.get_squelch
    get_window_voltage = common.get_window_voltage
    set_volume = common.set_volume
    set_squelch = common.set_squelch
    delete_channel = common.delete_channel
    key_action = common.key_action
    press_key = common.press_key
    press_key_sequence = common.press_key_sequence
    hold_key = common.hold_key
    release_key = common.release_key
    power_off = handheld.power_off
    get_battery_voltage = handheld.get_battery_voltage
    memory_read = handheld.memory_read
    jump_mode = handheld.jump_mode
    get_band_plan = handheld.get_band_plan
    get_custom_search_settings = handheld.get_custom_search_settings
    get_priority_mode = handheld.get_priority_mode
    get_scan_channel_group = handheld.get_scan_channel_group
    set_band_plan = handheld.set_band_plan
    set_custom_search_settings = handheld.set_custom_search_settings
    set_priority_mode = handheld.set_priority_mode
    go_to_quick_search_hold_mode = handheld.go_to_quick_search_hold_mode
    set_scan_channel_group = handheld.set_scan_channel_group
    enter_test_mode = handheld.enter_test_mode
    scan_groups = handheld.scan_groups
    frequency = handheld.frequency
    print_screen = handheld.print_screen

    #
    # Getters
    #

    def get_power(self) -> tuple[float, float]:
        """
        Sends the get power (PWR) command. This is an unofficial command for the BC75XLT.

        Returns:
            received power on a scale of 0 to 1
            frequency in Hz
        """
        response = self.execute_command('PWR')
        self.check_response(response, 2)
        # TODO: convert to RSSI
        return int(response[0]) / 512, int(response[1]) * self.FREQUENCY_SCALE

    def get_status(self) -> tuple[Screen, bool, bool]:
        """
        Sends the get status (STS) command. This is an unofficial command for the BC75XLT.

        Returns:
            object representation of the scanner's screen
            whether the scanner is squelched
            whether the scanner is muted.
        """
        response = self.execute_command('STS')
        return Screen(*response[:-2]), bool(int(response[-2])), bool(int(response[-1]))

    def get_reception_status(self) -> tuple[RadioState, bool, bool]:
        """
        Sends the get reception status (GLG) command. This is an unofficial command for the BC75XLT.

        Returns:
            object representation of the scanner's radio state
            whether the scanner is squelched
            whether the scanner is muted.
        """
        response = self.execute_command('GLG')
        self.check_response(response, 12)
        freq = float(response[0]) if response[0] else 0
        state = RadioState(-1, '', int(freq * 1e6), Modulation(response[1]))
        return state, bool(int(response[7])), bool(int(response[8]))

    #
    # Program Mode Getters
    #

    def get_key_beep(self) -> bool:
        """
        Sends the get key beep (KBP) command. Requires program mode.

        Returns:
            whether the keypad is locked
        """
        # BC75XLT doesn't use first arg
        response = self.execute_program_mode_command('KBP')
        self.check_response(response, 2)
        return bool(int(response[1]))

    def get_channel_info(self, channel: int) -> Channel:
        """
        Sends the get channel info (CIN) command. Requires program mode.

        Args:
            channel: the channel number to investigate, 1 - 500

        Returns:
            object representation of the channel configuration
        """
        # BC75XLT skips modulation and tone code
        assert 1 <= channel <= self.TOTAL_CHANNELS
        response = self.execute_program_mode_command('CIN', str(channel))
        self.check_response(response, 8)
        frequency_hz = int(response[2]) * self.FREQUENCY_SCALE
        return Channel(int(response[0]), response[1], frequency_hz, determine_modulation(frequency_hz), 0,
                    response[5], bool(int(response[6])), bool(int(response[7])))

    def get_xlt_custom_search_group(self) -> tuple[list[bool], BC75XLT_DelayTime, bool]:
        """
        Sends the get custom search group (CSG) command. Requires program mode.

        Returns:
            a list of 10 bools representing whether search is enabled for each of the 10 custom groups
            delay time as an enumeration
            whether the direction is down or up
        """
        response = self.execute_program_mode_command('CSG')
        self.check_response(response, 3)

        if len(response[0]) != 10:
            raise UnexpectedResultError(f'{len(response)} values returned, expected 10')

        return self.parse_program_mode_group(response[0]), BC75XLT_DelayTime(response[1]), bool(int(response[2]))

    def get_custom_search_group(self) -> list[bool]:
        """
        Sends the get custom search group (CSG) command. Requires program mode.
        This is an special override implementation for BC75XLT since it does not follow the otherwise common pattern.
        get_xlt_custom_search_group is preferred function for this scanner.

        Returns:
            a list of 10 bools representing whether search is enabled for each of the 10 custom groups
        """
        return self.get_xlt_custom_search_group()[0]

    def get_search_close_call_settings(self) -> tuple[BC75XLT_DelayTime, bool]:
        """
        Sends the get search / close call settings (SCO) command. Requires program mode.

        Returns:
            delay time as an enumeration
            whether the direction is down or up
        """
        response = self.execute_program_mode_command('SCO')
        self.check_response(response, 3)
        return BC75XLT_DelayTime(response[0]), bool(int(response[2]))

    def get_close_call_settings(self) -> tuple[BC75XLT_CloseCallMode, bool, bool, list[bool]]:
        """
        Sends the get close call settings (CLC) command. Requires program mode.

        Returns:
            close call mode as an enumeration
            whether the alert beep is enabled
            whether the alert light is enabled
            a list of 4 bools representing whether each of the 4 close call bands are enabled
        """
        # BC75XLT missing lockout
        response = self.execute_program_mode_command('CLC')
        self.check_response(response, 5)
        bands = [not b for b in self.parse_program_mode_group(response[3])]
        del bands[3]
        return BC75XLT_CloseCallMode(response[0]), bool(int(response[1])), bool(int(response[2])), bands
            

    #
    # Program Mode Setters
    #

    def set_key_beep(self, lock: bool):
        """
        Sends the set key beep (KBP) command. Requires program mode.

        Args:
            lock: whether keypad lock should be enabled
        """
        self.check_ok(self.execute_program_mode_command('KBP', '', str(int(lock))))

    def set_channel_info(self, channel: Channel):
        """
        Sends the set channel info (CIN) command. Requires program mode.

        Args:
            channel: object representation of the desired channel parameters
        """
        self.check_ok(self.execute_program_mode_command('CIN', str(channel.index), '',
                                                        str(int(channel.frequency / self.FREQUENCY_SCALE)), '', '',
                                                        channel.delay, str(int(channel.lockout)),
                                                        str(int(channel.priority))))

    def set_xlt_custom_search_group(self, states: list[bool], delay: BC75XLT_DelayTime, direction_down: bool):
        """
        Sends the set custom search group (CSG) command. Requires program mode.

        Args:
            states: list of 10 bools representing which of the 10 custom groups should have search enabled
            delay: enumeration of the desired delay time
            direction_down: whether the direction is down or up
        """
        assert len(states) == 10, f'Unexpected states length of {len(states)}, expected 10'
        state_str = self.build_program_mode_group(states)
        self.check_ok(self.execute_program_mode_command('CSG', state_str, delay.value, str(int(direction_down))))

    def set_custom_search_group(self, states: list[bool]):
        """
        Sends the set custom search group (CSG) command. Requires program mode.
        This is an special override implementation for BC75XLT since it does not follow the otherwise common pattern.
        This implementation assumes a delay of 2 and downward search direction.
        set_xlt_custom_search_group is preferred function for this scanner.

        Args:
            states: list of 10 bools representing which of the 10 custom groups should have search enabled
        """
        self.set_xlt_custom_search_group(states, BC75XLT_DelayTime.TWO, True)

    def set_search_close_call_settings(self, delay: BC75XLT_DelayTime, direction_down: bool):
        """
        Sends the set search / close call settings (SCO) command. Requires program mode.

        Args:
            delay: enumeration of the desired delay time
            direction_down: whether the direction is down or up
        """
        self.check_ok(self.execute_program_mode_command('SCO', delay.value, '', str(int(direction_down))))

    def set_close_call_settings(self, mode: BC75XLT_CloseCallMode, beep: bool, light: bool, bands: list[bool]):
        """
        Sends the set close call settings (CLC) command. Requires program mode.

        Args:
            mode: object representation of the desired close call mode
            beep: whether alert beep should be enabled
            light: whether alert light should be enabled
            bands: list of 4 bools representing which close call bands should be enabled
                (25 - 54, 108 - 137, 137 - 174, 406 - 512 MHz)
        """
        assert len(bands) == self.NUM_FREQUENCY_BANDS, f'Unexpected bands length of {len(bands)}, expected {self.NUM_FREQUENCY_BANDS}'
        band_str = ''.join([str(int(b)) for b in bands])
        band_str = band_str[:3] + '0' + band_str[3]  # 4th value is a reserved 0
        self.check_ok(self.execute_program_mode_command('CLC', mode.value, str(int(beep)), str(int(light)), band_str, ''))

    #
    # Key Pushers
    #

    def long_press_key(self: Bearcat, key: str):
        """
        Simulates a long key press.
        This is re-implemented with a try-except because it returns an invalid response despite working.
        The only documented use for long pressing a key is long pressing L/O (L) to clear all lock outs.

        Args:
            key: desired key to long press
        """
        try:
            common.long_press_key(self, key)
        except UnexpectedResultError:
            pass

    #
    # Combo Commands
    #

    def channel(self, channel: int):
        """Shortcut to jump to a given channel."""
        handheld.go_to_quick_search_hold_mode(self, 25000000)
        common.press_key_sequence(self, f'{channel}H')

    def update_channel(self, channel: Channel):
        """Sets a given channel's info only if the info has changed."""
        if not compare_channels(self.get_channel_info(channel.index), channel):
            self.set_channel_info(channel)

    def clear_channel(self, index: int):
        """Deletes a given channel if it currently has a frequency."""
        channel = self.get_channel_info(index)
        if channel.frequency:
            modulation = determine_modulation(channel.frequency)
            self.set_channel_info(Channel(channel.index, '', 0, modulation, 0, BC75XLT_DelayTime.ZERO.value, True, False))
