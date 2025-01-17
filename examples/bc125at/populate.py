"""Populate a BC125AT banks with channels from a CSV file."""
from sys import argv

from bearcat import Modulation
from bearcat.handheld.bc125at import BC125AT


# filters to select channels by using the first column
SELECT_FROM = ['RAIL', 'LOCAL', 'ATIS', 'ORD APP', 'ORD DPRT', 'ORD GND', 'ORD RAMP', 'ORD OTHER', 'PWK']
CHANNEL_FILE = '/run/user/1000/gvfs/smb-share:server=rossy.local,share=archive/Documents/Scanner/raw-channels.csv'

assert len(argv) > 1, "Script requires one argument, the address of the scanner."

i = 0
chans = {}
last_section = ''
with open(CHANNEL_FILE, 'r') as f:
    # skip the first line of the file
    sline = f.readline()

    while sline:
        sline = f.readline()
        line = [c.strip() for c in sline.split(',')]

        # ignore unpopulated lines
        if len(line) >= 7 and line[0] and line[5]:
            section = line[0]
            number = line[1]
            index = line[2]
            name = line[3]
            secondary_name = line[4]
            frequency = line[5]
            tone = line[6]
            modulation = line[7] if len(line) > 7 else ''

            # skip sections not in SELECT_FROM
            if SELECT_FROM and section not in SELECT_FROM:
                continue

            # detect section changes, go to next bank
            if section != last_section:
                if last_section:
                    i += 50 - i % 50

                last_section = section

            # increment channel number, prevent exceeding last channel
            i += 1
            if i > BC125AT.TOTAL_CHANNELS:
                break

            # if no name was provided use section name
            if not name:
                name = section

            # by default channels are named "NAME NUMBER-INDEX" so name is limited to 11 characters
            name_len = 11
            number_str = f' {number.rjust(2)}'
            index_str = f'-{index}'
            # if no index, increase limit to 13
            if not index:
                name_len += 2
                index_str = ''
                # if no number, allow full 16 characters to be used
                if not number:
                    name_len = 16
                    number_str = ''

            name = name[:min(name_len, len(name))].ljust(name_len)
            chan_name = f'{name}{number_str}{index_str}'

            # expects CTCSS/DCS frequency/codes
            try:
                tone = float(tone)
            except ValueError:
                tone = tone.upper()

            mod = Modulation.NFM
            if modulation:
                mod = Modulation(modulation.upper())

            chan = BC125AT.Channel(i, chan_name, int(float(frequency) * 1e6), mod, tone, lockout=False)
            print(chan)
            chans[i - 1] = chan

# init scanner connection
bc = BC125AT(argv[1])
bc.enter_program_mode()

# add all new channels, delete others
for i in range(BC125AT.TOTAL_CHANNELS):
    if i in chans:
        bc.update_channel(chans[i])
    else:
        bc.clear_channel(i + 1)

bc.exit_program_mode()
