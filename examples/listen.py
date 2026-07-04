"""Monitors the scanner, records audio on squelch, and transcribes the audio."""
import signal
import warnings

from sys import argv
from time import sleep
from sounddevice import Stream, query_devices

from bearcat.classes import RadioState
from bearcat.tools import detect_scanner, on_squelch

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

SAMPLE_RATE = 48000
BLOCK_SIZE = 4096
NUM_CHANNELS = 4

running = True

def exit_gracefully(sig_num, frame):
    """Handles a keyboard interrupt to shut down the script."""
    global running
    print('Quitting...')
    running = False


def handle_audio(in_data, out_data, frames, time, status):
    """Callback for handling new audio samples."""
    # if recording, cache samples in recording object
    out_data[:] = in_data[:, 0:1]


def handle_squelch(state: RadioState, squelched: bool) -> bool:
    if squelched:
        print(state)

    return running


print(query_devices())
in_device = int(input('Desired input device: '))
out_device = int(input('Desired output device: '))
stream = Stream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, device=(in_device), channels=(NUM_CHANNELS),
                callback=handle_audio)
stream.start()
print('Audio stream started')

signal.signal(signal.SIGINT, exit_gracefully)

port = argv[1] if len(argv) > 1 else ''
bc = detect_scanner(port)
on_squelch(bc, handle_squelch)

while running:
    sleep(1)

stream.stop()
stream.close()
