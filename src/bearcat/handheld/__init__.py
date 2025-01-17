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
