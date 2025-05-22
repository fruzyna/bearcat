"""Monitors the scanner, records audio on squelch, and transcribes the audio."""
import signal
import warnings
from time import sleep
from sounddevice import Stream, query_devices


warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

SAMPLE_RATE = 44100
BLOCK_SIZE = 4096
NUM_CHANNELS = 4

running = True

def exit_gracefully(_, __):
    """Handles a keyboard interrupt to shut down the script."""
    global running
    print('Quitting...')
    running = False


def handle_audio(in_data, out_data, __, ___, ____):
    """Callback for handling new audio samples."""
    # if recording, cache samples in recording object
    out_data[:] = in_data[:, 0:1]


print(query_devices())
in_device = int(input('Desired input device: '))
out_device = int(input('Desired output device: '))
stream = Stream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, device=(in_device, out_device), channels=(NUM_CHANNELS, 1),
                callback=handle_audio)
stream.start()
print('Audio stream started')

signal.signal(signal.SIGINT, exit_gracefully)

while running:
    sleep(1)

stream.stop()
stream.close()
