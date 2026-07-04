from time import sleep

from pytest import raises

from bearcat.classes import Channel, Modulation
from bearcat.exceptions import UnexpectedResultError
from bearcat.scanners.handheld import OperationMode, PriorityMode
from bearcat.scanners.bc75xlt import BC75XLT, BC75XLT_CloseCallMode, BC75XLT_DelayTime

scanner = BC75XLT('/host-dev/ttyUSB0')


def test_hardware():
    assert scanner.get_model() == 'BC75XLT'
    assert scanner.get_version() == 'Version 1.01.02'

def test_voltage():
    voltage, freq = scanner.get_window_voltage()
    assert 0 < voltage < 1
    assert not freq or scanner.MIN_FREQUENCY_HZ < freq < scanner.MAX_FREQUENCY_HZ


def test_volume():
    for i in range(16):
        scanner.set_volume(i)
        assert scanner.get_volume() == i

    for i in range(15, -1, -1):
        scanner.set_volume(i)
        assert scanner.get_volume() == i


def test_squelch():
    for i in range(16):
        scanner.set_squelch(i)
        assert scanner.get_squelch() == i

    for i in range(15, -1, -1):
        scanner.set_squelch(i)
        assert scanner.get_squelch() == i


def test_band_plan():
    scanner.set_band_plan(False)
    assert not scanner.get_band_plan()

    scanner.set_band_plan(True)
    assert scanner.get_band_plan()


def test_key_beep():
    scanner.set_key_beep(False)
    assert scanner.get_key_beep() == False

    scanner.set_key_beep(True)
    assert scanner.get_key_beep() == True


def test_priority_mode():
    scanner.set_priority_mode(PriorityMode.OFF)
    assert scanner.get_priority_mode() == PriorityMode.OFF

    scanner.set_priority_mode(PriorityMode.ON)
    assert scanner.get_priority_mode() == PriorityMode.ON

    scanner.set_priority_mode(PriorityMode.PLUS)
    assert scanner.get_priority_mode() == PriorityMode.PLUS

    scanner.set_priority_mode(PriorityMode.DND)
    assert scanner.get_priority_mode() == PriorityMode.DND


def test_custom_search_settings():
    min_freq = int(406e6)
    freq_step = int(8e6)
    for i in range(1, scanner.NUM_CUSTOM_SEARCH_GROUPS + 1):
        scanner.set_custom_search_settings(i, min_freq + i * freq_step, min_freq + (i + 1) * freq_step)

    for i in range(1, scanner.NUM_CUSTOM_SEARCH_GROUPS + 1):
        assert scanner.get_custom_search_settings(i) == (i, min_freq + i * freq_step, min_freq + (i + 1) * freq_step)


def test_close_call_settings():
    bands = [False] * scanner.NUM_FREQUENCY_BANDS
    bands[0] = True
    scanner.set_close_call_settings(BC75XLT_CloseCallMode.OFF, False, False, bands)
    assert scanner.get_close_call_settings() == (BC75XLT_CloseCallMode.OFF, False, False, bands)
    bands[1] = True
    scanner.set_close_call_settings(BC75XLT_CloseCallMode.PRIORITY, True, False, bands)
    assert scanner.get_close_call_settings() == (BC75XLT_CloseCallMode.PRIORITY, True, False, bands)
    bands[2] = True
    scanner.set_close_call_settings(BC75XLT_CloseCallMode.DND, True, True, bands)
    assert scanner.get_close_call_settings() == (BC75XLT_CloseCallMode.DND, True, True, bands)
    bands[3] = True
    scanner.set_close_call_settings(BC75XLT_CloseCallMode.OFF, True, True, bands)
    assert scanner.get_close_call_settings() == (BC75XLT_CloseCallMode.OFF, True, True, bands)
    bands = [False] * scanner.NUM_FREQUENCY_BANDS
    bands[0] = True
    scanner.set_close_call_settings(BC75XLT_CloseCallMode.OFF, False, False, bands)
    assert scanner.get_close_call_settings() == (BC75XLT_CloseCallMode.OFF, False, False, bands)


def test_search_close_call_settings():
    direction = False
    for delay in BC75XLT_DelayTime:
        scanner.set_search_close_call_settings(delay, direction)
        assert scanner.get_search_close_call_settings() == (delay, direction)
        direction = not direction


def test_custom_search_groups():
    groups = [True] * scanner.NUM_CUSTOM_SEARCH_GROUPS
    scanner.set_custom_search_group(groups)
    assert scanner.get_custom_search_group() == groups

    # one group will always be true, so embrace it
    groups = [True] + [False] * (scanner.NUM_CUSTOM_SEARCH_GROUPS - 1)
    scanner.set_custom_search_group(groups)
    assert scanner.get_custom_search_group() == groups


def test_scan_channel_groups():
    groups = [True] * scanner.NUM_SCAN_GROUPS
    scanner.set_scan_channel_group(groups)
    assert scanner.get_scan_channel_group() == groups

    # one group will always be true, so embrace it
    groups = [True] + [False] * (scanner.NUM_SCAN_GROUPS - 1)
    scanner.set_scan_channel_group(groups)
    assert scanner.get_scan_channel_group() == groups


def test_jump():
    scanner.jump_mode(OperationMode.SCAN)
    scanner.jump_mode(OperationMode.SERVICE_SEARCH)
    scanner.jump_mode(OperationMode.CUSTOM_SEARCH)
    scanner.jump_mode(OperationMode.CLOSE_CALL)
    # TODO: find a way to verify jumps


def test_press_key():
    scanner.press_key_sequence('462.5625')
    scanner.press_key('H')
    # TODO: find a way to verify key presses


def test_hold_and_release_key():
    scanner.go_to_quick_search_hold_mode(462562500)

    # only actual long press is to unlock all L/Os
    scanner.hold_key('L')
    sleep(3)
    scanner.release_key('L')
    # TODO: find a way to verify key presses


def test_long_press_key():
    scanner.go_to_quick_search_hold_mode(462562500)
    scanner.long_press_key('L')
    # TODO: find a way to verify key presses


def test_go_to_quick_search_hold_mode():
    scanner.go_to_quick_search_hold_mode(462562500)
    # TODO: find a way to verify key command


def test_get_status():
    # put scanner in scan mode with no groups selected
    scanner.go_to_quick_search_hold_mode(462562500)

    screen, squelch, mute = scanner.get_status()
    assert len(screen.lines) == 1

    assert screen.lines[0].text.strip() == '462.5625'
    assert not screen.lines[0].formatting
    assert screen.lines[0].large

    assert not squelch
    assert mute


def test_get_reception_status():
    # go to WX mode and wait for a channel to be found
    scanner.set_squelch(3)
    scanner.jump_mode(OperationMode.SERVICE_SEARCH)
    sleep(1)

    state, squelch, mute = scanner.get_reception_status()
    assert 162400000 <= state.frequency <= 162550000
    assert squelch
    assert not mute


def test_scan_groups():
    scanner.scan_groups(1, 3, 5, 7, 9)
    assert scanner.get_scan_channel_group() == [True, False] * 5


def test_frequency():
    scanner.frequency(462.562500)
    state, _, _ = scanner.get_reception_status()
    assert state.frequency == 462562500


def test_channel_info():
    set_info = Channel(24, '', 462562500, Modulation.NFM, 0, '1', False, True)
    scanner.set_channel_info(set_info)

    get_info = scanner.get_channel_info(24)
    assert str(get_info) == str(set_info)

    scanner.channel(24)
    state, _, _ = scanner.get_reception_status()
    set_info.index = -1  # reception status doesn't return the channel index
    assert str(state) == super(Channel, set_info).__str__()

    scanner.clear_channel(24)
    get_info = scanner.get_channel_info(24)
    # priority isn't changed if all channels are locked out
    assert str(get_info) == str(Channel(24, modulation=Modulation.AM, delay='0', priority=get_info.priority))


def test_power_off():
    scanner.power_off()
    # BC75XLT driver keeps port alive until physically disconnected
    with raises(UnexpectedResultError):
        scanner.get_model()
