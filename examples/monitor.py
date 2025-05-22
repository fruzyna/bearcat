"""Monitors a BC125AT scanner. Emulates the screen in the console and logs received transmissions to file."""
import signal
from sys import argv
from time import sleep
from datetime import datetime

from bearcat import find_scanners, detect_scanner

LOG_FILE = 'log.csv'

running = True


def exit_gracefully(_, __):
    """Handles a keyboard interrupt to shut down the script."""
    global running
    print('Quitting...')
    running = False


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

signal.signal(signal.SIGINT, exit_gracefully)

# print screen once, future prints will overlap this one
screen, squelch, mute = bc.get_status()
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
        length = (datetime.now() - started_at).total_seconds()
        if length > 0.5:
            with open(LOG_FILE, 'a') as f:
                f.write(f'{started_at},{round(length, 1)},{receiving.name},{receiving.frequency},{receiving.modulation.value},{receiving.tone_code}\n')

        receiving = None

    sleep(0.001)
