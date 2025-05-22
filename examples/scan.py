"""Monitors the scanner and records audio on squelch."""
import signal
import warnings
import numpy as np
from sys import argv
from pathlib import Path
from typing import Optional
from threading import Thread
from datetime import datetime
from soundfile import SoundFile
from time import sleep, monotonic
from sounddevice import Stream, query_devices

from bearcat import RadioState, find_scanners, detect_scanner


warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

RECORDING_DIR = Path('/home/liam/workspace/bearcat/recordings')
LOG_FILE = Path('/home/liam/workspace/bearcat/log-DATE.csv')

SAMPLE_RATE = 44100
BLOCK_SIZE = 4096
NUM_CHANNELS = 2
VOCAB = ''

queue = []
running = True

assert len(argv) > 1, "Script requires one argument, the address of the scanner."


class Recording:
    """Object representing a recording."""

    def __init__(self, radio_state: RadioState):
        self.audio_buffer = []
        self.radio_state = radio_state
        self.started_at = datetime.now()
        self.stopped_at: Optional[datetime] = None
        print(self.name, 'started')

    @property
    def is_recording(self):
        """Determines if the recording is running based on whether stop() has been called."""
        return self.stopped_at is None

    @property
    def length(self):
        """Determines the length of the recording based on the start and stop times, stop() must be called first."""
        return (self.stopped_at - self.started_at).total_seconds()

    @property
    def audio_length(self):
        """Determines the length of the recorded audio based on the buffer size."""
        return len(self.audio_buffer) * BLOCK_SIZE / SAMPLE_RATE

    @property
    def name(self):
        """Builds the recording file name using frequency and start time."""
        name = self.radio_state.name.replace(' ', '_') if self.radio_state.name else self.radio_state.frequency / 1e6
        return f'{name}_{self.started_at.strftime("%Y-%m-%d_%H:%M:%S")}.wav'

    def stop(self):
        """Marks the end of the recording."""
        self.stopped_at = datetime.now()
        print(self.name, 'stopped')

    def add_samples(self, samples):
        """Add given samples to the recording."""
        self.audio_buffer.append(samples.copy())


def exit_gracefully(_, __):
    """Handles a keyboard interrupt to shut down the script."""
    global running
    print('Quitting...')
    running = False


def handle_audio(in_data, out_data, __, ___, ____):
    """Callback for handling new audio samples."""
    # if recording, cache samples in recording object
    if queue:
        rec = queue[-1]
        if rec.is_recording or rec.audio_length < rec.length:
            # loopback audio to output device
            out_data[:] = in_data

            rec.add_samples(in_data.copy())
        else:
            out_data[:] = np.zeros(out_data.shape)
    else:
        out_data[:] = np.zeros(out_data.shape)


def process_thread():
    """
    Monitors the recording queue for completed recordings. Saves the recordings to file, then transcribes and logs them.
    """
    global running
    print('Processing thread started')
    while running:
        if queue and not queue[0].is_recording:
            rec = queue.pop(0)

            print(f'Recorded for {rec.length}s, got {rec.audio_length}s')
            name = RECORDING_DIR / rec.name

            if rec.length >= 0.6:
                file = SoundFile(name, mode='w', samplerate=SAMPLE_RATE, channels=NUM_CHANNELS)
                for frame in rec.audio_buffer:
                    file.write(frame)

                print(f'Saved recording {name}')
                with open(str(LOG_FILE).replace('DATE', rec.started_at.strftime('%Y-%m-%d')), 'a') as f:
                    f.write(f'{rec.started_at},{round(rec.length, 1)},{rec.radio_state.name},{rec.radio_state.frequency},{rec.radio_state.modulation.value},{rec.radio_state.tone_code}\n')
                    print('Wrote to log')

        sleep(0.001)


print(query_devices())
in_device = int(input('Desired input device: '))
out_device = int(input('Desired output device: '))
stream = Stream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, device=(in_device, out_device), channels=NUM_CHANNELS,
                callback=handle_audio)
stream.start()
print('Audio stream started')

# find a scanner
bcs = find_scanners()
if len(bcs) == 0:
    print('No scanners found')
    exit(1)
else:
    bc = bcs[0]

signal.signal(signal.SIGINT, exit_gracefully)

Thread(target=process_thread).start()

while running:
    start = monotonic()
    state, squelch, muted = bc.get_reception_status()

    # detect squelch start
    if squelch and not muted and not (queue and queue[-1].is_recording):
        queue.append(Recording(state))
    # detect squelch end
    elif not squelch and (queue and queue[-1].is_recording):
        queue[-1].stop()

    # query every 200 ms
    rem_time = 0.2 - (monotonic() - start) - 0.001
    if rem_time > 0:
        sleep(rem_time)

stream.stop()
stream.close()
