"""Contains classes that are universally applicable to all known Uniden scanners."""
from enum import Enum


class Modulation(Enum):
    """Enumeration of modulations available to Uniden scanners. Not all scanners support all modulations."""
    AUTO = 'AUTO'
    AM = 'AM'
    FM = 'FM'
    NFM = 'NFM'


class KeyAction(Enum):
    """Enumeration of possible keypad actions."""
    PRESS = 'P'
    LONG_PRESS = 'L'
    HOLD = 'H'
    RELEASE = 'R'


class DelayTime(Enum):
    """Enumeration of allowed delay times."""
    MINUS_TEN = '-10'
    MINUS_FIVE = '-5'
    ZERO = '0'
    ONE = '1'
    TWO = '2'
    THREE = '3'
    FOUR = '4'
    FIVE = '5'


class UnexpectedResultError(Exception):
    """Exception raised when a command does not return an expected result."""
    pass


class Screen:
    """Representation of the scanner's screen, composed of a list of lines."""

    class Line:
        """Representation of a single line on the scanner's screen."""

        def __init__(self, text: str, formatting: str, large: bool):
            self.text = text
            self.formatting = formatting
            self.large = large

        def __str__(self) -> str:
            """Apply formatting and character replacement on the line's string."""
            text = self.text

            # underline characters instead of inverting the colors
            underline = False
            for i, c in enumerate(self.formatting):
                if c == '*' and not underline:
                    text = text[:i] + '\033[4m' + text[i:]
                    underline = True
                elif c != '*' and underline:
                    text = text[:i+1] + '\033[0m' + text[i+1:]
                    underline = False

            if underline:
                text += '\033[0m'

            # replace ASCII placeholder characters with UNICODE versions
            return text.replace('|^', '↑').replace('|v', '↓').replace('=', '■')

    def __init__(self, *args):
        """
        Constructor, designed to directly take the response to the STS command. Uses the first argument to determine the
        number of lines to produce, then the following pairs are each line and its formatting.
        """
        self.lines = [Screen.Line(args[1 + i * 2], args[2 + i * 2], bool(int(c))) for i, c in enumerate(args[0])]

    def __str__(self) -> str:
        """Join each line's string as a new line."""
        return '\n'.join([str(l) for l in self.lines])
