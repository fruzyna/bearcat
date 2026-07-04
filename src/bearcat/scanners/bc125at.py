"""Defines functions used exclusively by the Uniden BC125AT scanner."""
from enum import Enum

from bearcat import Bearcat
from bearcat.classes import Modulation, Screen, RadioState, Channel
from bearcat.scanners import common, handheld
from bearcat.values import BASE_BYTE_MAP, BASE_TONE_MAP, HANDHELD_KEYS


class BC125AT_BacklightMode(Enum):
    """Enumeration of backlight modes supported by the BC125AT."""
    ALWAYS_ON = 'AO'
    ALWAYS_OFF = 'AF'
    KEYPRESS = 'KY'
    SQUELCH = 'SQ'
    KEYPRESS_SQUELCH = 'KS'


class BC125AT_CloseCallMode(Enum):
    """Enumeration of close call modes supported by the BC125AT."""
    OFF = '0'
    PRIORITY = '1'
    DND = '2'
    ONLY = '3'


class BC125AT_DelayTime(Enum):
    """Enumeration of allowed delay times."""
    MINUS_TEN = '-10'
    MINUS_FIVE = '-5'
    ZERO = '0'
    ONE = '1'
    TWO = '2'
    THREE = '3'
    FOUR = '4'
    FIVE = '5'


class BC125AT_TestMode(Enum):
    """Enumeration of various hardware test modes available on the BC125AT."""
    SOFTWARE = '1'
    CLOSE_CALL = '2'
    WEATHER_ALERT = '3'
    KEYPAD = '4'


def compare_channels(a: Channel, b: Channel) -> bool:
    return a.name == b.name and a.frequency == b.frequency and  a.modulation == b.modulation and \
        a.tone_code == b.tone_code and a.delay == b.delay and a.lockout == b.lockout and a.priority == b.priority


class BC125AT(Bearcat):
    """Uniden Bearcat BC125AT, a 500 channel analog scanner, released in 2012."""
    MODEL = 'BC125AT'
    AD_SCALING_FACTOR = 255
    TOTAL_CHANNELS = 500
    DISPLAY_WIDTH = 16
    BAUD_RATES = [115200]
    FREQUENCY_SCALE = 100
    MIN_FREQUENCY_HZ = int(25e6)
    MAX_FREQUENCY_HZ = int(512e6)
    NUM_SCAN_GROUPS = 10
    NUM_CUSTOM_SEARCH_GROUPS = 10
    NUM_SERVICE_SEARCH_GROUPS = 10
    NUM_FREQUENCY_BANDS = 5
    TONE_MAP = BASE_TONE_MAP
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
    long_press_key = common.long_press_key
    hold_key = common.hold_key
    release_key = common.release_key
    get_contrast = common.get_contrast
    set_contrast = common.set_contrast
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

    def get_status(self) -> tuple[Screen, bool, bool]:
        """
        Sends the get status (STS) command. This is an unofficial command for the BC125AT.

        Returns:
            object representation of the scanner's screen
            whether the scanner is squelched
            whether the scanner is muted.
        """
        response = self.execute_command('STS')
        return Screen(*response[:-9]), bool(int(response[-9])), bool(int(response[-8]))

    def get_reception_status(self) -> tuple[RadioState, bool, bool]:
        """
        Sends the get reception status (GLG) command. This is an unofficial command for the BC125AT.

        Returns:
            object representation of the scanner's radio state
            whether the scanner is squelched
            whether the scanner is muted.
        """
        response = self.execute_command('GLG')
        self.check_response(response, 12)
        freq = int(response[10]) if response[10] else 0
        state = RadioState(freq, response[6], int(response[0]) * self.FREQUENCY_SCALE,
                            Modulation(response[1]), int(response[3]))
        return state, bool(int(response[7])), bool(int(response[8]))

    def get_electronic_serial_number(self) -> tuple[str, str, str]:
        """
        Sends the get electronic serial number (ESN) command. This appears to be an unofficial and undocumented command
        for all scanners. It also appears to be unused on the BC125AT.

        Returns:
            14 Xs, likely an unused serial number
            3 0s, likely an unused product code
            1
        """
        response = self.execute_command('ESN')
        self.check_response(response, 3)
        return response[0], response[1], response[2]

    #
    # Program Mode Getters
    #

    def get_backlight(self) -> BC125AT_BacklightMode:
        """
        Sends the get backlight (BLT) command. Requires program mode.

        Returns:
            backlight mode as an enumeration
        """
        return BC125AT_BacklightMode(self.get_program_mode_string('BLT'))

    def get_charge_time(self) -> int:
        """
        Sends the get battery info (BSV) command. Requires program mode.

        Returns:
            battery charge time in hours, 1 - 16
        """
        return self.get_program_mode_number('BSV')

    def get_key_beep(self) -> tuple[bool, bool]:
        """
        Sends the get key beep (KBP) command. Requires program mode.

        Returns:
            whether the keypad beep is enabled
            whether the keypad is locked
        """
        response = self.execute_program_mode_command('KBP')
        self.check_response(response, 2)
        return not bool(int(response[0])), bool(int(response[1]))

    def get_channel_info(self, channel: int) -> Channel:
        """
        Sends the get channel info (CIN) command. Requires program mode.

        Args:
            channel: the channel number to investigate, 1 - 500

        Returns:
            object representation of the channel configuration
        """
        assert 1 <= channel <= self.TOTAL_CHANNELS
        response = self.execute_program_mode_command('CIN', str(channel))
        self.check_response(response, 8)
        return Channel(int(response[0]), response[1], int(response[2]) * self.FREQUENCY_SCALE,
                    Modulation(response[3]), int(response[4]), delay=response[5],
                    lockout=bool(int(response[6])), priority=bool(int(response[7])))

    def get_search_close_call_settings(self) -> tuple[BC125AT_DelayTime, bool]:
        """
        Sends the get search / close call settings (SCO) command. Requires program mode.

        Returns:
            delay time as an enumeration
            whether CTCSS/DCS code search is enabled
        """
        response = self.execute_program_mode_command('SCO')
        self.check_response(response, 2)
        return BC125AT_DelayTime(response[0]), bool(int(response[1]))

    def get_close_call_settings(self) -> tuple[BC125AT_CloseCallMode, bool, bool, list[bool], bool]:
        """
        Sends the get close call settings (CLC) command. Requires program mode.

        Returns:
            close call mode as an enumeration
            whether the alert beep is enabled
            whether the alert light is enabled
            a list of 5 bools representing whether each of the 5 close call bands are enabled
            whether scan is unlocked
        """
        response = self.execute_program_mode_command('CLC')
        self.check_response(response, 5)
        return BC125AT_CloseCallMode(response[0]), bool(int(response[1])), bool(int(response[2])),\
            [bool(int(c)) for c in response[3]], bool(int(response[4]))

    def get_service_search_group(self):
        """
        Sends the get service search group (SSG) command. Requires program mode.

        Returns:
            a list of 10 bools representing whether search is enabled for each of the 10 service groups
        """
        return self.get_program_mode_group('SSG', self.NUM_SERVICE_SEARCH_GROUPS)

    def get_weather_priority(self) -> bool:
        """
        Sends the get weather settings (WXS) command. Requires program mode.

        Returns:
            whether weather priority is enabled
        """
        return bool(self.get_program_mode_number('WXS'))

    #
    # Setters
    #

    def jump_to_channel(self, channel: int):
        """
        Jump to number tag (JNT) command. This is an unofficial command for the BC125AT.

        Args:
            channel: channel number
        """
        assert 1 <= channel <= self.TOTAL_CHANNELS, f'Unexpected channel number {channel}, expected 1 - 500'
        self.check_ok(self.execute_command('JNT', '', str(channel - 1)))

    #
    # Program Mode Setters
    #

    def set_backlight(self, mode: BC125AT_BacklightMode):
        """
        Sends the set backlight (BLT) command. Requires program mode.

        Args:
            mode: enumeration of the desired backlight mode
        """
        self.set_program_mode_value('BLT', mode.value)

    def set_charge_time(self, time: int):
        """
        Sends the set battery setting (BSV) command. Requires program mode despite manual not listing that.

        Args:
            time: battery charge time in hours, 1 - 14
        """
        assert 1 <= time <= 14, f'Unexpected charge time {time}, expected 1 - 14'
        self.set_program_mode_value('BSV', time)

    def set_key_beep(self, enabled: bool, lock: bool):
        """
        Sends the set key beep (KBP) command. Requires program mode.

        Args:
            enabled: whether keypad beep should be enabled
            lock: whether keypad lock should be enabled
        """
        self.check_ok(self.execute_program_mode_command('KBP', str(int(not enabled) * 99), str(int(lock))))

    def set_channel_info(self, channel: Channel):
        """
        Sends the set channel info (CIN) command. Requires program mode.

        Args:
            channel: object representation of the desired channel parameters
        """
        freq = int(channel.frequency / self.FREQUENCY_SCALE)
        self.check_ok(self.execute_program_mode_command('CIN', str(channel.index), channel.name, str(freq),
                    channel.modulation.value, str(channel.tone_code), channel.delay, str(int(channel.lockout)),
                    str(int(channel.priority))))

    def set_search_close_call_settings(self, delay: BC125AT_DelayTime, code_search: bool):
        """
        Sends the set search / close call settings (SCO) command. Requires program mode.

        Args:
            delay: enumeration of the desired delay time
            code_search: whether CTCSS/DCS code search should be enabled
        """
        self.check_ok(self.execute_program_mode_command('SCO', delay.value, str(int(code_search))))

    def set_close_call_settings(self, mode: BC125AT_CloseCallMode, beep: bool, light: bool, bands: list[bool], lockout: bool):
        """
        Sends the set close call settings (CLC) command. Requires program mode.

        Args:
            mode: object representation of the desired close call mode
            beep: whether alert beep should be enabled
            light: whether alert light should be enabled
            bands: list of 5 bools representing which close call bands should be enabled
                (25 - 54, 108 - 137, 137 - 174, 225 - 320, 320 - 512 MHz)
            lockout: whether scan should be unlocked
        """
        assert len(bands) == self.NUM_FREQUENCY_BANDS, f'Unexpected bands length of {len(bands)}, expected {self.NUM_FREQUENCY_BANDS}'
        band_str = ''.join([str(int(b)) for b in bands])
        self.check_ok(self.execute_program_mode_command('CLC', mode.value, str(int(beep)), str(int(light)),
                                                            band_str, str(int(lockout))))

    def set_service_search_group(self, states: list[bool]):
        """
        Sends the set service search group (SSG) command. Requires program mode.

        Args:
            states: list of 10 bools representing which of the 10 service groups should have search enabled
                (police, fire/EMS, HAM, marine, railroad, civil air, military air, CB, FRS/GMRS/MURS, racing)
        """
        self.set_program_mode_group('SSG', states, self.NUM_SERVICE_SEARCH_GROUPS)

    def set_weather_priority(self, on: bool):
        """
        Sends the set weather settings (WXS) command. Requires program mode.

        Args:
            on: whether to enable weather priority
        """
        self.set_program_mode_value('WXS', int(on))

    #
    # Combo Commands
    #

    def channel(self, channel: int):
        """Shortcut to jump to a given channel."""
        self.jump_to_channel(channel)

    def update_channel(self, channel: Channel):
        """Sets a given channel's info only if the info has changed."""
        if not compare_channels(self.get_channel_info(channel.index), channel):
            self.set_channel_info(channel)

    def clear_channel(self, index: int):
        """Deletes a given channel if it currently has a name and frequency."""
        channel = self.get_channel_info(index)
        if channel.name or channel.frequency:
            common.delete_channel(self, index)


class UBC125XLT(BC125AT):
    """Uniden Bearcat UBC125XLT, the European version of the BC125AT."""
    MODEL = 'UBC125XLT'
    MAX_FREQUENCY_HZ = int(905e6)
    NUM_SERVICE_SEARCH_GROUPS = 7


class UBC126AT(BC125AT):
    """Uniden Bearcat UBC126AT, the Australia & New Zealand version of the BC125AT."""
    MODEL = 'UBC126AT'
    MAX_FREQUENCY_HZ = int(905e6)
    NUM_SERVICE_SEARCH_GROUPS = 9
