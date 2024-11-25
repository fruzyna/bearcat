"""Reads a BC125AT scanner's channel bank configuration."""
from bearcat.bc125at import BC125AT

CHANNEL_FILE = 'backup.csv'

bc = BC125AT('/dev/ttyACM0')
tones = list(BC125AT.TONE_MAP.keys())
tone_codes = list(BC125AT.TONE_MAP.values())

with open(CHANNEL_FILE, 'w') as f:
    f.write('Group,Number,Index,Name,Secondary Name,Frequency (MHz),Tone,Modulation\n')
    for i in range(bc.TOTAL_CHANNELS):
        chan = bc.get_channel_info(i + 1)
        if chan.frequency:
            print(chan)
            tone = tones[tone_codes.index(chan.tone_code)]
            f.write(f'IMPORT,,,{chan.name},,{chan.frequency / 1e6},{tone},{chan.modulation.value}\n')
