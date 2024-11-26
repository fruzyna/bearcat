"""Contains the class representation of the Uniden BC125AT scanner."""
from bearcat import Modulation, KeyAction, DelayTime, UnexpectedResultError, Screen, CommandNotFound, CommandInvalid, \
    OperationMode

import socket
import serial
from enum import Enum
from threading import Thread, Lock
from typing import Union, Tuple, List


class BC125AT:
    """
    Object for interacting with the Uniden BC125AT serial API. All official and many known unofficial calls are
    supported. See https://info.uniden.com/twiki/pub/UnidenMan4/BC125AT/BC125AT_PC_Protocol_V1.01.pdf for official API.
    """

    ENCODING = 'ascii'
    TOTAL_CHANNELS = 500
    DISPLAY_WIDTH = 16
    FREQUENCY_SCALE = 100
    MIN_FREQUENCY_HZ = int(25e6)
    MAX_FREQUENCY_HZ = int(512e6)
    BAUD_RATES = [4800, 9600, 19200, 38400, 57600, 115200]
    AVAILABLE_KEYS = [
        '<', '^', '>',
        'H', '1', '2', '3',
        'S', '4', '5', '6',
        'R', '7', '8', '9',
        'L', 'E', '0', '.',
        'P', 'F'
    ]
    TONE_MAP = {
        # modes
        'NONE': 0, 'ALL': 0, 'SEARCH': 127, 'NO_TONE': 240,
        # CTCSS
        67.0: 64, 69.3: 65, 71.9: 66, 74.4: 67, 77.0: 68, 79.7: 69, 82.5: 70, 85.4: 71, 88.5: 72, 91.5: 73, 94.8: 74,
        97.4: 75, 100.0: 76, 103.5: 77, 107.2: 78, 110.9: 79, 114.8: 80, 118.8: 81, 123.0: 82, 127.3: 83, 131.8: 84,
        136.5: 85, 141.3: 86, 146.2: 87, 151.4: 88, 156.7: 89, 159.8: 90, 162.2: 91, 165.5: 92, 167.9: 93, 171.3: 94,
        173.8: 95, 177.3: 96, 179.9: 97, 183.5: 98, 186.2: 99, 189.9: 100, 192.8: 101, 196.6: 102, 199.5: 103,
        203.5: 104, 206.5: 105, 210.7: 106, 218.1: 107, 225.7: 108, 229.1: 109, 233.6: 110, 241.8: 111, 250.3: 112,
        254.1: 113,
        # DCS
        23: 128, 25: 129, 26: 130, 31: 131, 32: 132, 36: 133, 43: 134, 47: 135, 51: 136, 53: 137, 54: 138, 65: 139,
        71: 140, 72: 141, 73: 142, 74: 143, 114: 144, 115: 145, 116: 146, 122: 147, 125: 148, 131: 149, 132: 150,
        134: 151, 143: 152, 145: 153, 152: 154, 155: 155, 156: 156, 162: 157, 165: 158, 172: 159, 174: 160, 205: 161,
        212: 162, 223: 163, 225: 164, 226: 165, 243: 166, 244: 167, 245: 168, 246: 169, 251: 170, 252: 171, 255: 172,
        261: 173, 263: 174, 265: 175, 266: 176, 271: 177, 274: 178, 306: 179, 311: 180, 315: 181, 325: 182, 331: 183,
        332: 184, 343: 185, 346: 186, 351: 187, 356: 188, 364: 189, 365: 190, 371: 191, 411: 192, 412: 193, 413: 194,
        423: 195, 431: 196, 432: 197, 445: 198, 446: 199, 452: 200, 454: 201, 455: 202, 462: 203, 464: 204, 465: 205,
        466: 206, 503: 207, 506: 208, 516: 209, 523: 210, 526: 211, 532: 212, 546: 213, 565: 214, 606: 215, 612: 216,
        624: 217, 627: 218, 631: 219, 632: 220, 654: 221, 662: 222, 664: 223, 703: 224, 712: 225, 723: 226, 731: 227,
        732: 228, 734: 229, 743: 230, 754: 231
    }

    class BacklightMode(Enum):
        """Enumeration of backlight modes supported by the BC125AT."""
        ALWAYS_ON = 'AO'
        ALWAYS_OFF = 'AF'
        KEYPRESS = 'KY'
        SQUELCH = 'SQ'
        KEYPRESS_SQUELCH = 'KS'

    class PriorityMode(Enum):
        """Enumeration of priority modes supported by the BC125AT."""
        OFF = '0'
        ON = '1'
        PLUS = '2'
        DND = '3'

    class CloseCallMode(Enum):
        """Enumeration of close call modes supported by the BC125AT."""
        OFF = '0'
        PRIORITY = '1'
        DND = '2'
        ONLY = '3'

    class TestMode(Enum):
        """Enumeration of various hardware test modes available on the BC125AT."""
        SOFTWARE = '1'
        CLOSE_CALL = '2'
        WEATHER_ALERT = '3'
        KEYPAD = '4'

    class RadioState:
        """Object representation of radio state returned by both GLG and CIN commands."""

        def __init__(self, index: int, name: str, frequency: int, modulation: Modulation, tone=0, tone_code=0):
            """
            Args:
                index: channel number (1 - 500)
                name: name of the selected channel, may be blank, must be <= 16 characters
                frequency: channel frequency in Hz
                modulation: modulation type
                tone: optional CTCSS tone in hertz or DSC code, if tone is 0 (default), tone_code is used instead
                tone_code: optional CTCSS/DCS code identifier, see TONE_MAP values
            """
            assert 0 < index <= BC125AT.TOTAL_CHANNELS or index == -1, f'Invalid channel number, {index}'
            self.index = index
            assert len(name) <= BC125AT.DISPLAY_WIDTH, f'Name too long, "{name}"'
            self.name = name
            assert BC125AT.MIN_FREQUENCY_HZ <= frequency <= BC125AT.MAX_FREQUENCY_HZ or frequency == 0,\
                f'Invalid frequency, {frequency}'
            self.frequency = frequency
            self.modulation = modulation
            if tone:
                assert tone in BC125AT.TONE_MAP
                self.tone_code = BC125AT.TONE_MAP[tone]
            else:
                self.tone_code = tone_code

        @classmethod
        def from_glg_response(cls, frequency: str, modulation: str, attenuation: str, tone_code: str, search_name: str,
                              group_name: str, channel_name: str, squelched: str, muted: str, _: str, index: str,
                              __: str) -> 'BC125AT.RadioState':
            """Alternative constructor, designed to take the response to the GLG command."""
            number = int(index) if index else -1
            return cls(number, channel_name, int(frequency) * BC125AT.FREQUENCY_SCALE, Modulation(modulation),
                       tone_code=int(tone_code))

        def __str__(self) -> str:
            return f'{self.index}: "{self.name}" {self.frequency / 1e6} MHz {self.modulation.value} {self.tone_code}'

    class Channel(RadioState):
        """Object representation of radio state used with CIN command."""

        def __init__(self, index: int, name: str, frequency: int, modulation: Modulation, tone=0, tone_code=0,
                     delay=DelayTime.TWO, lockout=True, priority=False):
            """
            Args:
                index: channel number (1-500)
                name: name of the selected channel, may be blank, must be <= 16 characters
                frequency: channel frequency in Hz
                modulation: modulation type
                tone: optional CTCSS tone in hertz or DSC code, if tone is 0 (default), tone_code is used instead
                tone_code: optional CTCSS/DCS code identifier, see TONE_MAP values
                delay: optional delay, default TWO
                lockout: optional channel lockout (removal from scan), default True
                priority: optional channel priority (one per bank), default False
            """
            super().__init__(index, name, frequency, modulation, tone, tone_code)
            self.index = index
            self.delay = delay
            self.lockout = lockout
            self.priority = priority

        @classmethod
        def from_cin_response(cls, index: str, name: str, frequency: str, modulation: str, tone_code: str, delay: str,
                              lockout: str, priority: str) -> 'BC125AT.Channel':
            """Alternative constructor, designed to take the response to the CIN command."""
            return cls(int(index), name, int(frequency) * BC125AT.FREQUENCY_SCALE, Modulation(modulation),
                       tone_code=int(tone_code), delay=DelayTime(delay), lockout=bool(int(lockout)),
                       priority=bool(int(priority)))

        def to_response(self) -> List[str]:
            """Generates a list of parameters from the channel for the CIN command."""
            return [str(self.index), self.name, str(int(self.frequency / BC125AT.FREQUENCY_SCALE)),
                    self.modulation.value, str(self.tone_code), self.delay.value, str(int(self.lockout)),
                    str(int(self.priority))]

        def __str__(self) -> str:
            locked = 'Locked' if self.lockout else 'Unlocked'
            priority = ' Priority' if self.priority else ''
            return f'{super().__str__()} {self.delay.value} s {locked}{priority}'

    def __init__(self, port: str, baud_rate=115200, timeout=0.1):
        """
        Args:
            port: serial port name, /dev/ttyX on Linux, COMX on Windows
            baud_rate: optional serial port speed in bits per second, default 115200
            timeout: optional serial connection timeout in seconds, default 1/10
        """
        if len(port.split('.')) == 4:
            self._serial = None
            if ':' in port:
                parts = port.split(':')
                address = parts[0]
                port = int(parts[1])
            else:
                address = port
                port = 65125

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((address, port))
        else:
            self._socket = None
            assert baud_rate in self.BAUD_RATES
            self._serial = serial.Serial(port=port, baudrate=baud_rate, stopbits=serial.STOPBITS_ONE,
                                         bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, xonxoff=False,
                                         rtscts=False, dsrdtr=False, timeout=timeout)

        self._in_program_mode = False
        self.debug = False
        self._cmd_lock = Lock()

    def listen(self, address='127.0.0.1', port=65125):
        """Creates a server socket for other BC125AT instances to send their bytes to."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((address, port))
        s.listen()
        Thread(target=self._server_thread, args=(s,), daemon=True).start()

    def _server_thread(self, s: socket.socket):
        """Thread that accepts all incoming connections to the server socket. Created automatically by listen()."""
        while True:
            client, addr = s.accept()
            Thread(target=self._client_listener, args=(client,), daemon=True).start()

    def _client_listener(self, s: socket.socket):
        """Thread that handles all active client connections. Create automatically by _server_thread()."""
        while True:
            recv_bytes = s.recv(4096)
            if not recv_bytes:
                break

            s.sendall(self._execute_command_raw(recv_bytes))

        s.close()

    #
    # Command Execution Helpers
    #

    def _execute_command_raw(self, command: bytes) -> bytes:
        """Executes a command and returns the response all in bytes."""
        with self._cmd_lock:
            if self._serial:
                self._serial.write(command)
                return self._serial.readline()
            elif self._socket:
                self._socket.sendall(command)
                return self._socket.recv(4096)

    def _execute_command(self, *command: str) -> List[str]:
        """Executes a command and returns the response."""
        # build and send command
        cmd_str = ','.join(command).upper() + '\r'
        cmd_bytes = cmd_str.encode(BC125AT.ENCODING)
        res_bytes = self._execute_command_raw(cmd_bytes)
        if self.debug:
            print('[SENT]\t\t', cmd_str)

        # read the command response and replace special characters with reasonable alternatives
        # TODO: figure out how to manually decode with a custom char set
        res_bytes = res_bytes.replace(b'\x80', b'=').replace(b'\x81', b'|^').replace(b'\x82', b'|v')\
                             .replace(b'\x8b', b'F').replace(b'\x8c', b'P').replace(b'\x91', b'+')\
                             .replace(b'\x92', b'C').replace(b'\x8d\x8e\x8f\x90', b'HOLD')\
                             .replace(b'\x93\x94\x96\x97', b'TL/O').replace(b'\x95\x96\x97', b'L/O')\
                             .replace(b'\x98\x99\x9a', b'AM').replace(b'\x9b\x9c\x9a', b'FM')\
                             .replace(b'\x9d\x9e\x9c\x9a', b'NFM').replace(b'\xa1\xa2', b'PRI').replace(b'\xa6', b'1')\
                             .replace(b'\xa7', b'2').replace(b'\xa8\xa9', b'3').replace(b'\xaa\xab', b'4')\
                             .replace(b'\xac\xad', b'5').replace(b'\xb1', b'[').replace(b'\xb2', b' ')\
                             .replace(b'\xb3', b']').replace(b'\xc5\xc6\xc7', b'SRC:')\
                             .replace(b'\xcd\xce\xcf', b'BNK:').replace(b'\xd4\xd5\xd6', b'SVC:')

        # check for remaining special characters
        if self.debug:
            for i in range(len(res_bytes)):
                if res_bytes[i] > 128:
                    print(res_bytes[i])

        # decode command string and parse as comma separated string
        res_str = res_bytes.decode(BC125AT.ENCODING).strip()
        res_parts = res_str.split(',')
        if self.debug:
            print('[RECEIVED]\t', res_str)

        # determine if the command successfully ran
        if res_parts[0] == 'ERR':
            raise CommandNotFound('Scanner did not recognize command')
        elif res_parts[0] != command[0]:
            raise UnexpectedResultError(f'Unrecognized command response, {res_parts[0]}')
        elif len(res_parts) == 1:
            raise UnexpectedResultError('No value returned')
        elif res_parts[1] == 'NG':
            raise CommandInvalid('Scanner did not recognize command at this time')

        # skip command and return result
        return res_parts[1:]

    @staticmethod
    def _check_response(response: List[str], expected_values: int):
        """Used for to check that the correct number of values were returned. Raises an UnexpectedResultError is not."""
        if len(response) != expected_values:
            raise UnexpectedResultError(f'{len(response)} values returned, expected {expected_values}')

    @staticmethod
    def _check_ok(response: List[str]):
        """Used for basic commands to check that OK was returned. Raises an UnexpectedResultError is not OK."""
        BC125AT._check_response(response, 1)
        if response[0] != 'OK':
            raise UnexpectedResultError(f'Not OK response, "{response[0]}"')

    def _execute_action(self, cmd: str):
        """Executes a specified action (no arguments, no response value)."""
        self._check_ok(self._execute_command(cmd))

    def _get_string(self, cmd: str) -> str:
        """Sends a given command expecting a single value in return."""
        response = self._execute_command(cmd)
        self._check_response(response, 1)
        return response[0]

    def _get_number(self, cmd: str) -> int:
        """Sends a given command expecting a single integer in return."""
        response = self._get_string(cmd)
        return int(response)

    def _set_value(self, cmd: str, value: Union[str, int]):
        """Sends a given command and value as a key-value pair."""
        self._check_ok(self._execute_command(cmd, str(value)))

    def _execute_program_mode_command(self, *command: str) -> List[str]:
        """Executes a command and returns the response for commands that require program mode."""
        already_program = self._in_program_mode
        if not already_program:
            self.enter_program_mode()

        response = self._execute_command(*command)

        if not already_program:
            self.exit_program_mode()

        return response

    def _get_program_mode_string(self, cmd: str) -> str:
        """Sends a given command expecting a single value in return, for commands that require program mode."""
        response = self._execute_program_mode_command(cmd)
        self._check_response(response, 1)
        return response[0]

    def _get_program_mode_number(self, cmd: str) -> int:
        """Sends a given command expecting a single integer in return, for commands that require program mode."""
        response = self._get_program_mode_string(cmd)
        return int(response)

    def _get_program_mode_group(self, cmd: str) -> List[bool]:
        """
        Sends a given command expecting a string representing a list of booleans in return, for commands that require
        program mode.
        """
        response = self._get_program_mode_string(cmd)
        if len(response) != 10:
            raise UnexpectedResultError(f'{len(response)} values returned, expected 10')

        return [bool(c) for c in response]

    def _set_program_mode_value(self, cmd: str, value: Union[str, int]):
        """Sends a given command and value as a key-value pair for commands that require program mode."""
        self._check_ok(self._execute_program_mode_command(cmd, str(value)))

    def _set_program_mode_group(self, cmd: str, states: List[bool]):
        """Sends a given command and string representing a list of booleans, for commands that require program mode."""
        assert len(states) == 10, f'Unexpected states length of {len(states)}, expected 10'
        state_str = ''.join([str(int(b)) for b in states])
        self._set_program_mode_value(cmd, state_str)

    #
    # Actions
    #

    def power_off(self):
        """Sends the power off (POF) command. This is an unofficial command for the BC125AT."""
        self._execute_action('POF')

    def enter_program_mode(self):
        """Sends the enter program mode (PRG) command. Required for many commands. Prevents scanner operation."""
        self._execute_action('PRG')
        self._in_program_mode = True

    def exit_program_mode(self):
        """Sends the exit program mode (EPG) command. Resumes normal scanner operation."""
        self._execute_action('EPG')
        self._in_program_mode = False

    #
    # Getters
    #

    def get_status(self) -> Tuple[Screen, bool, bool]:
        """
        Sends the get status (STS) command. This is an unofficial command for the BC125AT.

        Returns:
            object representation of the scanner's screen
            whether the scanner is squelched
            whether the scanner is muted.
        """
        response = self._execute_command('STS')
        return Screen(*response[:-9]), bool(int(response[-9])), bool(int(response[-8]))

    def get_reception_status(self) -> Tuple[RadioState, bool, bool]:
        """
        Sends the get reception status (GLG) command. This is an unofficial command for the BC125AT.

        Returns:
            object representation of the scanner's radio state
            whether the scanner is squelched
            whether the scanner is muted.
        """
        response = self._execute_command('GLG')
        self._check_response(response, 12)
        return BC125AT.RadioState.from_glg_response(*response), bool(int(response[7])), bool(int(response[8]))

    def get_model(self) -> str:
        """
        Sends the get model (MDL) command.

        Returns:
            scanner's model number (BC125AT)
        """
        return self._get_string('MDL')

    def get_version(self) -> str:
        """
        Sends the get version (VER) command.

        Returns:
            scanner's firmware version number
        """
        return self._get_string('VER')

    def get_global_lockout_freq(self) -> int:
        """
        Sends the get global lockout freq (GLF) command.

        Returns:
            the next lockout frequency in Hz or -100 when all end of list is reached
        """
        return self._get_number('GLF') * BC125AT.FREQUENCY_SCALE

    def get_volume(self) -> int:
        """
        Sends the get volume (VOL) command.

        Returns:
            volume level, 0 - 15
        """
        return self._get_number('VOL')

    def get_squelch(self) -> int:
        """
        Sends the get squelch (SQL) command.

        Returns:
            squelch level, 0 - 15
        """
        return self._get_number('SQL')

    def get_battery_voltage(self) -> float:
        """
        Sends the get battery voltage (BAV) command. This is an unofficial command for the BC125AT.

        Returns:
            battery potential in volts
        """
        return self._get_number('BAV') * 6.4 / 1023

    def get_window_voltage(self) -> Tuple[float, float]:
        """
        Sends the get window voltage (WIN) command. This is an unofficial command for the BC125AT.

        Returns:
            window potential as a percent of the A/D value, 0 - 1
            window frequency in Hz
        """
        response = self._execute_command('WIN')
        self._check_response(response, 2)
        # TODO: determine scaling factor of voltage A/D and return voltage
        return int(response[0]) / 255, int(response[1]) * BC125AT.FREQUENCY_SCALE

    def get_electronic_serial_number(self) -> Tuple[str, str, str]:
        """
        Sends the get electronic serial number (ESN) command. This appears to be an unofficial and undocumented command
        for all scanners. It also appears to be unused on the BC125AT.

        Returns:
            14 Xs, likely an unused serial number
            3 0s, likely an unused product code
            1
        """
        response = self._execute_command('ESN')
        self._check_response(response, 3)
        return response[0], response[1], response[2]

    def memory_read(self, location: int) -> Tuple[List[int], int]:
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
        response = self._execute_command('MRD', str(location))
        self._check_response(response, 18)
        assert int(response[0], 16) == location
        return [int(b, 16) for b in response[1:17]], int(response[17], 16)

    #
    # Program Mode Getters
    #

    def get_backlight(self) -> BacklightMode:
        """
        Sends the get backlight (BLT) command. Requires program mode.

        Returns:
            backlight mode as an enumeration
        """
        return BC125AT.BacklightMode(self._get_program_mode_string('BLT'))

    def get_charge_time(self) -> int:
        """
        Sends the get battery info (BSV) command. Requires program mode.

        Returns:
            battery charge time in hours, 1 - 16
        """
        return self._get_program_mode_number('BSV')

    def get_band_plan(self) -> bool:
        """
        Sends the get band plan (BPL) command. Requires program mode.

        Returns:
            whether the Canadian (True) or American (False) band plan is selected
        """
        return bool(self._get_program_mode_number('BPL'))

    def get_key_beep(self) -> Tuple[bool, bool]:
        """
        Sends the get key beep (KBP) command. Requires program mode.

        Returns:
            whether the keypad beep is enabled
            whether the keypad is locked
        """
        response = self._execute_program_mode_command('KBP')
        self._check_response(response, 2)
        return not bool(int(response[0])), bool(int(response[1]))

    def get_priority_mode(self) -> PriorityMode:
        """
        Sends the get priority mode (PRI) command. Requires program mode.

        Returns:
            priority mode as an enumeration
        """
        return BC125AT.PriorityMode(self._get_program_mode_number('PRI'))

    def get_scan_channel_group(self) -> List[bool]:
        """
        Sends the get scan channel group (SCG) command. Requires program mode.

        Returns:
            a list of 10 bools representing whether scanning is enabled for each of the 10 channel groups
        """
        return self._get_program_mode_group('SCG')

    def get_channel_info(self, channel: int) -> Channel:
        """
        Sends the get channel info (CIN) command. Requires program mode.

        Args:
            channel: the channel number to investigate, 1 - 500

        Returns:
            object representation of the channel configuration
        """
        assert 1 <= channel <= BC125AT.TOTAL_CHANNELS
        response = self._execute_program_mode_command('CIN', str(channel))
        self._check_response(response, 8)
        return BC125AT.Channel.from_cin_response(*response)

    def get_search_close_call_settings(self) -> Tuple[DelayTime, bool]:
        """
        Sends the get search / close call settings (SCO) command. Requires program mode.

        Returns:
            delay time as an enumeration
            whether CTCSS/DCS code search is enabled
        """
        response = self._execute_program_mode_command('SCO')
        self._check_response(response, 2)
        return DelayTime(response[0]), bool(int(response[1]))

    def get_close_call_settings(self) -> Tuple[CloseCallMode, bool, bool, List[bool], bool]:
        """
        Sends the get close call settings (CLC) command. Requires program mode.

        Returns:
            close call mode as an enumeration
            whether the alert beep is enabled
            whether the alert light is enabled
            a list of 5 bools representing whether each of the 5 close call bands are enabled
            whether scan is unlocked
        """
        response = self._execute_program_mode_command('CLC')
        self._check_response(response, 5)
        return BC125AT.CloseCallMode(response[0]), bool(int(response[1])), bool(int(response[2])),\
            [bool(c) for c in response[3]], bool(int(response[4]))

    def get_service_search_group(self):
        """
        Sends the get service search group (SSG) command. Requires program mode.

        Returns:
            a list of 10 bools representing whether search is enabled for each of the 10 service groups
        """
        return self._get_program_mode_group('SSG')

    def get_custom_search_group(self) -> List[bool]:
        """
        Sends the get custom search group (CSG) command. Requires program mode.

        Returns:
            a list of 10 bools representing whether search is enabled for each of the 10 custom groups
        """
        return self._get_program_mode_group('CSG')

    def get_custom_search_settings(self, group: int) -> Tuple[int, int, int]:
        """
        Sends the get custom search settings (CSP) command. Requires program mode.

        Returns:
            search group number, 1 - 10
            search upper limit in Hz
            search lower limit in Hz
        """
        assert 1 <= group <= 10
        response = self._execute_program_mode_command('CSP', str(group))
        self._check_response(response, 3)
        return int(response[0]), int(response[1]) * BC125AT.FREQUENCY_SCALE, int(response[2]) * BC125AT.FREQUENCY_SCALE

    def get_weather_priority(self) -> bool:
        """
        Sends the get weather settings (WXS) command. Requires program mode.

        Returns:
            whether weather priority is enabled
        """
        return bool(self._get_program_mode_number('WXS'))

    def get_contrast(self) -> str:
        """
        Sends the get contrast (CNT) command. Requires program mode.

        Returns:
            display contrast level, 0 - 15
        """
        return self._get_program_mode_string('CNT')

    #
    # Setters
    #

    def unlock_global_lo(self, frequency: int):
        """
        Sends the unlock global lo (ULF) command.

        Args:
            frequency: frequency in Hz to unlock globally
        """
        assert BC125AT.MIN_FREQUENCY_HZ <= frequency <= BC125AT.MAX_FREQUENCY_HZ,\
            f'Unexpected frequency {frequency}, expected 25 - 512 MHz'
        self._set_value('ULF', frequency // BC125AT.FREQUENCY_SCALE)

    def set_volume(self, level: int):
        """
        Sends the set volume (VOL) command.

        Args:
            level: volume level, 0 - 15
        """
        assert 0 <= level <= 15, f'Unexpected volume level {level}, expected 0 - 15'
        self._set_value('VOL', level)

    def set_squelch(self, level: int):
        """
        Sends the set squelch (SQL) command.

        Args:
            level: volume level, 0 - 15
        """
        assert 0 <= level <= 15, f'Unexpected squelch level {level}, expected 0 - 15'
        self._set_value('SQL', level)

    def go_to_quick_search_hold_mode(self, frequency: int, delay=DelayTime.TWO):
        """
        Go to quick search hold mode (QSH) command. This is an unofficial command for the BC125AT.

        Args:
            frequency: channel frequency in Hz
            delay: optional delay, default TWO
        """
        assert BC125AT.MIN_FREQUENCY_HZ <= frequency <= BC125AT.MAX_FREQUENCY_HZ
        self._check_ok(self._execute_command('QSH', str(int(frequency / self.FREQUENCY_SCALE)), '', '', '', '',
                                             delay.value, '', '', '', '', '', '', ''))

    def jump_to_channel(self, channel: int):
        """
        Jump to number tag (JNT) command. This is an unofficial command for the BC125AT.

        Args:
            channel: channel number
        """
        assert 1 <= channel <= self.TOTAL_CHANNELS, f'Unexpected channel number {channel}, expected 1 - 500'
        self._check_ok(self._execute_command('JNT', '', str(channel - 1)))

    def jump_mode(self, mode: OperationMode):
        """Jump mode (JPM) command. This is an unofficial command for the BC125AT."""
        self._set_value('JPM', mode.value)

    def enter_test_mode(self, mode: TestMode):
        """Enter test mode (TST) command. This appears to be an unofficial and undocumented command for all scanners."""
        assert self._in_program_mode, 'Scanner must be manually put into program mode to use test mode'
        try:
            self._execute_command('TST', mode.value, 'UNIDEN_TEST_MODE')
        except UnexpectedResultError:
            pass
        self._in_program_mode = False

    #
    # Program Mode Setters
    #

    def set_backlight(self, mode: BacklightMode):
        """
        Sends the set backlight (BLT) command. Requires program mode.

        Args:
            mode: enumeration of the desired backlight mode
        """
        self._set_program_mode_value('BLT', mode.value)

    def set_band_plan(self, canada: bool):
        """
        Sends the set band plan (BPL) command. Requires program mode.

        Args:
            canada: whether Canadian (True) or American (False) band plan should be used
        """
        self._set_program_mode_value('BPL', int(canada))

    def set_charge_time(self, time: int):
        """
        Sends the set battery setting (BSV) command. Requires program mode despite manual not listing that.

        Args:
            time: battery charge time in hours, 1 - 14
        """
        assert 1 <= time <= 14, f'Unexpected charge time {time}, expected 1 - 14'
        self._set_value('BSV', time)

    def clear_all_memory(self):
        """Sends the clear all memory (CLR) command. Requires program mode. Factory resets the scanner."""
        self._check_ok(self._execute_program_mode_command('CLR'))

    def set_key_beep(self, enabled: bool, lock: bool):
        """
        Sends the set key beep (KBP) command. Requires program mode.

        Args:
            enabled: whether keypad beep should be enabled
            lock: whether keypad lock should be enabled
        """
        self._check_ok(self._execute_program_mode_command('KBP', str(int(not enabled) * 99), str(int(lock))))

    def set_priority_mode(self, mode: PriorityMode):
        """
        Sends the set priority mode (PRI) command. Requires program mode.

        Args:
            mode: enumeration of the desired priority
        """
        self._set_program_mode_value('PRI', mode.value)

    def set_scan_channel_group(self, states: List[bool]):
        """
        Sends the set scan channel group (SCG) command. Requires program mode.

        Args:
            states: list of 10 bools representing which of the 10 channel groups should have scanning enabled
        """
        self._set_program_mode_group('SCG', states)

    def delete_channel(self, channel: int):
        """
        Sends the delete channel (DCH) command. Requires program mode.

        Args:
            channel: channel number to delete
        """
        assert 1 <= channel <= BC125AT.TOTAL_CHANNELS
        self._set_program_mode_value('DCH', channel)

    def set_channel_info(self, channel: Channel):
        """
        Sends the set channel info (CIN) command. Requires program mode.

        Args:
            channel: object representation of the desired channel parameters
        """
        self._check_ok(self._execute_program_mode_command('CIN', *channel.to_response()))

    def set_search_close_call_settings(self, delay: DelayTime, code_search: bool):
        """
        Sends the set search / close call settings (SCO) command. Requires program mode.

        Args:
            delay: enumeration of the desired delay time
            code_search: whether CTCSS/DCS code search should be enabled
        """
        self._check_ok(self._execute_program_mode_command('SCO', delay.value, str(int(code_search))))

    def lock_out_frequency(self, frequency: int):
        """
        Sends the lock out frequency (LOF) command. Requires program mode.

        Args:
            frequency: frequency in Hz to lockout
        """
        assert BC125AT.MIN_FREQUENCY_HZ <= frequency <= BC125AT.MAX_FREQUENCY_HZ,\
            f'Unexpected frequency {frequency}, expected 25 - 512 MHz'
        self._set_program_mode_value('LOF', frequency // BC125AT.FREQUENCY_SCALE)

    def set_close_call_settings(self, mode: CloseCallMode, beep: bool, light: bool, bands: List[bool], lockout: bool):
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
        assert len(bands) == 5, f'Unexpected bands length of {len(bands)}, expected 5'
        band_str = ''.join([str(int(b)) for b in bands])
        self._check_ok(self._execute_program_mode_command('CLC', mode.value, str(int(beep)), str(int(light)),
                                                          band_str, str(int(lockout))))

    def set_service_search_group(self, states: List[bool]):
        """
        Sends the set service search group (SSG) command. Requires program mode.

        Args:
            states: list of 10 bools representing which of the 10 service groups should have search enabled
                (police, fire/EMS, HAM, marine, railroad, civil air, military air, CB, FRS/GMRS/MURS, racing)
        """
        self._set_program_mode_group('SSG', states)

    def set_custom_search_group(self, states: List[bool]):
        """
        Sends the set custom search group (CSG) command. Requires program mode.

        Args:
            states: list of 10 bools representing which of the 10 custom groups should have search enabled
        """
        self._set_program_mode_group('CSG', states)

    def set_custom_search_settings(self, index: int, lower_limit: int, upper_limit: int):
        """
        Sends the set custom search settings (CSP) command. Requires program mode.

        Args:
            index: custom search number
            lower_limit: desired custom search lower frequency limit in Hz
            upper_limit: desired custom search upper frequency limit in Hz
        """
        assert 1 <= index <= 10, f'Unexpected search index {index}, expected 1 - 10'
        assert BC125AT.MIN_FREQUENCY_HZ <= lower_limit <= BC125AT.MAX_FREQUENCY_HZ,\
            f'Unexpected lower limit {lower_limit}, expected 25 - 512 MHz'
        assert BC125AT.MIN_FREQUENCY_HZ <= upper_limit <= BC125AT.MAX_FREQUENCY_HZ,\
            f'Unexpected upper limit {upper_limit}, expected 25 - 512 MHz'
        self._check_ok(self._execute_program_mode_command('CSP', str(index),
                                                          str(lower_limit // BC125AT.FREQUENCY_SCALE),
                                                          str(upper_limit // BC125AT.FREQUENCY_SCALE)))

    def set_weather_priority(self, on: bool):
        """
        Sends the set weather settings (WXS) command. Requires program mode.

        Args:
            on: whether to enable weather priority
        """
        self._set_program_mode_value('WXS', int(on))

    def set_contrast(self, level: int):
        """
        Sends the set contrast (CNT) command. Requires program mode.

        Args:
            level: desired contrast level, 0 - 15
        """
        assert 0 <= level <= 15, f'Unexpected contrast level {level}, expected 0 - 15'
        self._set_program_mode_value('CNT', level)

    #
    # Key Pushers
    #

    def _key_action(self, key: str, action: KeyAction):
        """
        Sends the key (KEY) command. This is an unofficial command for the BC125AT.

        Args:
            key: desired key to press
            action: enumeration of the desired action to perform on the given key
        """
        key = key.upper()
        assert len(key) == 1, 'Key must be a single character'
        assert key in BC125AT.AVAILABLE_KEYS, f'Unrecognized key, {key}'
        self._check_ok(self._execute_command('KEY', key, action.value))

    def press_key(self, key: str):
        """
        Simulates a key press.

        Args:
            key: desired key to press
        """
        self._key_action(key, KeyAction.PRESS)

    def press_key_sequence(self, keys: str):
        """
        Simulates a sequence of key presses.

        Args:
            keys: desired keys to press in sequence
        """
        for k in keys:
            if not self.press_key(k):
                raise UnexpectedResultError(f'Failed to send key press {k}')

    def long_press_key(self, key: str):
        """
        Simulates a long key press.

        Args:
            key: desired key to long press
        """
        self._key_action(key, KeyAction.LONG_PRESS)

    def hold_key(self, key: str):
        """
        Simulates a held key.

        Args:
            key: desired key to hold
        """
        self._key_action(key, KeyAction.HOLD)

    def release_key(self, key: str):
        """
        Simulates a released key.

        Args:
            key: desired key to release
        """
        self._key_action(key, KeyAction.RELEASE)
