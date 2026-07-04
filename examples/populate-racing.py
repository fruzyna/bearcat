"""Populate a BC125AT banks with channels from a CSV file."""
from sys import argv
from pathlib import Path

from bearcat.classes import Modulation, Channel
from bearcat.tools import detect_scanner


# filters to select channels by using the first column
SELECT_FROM = ['NASCAR', 'CUP', 'OAPS', 'ARCA']
FILE_DIR = Path('/channels')

# find a scanner either from a given address or scanning
port = argv[1] if len(argv) > 1 else ''
bc = detect_scanner(port)

count = 0
groups = {}
last_section = ''
total_channels = bc.TOTAL_CHANNELS
band_size = total_channels // 10
for file in FILE_DIR.glob('*.csv'):
    with open(file, 'r') as f:
        # skip the first line of the file
        sline = f.readline()

        while sline:
            sline = f.readline()
            line = [c.strip() for c in sline.strip().strip(',').split(',')]

            # ignore unpopulated lines

            if len(line) >= 4 and line[0]:
                section = line[0]
                number = line[1]
                last_name = line[2]
                first_name = line[3]

                # combine last and first name
                if not last_name:
                    name = section
                else:
                    name = last_name
                    if first_name:
                        name += f' {first_name}'

                # skip sections not in SELECT_FROM
                if SELECT_FROM and section not in SELECT_FROM:
                    continue

                for i in range(4, len(line), 2):
                    index = (i - 2) // 2
                    frequency = line[i]
                    tone = line[i + 1] if len(line) > i + 1 else 'Search'

                    # if no name was provided use section name
                    if not name:
                        name = section

                    # by default channels are named "NAME NUMBER-INDEX"
                    if not number:
                        number_str = ''
                    elif len(line) < 7:
                        number_str = f' {number}'
                    else:
                        number_str = f' {number}-{index}'

                    # fill remaining space with name
                    name_len = 16 - len(number_str)
                    name = name[:min(name_len, len(name))].ljust(name_len)
                    chan_name = name + number_str

                    # expects CTCSS/DCS frequency/codes
                    try:
                        tone = float(tone)
                    except ValueError:
                        tone = tone.upper()
                        if not tone:
                            tone = 'SEARCH'

                    # build channel index
                    count += 1
                    channel = Channel(count, chan_name, int(float(frequency) * 1e6), Modulation.NFM, bc.TONE_MAP[tone], lockout=False)

                    group = f'{section}-{index}' if number else section
                    if group not in groups:
                        groups[group] = {}

                    groups[group][number if number else count] = channel

channels = {}
channel_num = 0
for group, numbers in groups.items():
    # determine if all numbers are unique numbers
    numbered = True
    raw_numbers = []
    for number, channel in numbers.items():
        try:
            raw_numbers.append(int(number))
        except ValueError:
            if len(number) > 1:
                try:
                    raw_numbers.append(int(number[1:]))
                except ValueError:
                    numbered = False
            else:
                numbered = False

    if numbered and len(list(set(raw_numbers))) != len(raw_numbers):
        numbered = False

    # renumber channels in each group
    base = channel_num
    for number, channel in numbers.items():
        if numbered and (group.startswith('CUP') or group.startswith('INDY')):
            if number in ['0', 'O0']:
                channel_num = base + 100
            else:
                try:
                    channel_num = base + int(number) % 100
                except ValueError:
                    channel_num = base + int(number[1:]) % 100
        else:
            channel_num += 1

        channel.index = channel_num
        channels[channel_num] = channel

    # jump to start of next group
    channel_num = (channel_num // band_size + 1) * band_size

# init scanner connection
bc.enter_program_mode()

# add all new channels, delete others
for i in range(1, total_channels + 1):
    if i in channels:
        print(channels[i])
        bc.update_channel(channels[i])
    else:
        bc.clear_channel(i)

bc.exit_program_mode()
