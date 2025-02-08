"""Contains classes that are applicable to most if not all known handheld Uniden scanners."""
import abc
from enum import Enum

from bearcat import BearcatBase


class BearcatHandheld(BearcatBase, metaclass=abc.ABCMeta):
    """Object that represents API calls available to all handheld Uniden Bearcat scanners."""

    #
    # Actions
    #

    def power_off(self):
        """Sends the power off (POF) command. This is an unofficial command for the BC125AT."""
        self._execute_action('POF')

    #
    # Getters
    #

    def get_battery_voltage(self) -> float:
        """
        Sends the get battery voltage (BAV) command. This is an unofficial command for the BC125AT.

        Returns:
            battery potential in volts
        """
        return self._get_number('BAV') * 6.4 / 1023


class BearcatHandheldClassic(BearcatHandheld, metaclass=abc.ABCMeta):
    """Object that represents API calls available to "classic" (pre-2012) Uniden scanners."""

    class BacklightMode(Enum):
        """Enumeration of backlight modes supported by most classic handheld Uniden scanners."""
        INFINITE = 'IF'
        SECONDS_10 = '10'
        SECONDS_30 = '30'
        KEYPRESS = 'KY'
        SQUELCH = 'SQ'

    #
    # Program Mode Actions
    #

    def copy_system(self, source_index: int, copy_name: str) -> int:
        """
        Sends the Copy System (CPS) command. Requires program mode.

        Args:
            source_index: index of the system to copy
            copy_name: name of the new copied system

        Returns:
            index of the new copied system
        """
        response = self._execute_program_mode_command('CPS', str(source_index), copy_name)
        self._check_response(response, 1)
        return int(response[0])

    #
    # Getters
    #

    def get_backlight(self) -> BacklightMode:
        """
        Sends the get backlight (BLT) command. Requires program mode.

        Returns:
            backlight mode as an enumeration
        """
        return self.BacklightMode(self._get_program_mode_string('BLT'))

    #
    # Program Mode Getters
    #

    def get_battery_save(self) -> bool:
        """
        Sends the get Battery Save (BSV) command. Requires program mode.

        Returns:
            whether to enable battery save as a boolean
        """
        return bool(self._get_program_mode_number('BSV'))

    #
    # Setters
    #

    def set_backlight(self, mode: BacklightMode):
        """
        Sends the set backlight (BLT) command. Requires program mode.

        Args:
            mode: enumeration of the desired backlight mode
        """
        self._set_program_mode_value('BLT', mode.value)

    #
    # Program Mode Setters
    #

    def set_battery_save(self, enable: bool):
        """
        Sends the set Battery Save (BSV) command. Requires program mode.

        Args:
            enable: whether to enable battery save as a boolean
        """
        self._set_program_mode_value('BSV', int(enable))
