"""Monitors the scanner, records audio on squelch, and transcribes the audio."""
from bearcat.bc125at import BC125AT

import signal
import whisper
from pathlib import Path
from soundfile import SoundFile
from sounddevice import InputStream
from typing import Optional
from time import sleep
from datetime import datetime
from threading import Thread
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

RECORDING_DIR = Path('recordings')
LOG_FILE = Path('log.csv')

SAMPLE_RATE = 44100
BLOCK_SIZE = 4096
NUM_CHANNELS = 2
VOCAB = 'DEVAL, UP, CN, CPKC, Metra, Des Plaines, Bensonville, Bensonville Tower, Galewood, Elgin'

queue = []
running = True

class Recording:
    """Object representing a recording."""

    def __init__(self, radio_state: BC125AT.RadioState):
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


def handle_audio(in_data, _, __, ___):
    """Callback for handling new audio samples."""
    if queue:
        rec = queue[-1]
        if rec.is_recording or rec.audio_length < rec.length:
            rec.add_samples(in_data.copy())


def process_thread():
    """
    Monitors the recording queue for completed recordings. Saves the recordings to file, transcibes them, and logs them.
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

                print(f'Saved recording {name}, transcribing...')
                text = ''
                try:
                    transcription = model.transcribe(str(name), initial_prompt=VOCAB)
                    text = transcription['text']
                    print('Heard:', text)
                    if any(ord(c) > 128 for c in text) or transcription['language'] != 'en':
                        text = ''
                        print('Threw out transcription')
                except KeyError:
                    print('KeyError transcribing')
                except RuntimeError:
                    print('RuntimeError transcribing')

                if text:
                    with open(LOG_FILE, 'a') as f:
                        f.write(f'{rec.started_at},{round(rec.length, 1)},{rec.radio_state.name},{rec.radio_state.frequency},{rec.radio_state.modulation.value},{rec.radio_state.tone_code},"{text}"\n')
                        print('Wrote to log')

        sleep(0.001)


model = whisper.load_model('turbo')
print('Whisper model loaded')

bc = BC125AT('/dev/ttyACM0')
bc.listen()
print('BC125AT started')

stream = InputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, device=8, channels=NUM_CHANNELS,
                     callback=handle_audio)
stream.start()
print('Audio stream started')

signal.signal(signal.SIGINT, exit_gracefully)

Thread(target=process_thread).start()

while running:
    state, squelch, _ = bc.get_reception_status()

    # detect squelch start
    if squelch and not (queue and queue[-1].is_recording):
        queue.append(Recording(state))
    # detect squelch end
    elif not squelch and (queue and queue[-1].is_recording):
        queue[-1].stop()

    sleep(0.001)

stream.stop()
stream.close()
