"""Contains classes commonly used between scanner models."""
from enum import Enum


class Screen:
    """Representation of the scanner's screen, composed of a list of lines."""

    class Line:
        """Representation of a single line on the scanner's screen."""

        def __init__(self, text: str, formatting: str, large: bool):
            self.text = text
            self.formatting = formatting
            self.large = large

        def __str__(self) -> str:
            """Apply formatting on the line's string."""
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

            return text

    def __init__(self, *args: str):
        """
        Constructor, designed to directly take the response to the STS command. Uses the first argument to determine the
        number of lines to produce, then the following pairs are each line and its formatting.
        """
        self.lines = [Screen.Line(args[1 + i * 2], args[2 + i * 2], bool(int(c))) for i, c in enumerate(args[0])]

    def __str__(self) -> str:
        """Join each line's string as a new line."""
        return '\n'.join([str(l) for l in self.lines])


class Modulation(Enum):
    """Enumeration of modulations available to Uniden scanners. Not all scanners support all modulations."""
    AUTO = 'AUTO'
    AM = 'AM'
    FM = 'FM'
    NFM = 'NFM'


class RadioState:
    """Object representation of radio state returned by both GLG and CIN commands."""

    def __init__(self, index: int = -1, name: str = '', frequency: int = 0, modulation: Modulation = Modulation.NFM, tone_code: int = 0):
        """
        Args:
            index: channel number (1 - 500)
            name: name of the selected channel, may be blank, must be <= 16 characters
            frequency: channel frequency in Hz
            modulation: modulation type
            tone_code: optional CTCSS/DCS code identifier, see TONE_MAP values
        """
        self.index = index
        self.name = name
        self.frequency = frequency
        self.modulation = modulation
        self.tone_code = tone_code

    def __str__(self) -> str:
        return f'{self.index}: "{self.name}" {self.frequency / 1e6} MHz {self.modulation.value} {self.tone_code}'


class Channel(RadioState):
    """Object representation of radio state used with CIN command."""

    def __init__(self, index: int = -1, name: str = '', frequency: int = 0, modulation: Modulation = Modulation.NFM, tone_code: int = 0,
                 delay: str = '2', lockout: bool = True, priority: bool = False):
        """
        Args:
            index: channel number (1-500)
            name: name of the selected channel, may be blank, must be <= 16 characters
            frequency: channel frequency in Hz
            modulation: modulation type
            tone_code: optional CTCSS/DCS code identifier, see TONE_MAP values
            delay: optional delay, default TWO
            lockout: optional channel lockout (removal from scan), default True
            priority: optional channel priority (one per bank), default False
        """
        super().__init__(index, name, frequency, modulation, tone_code)
        self.index = index
        self.delay = delay
        self.lockout = lockout
        self.priority = priority

    def __str__(self) -> str:
        locked = 'Locked' if self.lockout else 'Unlocked'
        priority = ' Priority' if self.priority else ''
        return f'{super().__str__()} {self.delay}s {locked}{priority}'
