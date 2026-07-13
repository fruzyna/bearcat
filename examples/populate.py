"""Populate a BC125AT banks with channels from a CSV file."""
from sys import argv
from pathlib import Path

from bearcat.classes import Modulation, Channel
from bearcat.tools import detect_scanner


# filters to select channels by using the first column
SELECT_FROM = ['NWS', 'UNION', 'LINCOLN', 'BOREALIS']
FILE_DIR = Path('/channels')

# find a scanner either from a given address or scanning
port = argv[1] if len(argv) > 1 else ''
bc = detect_scanner(port)

i = 0
chans = {}
last_section = ''
total_channels = bc.TOTAL_CHANNELS
band_size = total_channels // 10
for file in FILE_DIR.glob('*.csv'):
    with open(file, 'r') as f:
        # skip the first line of the file
        sline = f.readline()

        while sline:
            sline = f.readline()
            line = [c.strip() for c in sline.split(',')]

            # ignore unpopulated lines
            if len(line) >= 3 and line[0] and line[2]:
                section = line[0]
                name = line[1]
                frequency = line[2]
                tone = line[3]
                modulation = line[4] if len(line) > 3 else ''

                # skip sections not in SELECT_FROM
                if SELECT_FROM and section not in SELECT_FROM:
                    continue

                # detect section changes, go to next bank
                if section != last_section:
                    if last_section:
                        i += band_size - i % band_size

                    last_section = section

                # increment channel number, prevent exceeding last channel
                i += 1
                if i > total_channels:
                    break

                # if no name was provided use section name
                if not name:
                    name = section

                name = name[:min(16, len(name))].ljust(16)

                # expects CTCSS/DCS frequency/codes
                try:
                    tone = float(tone)
                except ValueError:
                    tone = tone.upper()

                mod = Modulation.NFM
                if modulation:
                    mod = Modulation(modulation.upper())

                chan = Channel(i, name, int(float(frequency) * 1e6), mod, bc.TONE_MAP[tone], lockout=False)
                print(chan)
                chans[i - 1] = chan

# init scanner connection
bc.enter_program_mode()

# add all new channels, delete others
for i in range(total_channels):
    if i in chans:
        bc.update_channel(chans[i])
    else:
        bc.clear_channel(i + 1)

bc.exit_program_mode()
