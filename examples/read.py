"""Reads a BC125AT scanner's channel bank configuration."""
from sys import argv

from bearcat.tools import detect_scanner
from bearcat.classes import Channel


CHANNEL_FILE = 'backup.csv'

# find a scanner either from a given address or scanning
port = argv[1] if len(argv) > 1 else ''
bc = detect_scanner(port)

tones = list(bc.TONE_MAP.keys())
tone_codes = list(bc.TONE_MAP.values())

bc.enter_program_mode()
with open(CHANNEL_FILE, 'w') as f:
    f.write('Group,Number,Index,Name,Secondary Name,Frequency (MHz),Tone,Modulation\n')
    for i in range(bc.TOTAL_CHANNELS):
        chan: Channel = bc.get_channel_info(i + 1)
        if chan.frequency:
            print(chan)
            tone = tones[tone_codes.index(chan.tone_code)]
            f.write(f'IMPORT,,{chan.index},{chan.name},,{chan.frequency / 1e6},{chan.tone_code},{chan.modulation.value}\n')

bc.exit_program_mode()
