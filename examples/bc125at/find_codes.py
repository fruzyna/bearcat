"""Attempts all possible commands to find which commands are supported by the BC125AT."""
from sys import argv
from itertools import product
from string import ascii_uppercase

from bearcat import CommandNotFound, CommandInvalid, UnexpectedResultError
from bearcat.handheld.bc125at import BC125AT


CHANNEL_FILE = 'backup.csv'

assert len(argv) > 1, "Script requires one argument, the address of the scanner."

bc = BC125AT(argv[1])

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
