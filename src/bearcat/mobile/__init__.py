"""Contains the class representation of the Uniden BC125AT scanner."""
import abc

from bearcat import BearcatCommon


class BearcatMobile(BearcatCommon, metaclass=abc.ABCMeta):

    #
    # Program Mode Getters
    #

    def get_lcd_upside_down_settings(self) -> bool:
        """
        Sends the get LCD Upside-down Settings (DUD) command. Requires program mode.

        Returns:
            whether the display is upside down as a boolean
        """
        return bool(self._get_program_mode_number('DUD'))

    #
    # Program Mode Setters
    #

    def set_lcd_upside_down_settings(self, upside_down: bool):
        """
        Sends the set LCD Upside-down Settings (DUD) command. Requires program mode.

        Args:
            upside_down: whether the display is upside down as a boolean
        """
        self._set_program_mode_value('DUD', int(upside_down))
