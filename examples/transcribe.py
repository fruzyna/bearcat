"""Monitors the scanner, records audio on squelch, and transcribes the audio."""
import signal
#import whisper
import warnings
import numpy as np
from typing import List
from pathlib import Path
from threading import Thread
from datetime import datetime
from soundfile import SoundFile
from time import sleep, monotonic
from sounddevice import Stream, query_devices

from bearcat import RadioState, find_scanners, detect_scanner


warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

RECORDING_DIR = Path('/home/liam/bearcat/recordings')
LOG_DIR = Path('/home/liam/bearcat/logs')

SAMPLE_RATE_HZ = 48000
BLOCK_SIZE_S = 0.1
NUM_STREAMS = 4
ALLOWED_GAP = 4
DTYPE = np.float32
MONITOR = True

BLOCK_SIZE = int(SAMPLE_RATE_HZ * BLOCK_SIZE_S // NUM_STREAMS * NUM_STREAMS)


class Recorder:

    def __init__(self, channel: int, state: RadioState):
        self.radio_index = channel
        self.radio_state = state
        self.buffer = np.array([], dtype=DTYPE)
        self.start_time = datetime.now()
        self.stopped_at = 0
        print(f'starting {self.radio_index}: {self.short_state}')

    def add_samples(self, samples):
        self.buffer = np.concatenate((self.buffer, samples[:, self.radio_index].copy()))

    def compare_state(self, state: RadioState) -> bool:
        return state.frequency == self.radio_state.frequency

    @property
    def audio(self) -> np.ndarray:
        if self.is_recording:
            return self.buffer
        else:
            return self.buffer[:-SAMPLE_RATE_HZ * ALLOWED_GAP]

    @property
    def duration(self) -> float:
        return len(self.audio) / SAMPLE_RATE_HZ

    @property
    def is_recording(self) -> bool:
        return not self.is_stopped or len(self.buffer) - self.stopped_at < ALLOWED_GAP * SAMPLE_RATE_HZ

    @property
    def is_stopped(self) -> bool:
        return self.stopped_at > 0

    @property
    def name(self) -> str:
        return f'{self.start_time.strftime("%y%m%d-%H%M%S")} {self.short_state}.wav'

    @property
    def short_state(self) -> str:
        return f"{self.radio_state.frequency / 1e6} {self.radio_state.name}"

    def stop(self):
        print(f'stopping {self.radio_index}: {self.short_state}')
        self.stopped_at = len(self.buffer)

    def resume(self):
        print(f'resuming {self.radio_index}: {self.short_state}')
        self.stopped_at = 0


def exit_gracefully(_, __):
    """Handles a keyboard interrupt to shut down the script."""
    global running
    print('Quitting...')
    running = False


def audio_handler(in_data, out_data, __, ___, ____):
    """Callback for handling new audio samples."""
    # loopback audio to output device
    if MONITOR:
        out_data[:] = np.mean(in_data, 1, keepdims=True) * len(squelched)

    recs = {}
    for r in recorders:
        if r.is_recording and r.radio_index not in recs:
            recs[r.radio_index] = r

    for i, sq in enumerate(squelched):
        if sq and (i not in recs or not recs[i].compare_state(sq)):
            if i in recs and not recs[i].is_stopped:
                recs[i].stop()

            rec = Recorder(i, sq)
            rec.add_samples(in_data)
            recorders.insert(0, rec)
        else:
            if sq and i in recs and recs[i].compare_state(sq) and recs[i].is_stopped:
                recs[i].resume()
            elif not sq and i in recs and not recs[i].is_stopped:
                recs[i].stop()

            if i in recs and recs[i].is_recording:
                recs[i].add_samples(in_data)


def process_thread():
    """
    Monitors the recording queue for completed recordings. Saves the recordings to file, then transcribes and logs them.
    """
    global running
    print('Processing thread started')
    while running:
        completed = [i for i, rec in enumerate(recorders) if not rec.is_recording]
        if completed:
            rec = recorders.pop(completed[-1])
            print(f'Recorded for {rec.duration}s')
            name = RECORDING_DIR / rec.name

            text = ''
            if rec.duration >= 1.0:
                with SoundFile(name, mode='w', samplerate=SAMPLE_RATE_HZ, channels=1) as f:
                    f.write(rec.audio)

                print(f'Saved recording {name}, transcribing...')
                # try:
                #     transcription_start = monotonic()
                #     transcription = model.transcribe(str(name), initial_prompt='')
                #     transcribe_time = monotonic() - transcription_start
                #     transcription_ratio = transcribe_time / rec.duration
                #
                #     text = transcription['text']
                #     words_per_second = len(text.split()) / rec.duration
                #     print('Heard:', text, f'({words_per_second} wps, {transcription_ratio})')
                #
                #     if any(ord(c) > 128 for c in text):
                #         text = ''
                #         print('Threw out transcription, non-english character')
                #     elif transcription['language'] != 'en':
                #         text = ''
                #         print('Threw out transcription, not english')
                #     elif words_per_second > 5:
                #         text = ''
                #         print('Threw out transcription, too wordy')
                #     elif transcription_ratio > 30:
                #         text = ''
                #         print('Threw out transcription, took too long')
                #     elif len(text) < 15 and 'thank you' in text.lower():
                #         print('Threw out transcription, "thank you"')
                # except KeyError:
                #     print('KeyError transcribing')
                # except RuntimeError:
                #     print('RuntimeError transcribing')

            with open(LOG_DIR / f"{rec.start_time.strftime('%Y-%m-%d')}.csv", 'a') as f:
                f.write(f'{rec.start_time},{round(rec.duration, 1)},{rec.radio_state.name},{rec.radio_state.frequency},{rec.radio_state.modulation.value},{rec.radio_state.tone_code},"{text}"\n')
                print('Wrote to log')

        sleep(0.1)


squelched = [False] * NUM_STREAMS
recorders: List[Recorder] = []
running = True

print(query_devices())
in_device = int(input('Desired input device: '))
out_device = int(input('Desired output device: '))
stream = Stream(SAMPLE_RATE_HZ, BLOCK_SIZE, (in_device, out_device), (NUM_STREAMS, 1), DTYPE, callback=audio_handler)
stream.start()
print('Audio stream started')

#model = whisper.load_model('turbo')
#print('Whisper model loaded')

# find a scanner
bcs = find_scanners()
if len(bcs) == 0:
    print('No scanners found')
    exit(1)

signal.signal(signal.SIGINT, exit_gracefully)

Thread(target=process_thread).start()

while running:
    start = monotonic()

    for i, bc in enumerate(bcs):
        state, squelch, muted = bc.get_reception_status()
        squelched[i] = state if squelch else False

    # query every 200 ms
    rem_time = 0.2 - (monotonic() - start) - 0.001
    if rem_time > 0:
        sleep(rem_time)

stream.stop()
stream.close()
