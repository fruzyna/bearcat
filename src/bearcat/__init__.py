"""Contains the base Bearcat class and functions used to detect and connect to scanners."""
import socket
import serial
from threading import Thread, Lock
from typing import Union

from bearcat.exceptions import CommandNotFound, CommandInvalid, UnexpectedResultError
from bearcat.values import ALL_BAUD_RATES, BASE_BYTE_MAP


class Bearcat():
    """Base object that represents core functionality and implements API calls available to all Uniden Bearcat scanners."""

    ENCODING = 'ascii'
    BYTE_MAP = BASE_BYTE_MAP
    MODEL = 'UNKNOWN'
    AD_SCALING_FACTOR = 255
    TOTAL_CHANNELS = 0
    BAUD_RATES = ALL_BAUD_RATES
    FREQUENCY_SCALE = 100
    MIN_FREQUENCY_HZ = 0
    MAX_FREQUENCY_HZ = 0
    NUM_SCAN_GROUPS = 0
    NUM_CUSTOM_SEARCH_GROUPS = 0
    TONE_MAP: dict[Union[str, float], int] = {}
    AVAILABLE_KEYS: list[str] = []

    def __init__(self, port: str = '127.0.0.1', baud_rate: int = -1, timeout: float = 0.1):
        """
        Args:
            port: serial port name (/dev/ttyX on Linux, COMX on Windows) or proxy address, default 127.0.0.1:65125
            baud_rate: optional serial port speed in bits per second, default 115200
            timeout: optional serial connection timeout in seconds, default 1/10 sec
        """
        if port.count('.') == 3:
            self._serial = None
            if ':' in port:
                parts = port.split(':')
                address = parts[0]
                sock_port = int(parts[1])
            else:
                address = port
                sock_port = 65125

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((address, sock_port))
        else:
            self._socket = None
            if baud_rate < 0:
                baud_rate = self.BAUD_RATES[0]

            assert baud_rate in self.BAUD_RATES
            self._serial = serial.Serial(port=port, baudrate=baud_rate, stopbits=serial.STOPBITS_ONE,
                                         bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, xonxoff=False,
                                         rtscts=False, dsrdtr=False, timeout=timeout)

        self.in_program_mode = False
        self.debug = False
        self._cmd_lock = Lock()

    def listen(self, address: str = '127.0.0.1', port: int = 65125):
        """Creates and starts a server socket for other instances to send their bytes to."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((address, port))
        s.listen()
        Thread(target=self._server_thread, args=(s,), daemon=True).start()

    def _server_thread(self, s: socket.socket):
        """Thread that accepts all incoming connections to the server socket. Created automatically by listen()."""
        while True:
            client, _ = s.accept()
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

    def _extend_ascii(self, input_bytes: bytes) -> bytes:
        """Replaces Uniden's extended ASCII characters with ASCII characters from the class's byte map."""
        output_bytes = bytes()
        for b in input_bytes:
            if b < 0x80:
                output_bytes += bytes([b])
            else:
                try:
                    output_bytes += self.BYTE_MAP[b]
                except:
                    raise UnexpectedResultError(f'Invalid byte in response, {b}')

        return output_bytes

    def _execute_command_raw(self, command: bytes) -> bytes:
        """Executes a command and returns the response all in bytes."""
        with self._cmd_lock:
            if self._serial:
                self._serial.write(command)
                return self._serial.readline()
            elif self._socket:
                self._socket.sendall(command)
                return self._socket.recv(4096)
            
        return bytes()

    def execute_command(self, *command: str) -> list[str]:
        """Executes a command and returns the response."""
        # build and send command
        if command[0].upper() == 'CIN':
            cmd_str = ','.join([c.upper() if i != 2 else c for i, c in enumerate(command)]) + '\r'
        else:
            cmd_str = ','.join(command).upper() + '\r'
        cmd_bytes = cmd_str.encode(self.ENCODING)
        res_bytes = self._execute_command_raw(cmd_bytes)
        if self.debug:
            print('[SENT]\t\t', cmd_str)

        # decode command string and parse as comma separated string
        res_str = self._extend_ascii(res_bytes).decode('UTF-8').strip()
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
    def check_response(response: list[str], expected_values: int):
        """Used for to check that the correct number of values were returned. Raises an UnexpectedResultError is not."""
        if len(response) != expected_values:
            raise UnexpectedResultError(f'{len(response)} values returned, expected {expected_values}')

    @staticmethod
    def check_ok(response: list[str]):
        """Used for basic commands to check that OK was returned. Raises an UnexpectedResultError is not OK."""
        Bearcat.check_response(response, 1)
        if response[0] != 'OK':
            raise UnexpectedResultError(f'Not OK response, "{response[0]}"')

    def execute_action(self, cmd: str):
        """Executes a specified action (no arguments, no response value)."""
        self.check_ok(self.execute_command(cmd))

    def _get_string(self, cmd: str) -> str:
        """Sends a given command expecting a single value in return."""
        response = self.execute_command(cmd)
        self.check_response(response, 1)
        return response[0]

    def get_number(self, cmd: str) -> int:
        """Sends a given command expecting a single integer in return."""
        response = self._get_string(cmd)
        return int(response)

    def set_value(self, cmd: str, value: Union[str, int]):
        """Sends a given command and value as a key-value pair."""
        self.check_ok(self.execute_command(cmd, str(value)))

    def execute_program_mode_command(self, *command: str) -> list[str]:
        """Executes a command and returns the response for commands that require program mode."""
        already_program = self.in_program_mode
        if not already_program:
            self.enter_program_mode()

        response = self.execute_command(*command)

        if not already_program:
            self.exit_program_mode()

        return response

    def get_program_mode_string(self, cmd: str) -> str:
        """Sends a given command expecting a single value in return, for commands that require program mode."""
        response = self.execute_program_mode_command(cmd)
        self.check_response(response, 1)
        return response[0]

    def get_program_mode_number(self, cmd: str) -> int:
        """Sends a given command expecting a single integer in return, for commands that require program mode."""
        response = self.get_program_mode_string(cmd)
        return int(response)

    @staticmethod
    def parse_program_mode_group(states: str) -> list[bool]:
        return [not bool(int(c)) for c in states]

    def get_program_mode_group(self, cmd: str, total_groups: int) -> list[bool]:
        """
        Sends a given command expecting a string representing a list of booleans in return, for commands that require
        program mode.
        """
        response = self.get_program_mode_string(cmd)
        if len(response) != total_groups:
            raise UnexpectedResultError(f'{len(response)} values returned, expected {total_groups}')

        return self.parse_program_mode_group(response)

    def set_program_mode_value(self, cmd: str, value: Union[str, int]):
        """Sends a given command and value as a key-value pair for commands that require program mode."""
        self.check_ok(self.execute_program_mode_command(cmd, str(value)))

    @staticmethod
    def build_program_mode_group(states: list[bool]) -> str:
        return ''.join([str(int(not b)) for b in states])

    def set_program_mode_group(self, cmd: str, states: list[bool], total_groups: int):
        """Sends a given command and string representing a list of booleans, for commands that require program mode."""
        assert len(states) == total_groups, f'Unexpected states length of {len(states)}, expected {total_groups}'
        self.set_program_mode_value(cmd, self.build_program_mode_group(states))

    #
    # Actions
    #

    def enter_program_mode(self):
        """Sends the enter program mode (PRG) command. Required for many commands. Prevents scanner operation."""
        self.execute_action('PRG')
        self.in_program_mode = True

    def exit_program_mode(self):
        """Sends the exit program mode (EPG) command. Resumes normal scanner operation."""
        self.execute_action('EPG')
        self.in_program_mode = False

    #
    # Getters
    #

    def get_model(self) -> str:
        """
        Sends the get model (MDL) command.

        Returns:
            scanner's model number
        """
        return self._get_string('MDL')

    def get_version(self) -> str:
        """
        Sends the get version (VER) command.

        Returns:
            scanner's firmware version number
        """
        return self._get_string('VER')

    def get_global_lockout_freqs(self) -> list[int]:
        """
        Sends the get global lockout freq (GLF) command. Requires program mode.

        Returns:
            a list of all globally locked out frequencies in Hz
        """
        program_mode = self.in_program_mode

        freqs: list[int] = []
        if not program_mode:
            self.enter_program_mode()

        latest = self.get_program_mode_number('GLF')
        while latest != -1:
            freqs.append(latest * self.FREQUENCY_SCALE)
            latest = self.get_program_mode_number('GLF')

        if not program_mode:
            self.exit_program_mode()
        return freqs

    #
    # Program Mode Getters
    #

    def clear_all_memory(self):
        """Sends the clear all memory (CLR) command. Requires program mode. Factory resets the scanner."""
        try:
            self.check_ok(self.execute_program_mode_command('CLR'))
        except UnexpectedResultError:
            print('Somewhat-expected error while clearing')
            while self.in_program_mode:
                try:
                    self.exit_program_mode()
                except UnexpectedResultError:
                    pass

    def get_custom_search_group(self) -> list[bool]:
        """
        Sends the get custom search group (CSG) command. Requires program mode.

        Returns:
            a list of 10 bools representing whether search is enabled for each of the 10 custom groups
        """
        return self.get_program_mode_group('CSG', self.NUM_CUSTOM_SEARCH_GROUPS)

    #
    # Setters
    #

    def unlock_global_lo(self, frequency: int):
        """
        Sends the unlock global lo (ULF) command.

        Args:
            frequency: frequency in Hz to unlock globally
        """
        assert self.MIN_FREQUENCY_HZ <= frequency <= self.MAX_FREQUENCY_HZ,\
            f'Unexpected frequency {frequency}, expected 25 - 512 MHz'
        self.set_program_mode_value('ULF', frequency // self.FREQUENCY_SCALE)

    #
    # Program Mode Setters
    #

    def lock_out_frequency(self, frequency: int):
        """
        Sends the lock out frequency (LOF) command. Requires program mode.

        Args:
            frequency: frequency in Hz to lockout
        """
        assert self.MIN_FREQUENCY_HZ <= frequency <= self.MAX_FREQUENCY_HZ,\
            f'Unexpected frequency {frequency}, expected 25 - 512 MHz'
        self.set_program_mode_value('LOF', frequency // self.FREQUENCY_SCALE)

    def set_custom_search_group(self, states: list[bool]):
        """
        Sends the set custom search group (CSG) command. Requires program mode.

        Args:
            states: list of 10 bools representing which of the 10 custom groups should have search enabled
        """
        self.set_program_mode_group('CSG', states, self.NUM_CUSTOM_SEARCH_GROUPS)
