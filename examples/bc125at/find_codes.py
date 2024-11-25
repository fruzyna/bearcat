"""Attempts all possible commands to find which commands are supported by the BC125AT."""
from bearcat import CommandNotFound, CommandInvalid, UnexpectedResultError
from bearcat.bc125at import BC125AT

from itertools import product
from string import ascii_uppercase

CHANNEL_FILE = 'backup.csv'

bc = BC125AT('/dev/ttyACM0')

# attempt every command possible from AAA to ZZZ
for x in range(3, 4):
    for c in product(ascii_uppercase, repeat=x):
        cmd = ''.join(c)
        # skip known dangerous commands
        if cmd in ['CLR', 'EPG', 'POF', 'PRG']:
            print('Known:', cmd)
            continue

        try:
            bc._execute_command(cmd)
            print('Valid:', cmd)
        except CommandNotFound:
            continue
        except CommandInvalid:
            print('Invalid:', cmd)
        except UnexpectedResultError:
            print('No result:', cmd)
