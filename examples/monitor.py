"""Monitors a BC125AT scanner. Emulates the screen in the console and logs received transmissions to file."""
import signal
from sys import argv
from time import sleep
from datetime import datetime

from bearcat.tools import detect_scanner
from bearcat.scanners.bc125at import BC125AT

LOG_FILE = 'log.csv'

running = True


def exit_gracefully(sig_num, frame):
    """Handles a keyboard interrupt to shut down the script."""
    global running
    print('Quitting...')
    running = False


# find a scanner either from a given address or scanning
port = argv[1] if len(argv) > 1 else ''
bc = detect_scanner(port)

signal.signal(signal.SIGINT, exit_gracefully)

# print screen once, future prints will overlap this one
screen = bc.get_status()[0]
print(screen)
last_line_count = len(screen.lines)

started_at = 0
receiving = None
while running:
    # print the screen on top of previous prints
    screen, squelch, _ = bc.get_status()
    print(f'\033[{last_line_count}F' + str(screen))
    last_line_count = len(screen.lines)

    # detect squelch start
    if squelch and not receiving:
        started_at = datetime.now()
        receiving, _, _ = bc.get_reception_status()
    # detect squelch end
    elif not squelch and receiving:
        length = (datetime.now() - started_at).total_seconds(0)
        if length > 0.5:
            with open(LOG_FILE, 'a') as f:
                f.write(f'{started_at},{round(length, 1)},{receiving.name},{receiving.frequency},{receiving.modulation.value},{receiving.tone_code}\n')

        receiving = None

    sleep(0.001)
