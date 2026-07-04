from time import sleep
from typing import Callable
from threading import Thread
from serial import SerialException
from serial.tools.list_ports import comports

from bearcat import Bearcat
from bearcat.classes import RadioState
from bearcat.exceptions import CommandNotFound, ScannerNotFound, UnexpectedResultError, UnsupportedModel
from bearcat.values import ALL_BAUD_RATES


def _monitor_thread(scanner: Bearcat, callback: Callable[[RadioState, bool], bool]):
    """Thread which monitors the given scanner and triggers the given callback on squelch."""
    running = True
    receiving = RadioState()
    squelched = False
    while running:
        state, squelch, mute = scanner.get_reception_status()

        if squelch != squelched:
            squelched = squelch
            if squelched:
                receiving = state

            running = callback(receiving, squelched)
            if not squelched:
                receiving = None

        sleep(0.001)


def on_squelch(scanner: Bearcat, callback: Callable[[RadioState, bool], bool]):
    """
    Starts a thread which monitors the given scanner and triggers the given callback on squelch.

    Args:
        scanner: scanner to monitor for squelch
        callback: function to call when a squelch occurs or ends
    """
    Thread(target=_monitor_thread, args=(scanner, callback)).start()


def find_scanners() -> list[Bearcat]:
    """
    Scans serial ports for connected scanners.

    Returns:
        list of all available scanners as their respective objects
    """
    scanners: list[Bearcat] = []
    ports = [p.device for p in comports() if p.description != 'n/a']
    for port in ports:
        scanner = detect_scanner(port)
        if scanner:
            scanners.append(scanner)

    return scanners


def detect_scanner(port: str = '') -> Bearcat:
    """
    Detects a scanner on a given serial port (or IP address).

    Args:
        port: serial port path

    Returns:
        object representing the scanner at the given port
    """
    if port:
        for rate in ALL_BAUD_RATES:
            try:
                # attempt to connect to the scanner
                bc = Bearcat(port, rate)
                try:
                    model = bc.get_model()
                except CommandNotFound:
                    # command not found probably means there is garbage in the buffer, try again
                    model = bc.get_model()

                version = bc.get_version()
            except SerialException as e:
                if e.errno == 13:
                    print('Insignificant permissions for', port)

                break
            except UnexpectedResultError:
                continue

            # construct an object based on the discovered scanner
            scanner = construct_scanner(model, port, rate)
            print(f'Found {model} ({version}): {port} @ {rate}')
            return scanner
        
        raise ScannerNotFound
    else:
        scanners = find_scanners()
        if len(scanners) == 0:
            raise ScannerNotFound
        else:
            return scanners[0]


def construct_scanner(model: str, port: str, rate: int = -1) -> Bearcat:
    """
    Constructs a scanner object based on the given model.

    Args:
        model: desired model name
        port: serial port path
        rate: optional desired baud rate

    Returns:
        object representing the requested scanner using the specified type
    """
    from bearcat.scanners import SCANNERS
    for scanner in SCANNERS:
        if model == scanner.MODEL:
            return scanner(port, rate)

    raise UnsupportedModel
