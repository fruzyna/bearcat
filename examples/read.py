"""Reads a BC125AT scanner's channel bank configuration."""
from sys import argv

from bearcat import find_scanners, detect_scanner


CHANNEL_FILE = 'backup.csv'

# find a scanner either from a given address or scanning
if len(argv) > 1:
    bc = detect_scanner(argv[1])
else:
    scanners = find_scanners()
    if len(scanners) == 0:
        print('No scanners found')
        exit(1)
    else:
        bc = scanners[0]

tones = list(bc.TONE_MAP.keys())
tone_codes = list(bc.TONE_MAP.values())

bc.enter_program_mode()
with open(CHANNEL_FILE, 'w') as f:
    f.write('Group,Number,Index,Name,Secondary Name,Frequency (MHz),Tone,Modulation\n')
    for i in range(bc.TOTAL_CHANNELS):
        chan = bc.get_channel_info(i + 1)
        if chan.frequency:
            print(chan)
            tone = tones[tone_codes.index(chan.tone_code)]
            f.write(f'IMPORT,,,,,{chan.frequency / 1e6},,\n')

bc.exit_program_mode()
