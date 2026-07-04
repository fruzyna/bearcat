from bearcat.scanners.handheld import PriorityMode, OperationMode
from bearcat.scanners.bc125at import BC125AT_BacklightMode, BC125AT_CloseCallMode, BC125AT_DelayTime
from bearcat.classes import Modulation, Channel
from bearcat.scanners.bc125at import BC125AT

from pytest import raises
from serial import SerialException
from time import sleep

scanner = BC125AT('/host-dev/ttyACM0')


def test_hardware():
    assert scanner.get_model() == 'BC125AT'
    assert scanner.get_version() == 'Version 1.06.06'


def test_voltage():
    voltage, freq = scanner.get_window_voltage()
    assert 0 < voltage < 1
    assert not freq or scanner.MIN_FREQUENCY_HZ < freq < scanner.MAX_FREQUENCY_HZ
    assert 0 < scanner.get_battery_voltage() < 3.5


def test_electronic_serial_number():
    assert scanner.get_electronic_serial_number() == ('XXXXXXXXXXXXXX', '000', '1')


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


def test_contrast():
    for i in range(1, 16):
        scanner.set_contrast(i)
        assert scanner.get_contrast() == i

    for i in range(15, 0, -1):
        scanner.set_contrast(i)
        assert scanner.get_contrast() == i


def test_charge_time():
    for i in range(1, 15):
        scanner.set_charge_time(i)
        assert scanner.get_charge_time() == i

    for i in range(14, 1, -1):
        scanner.set_charge_time(i)
        assert scanner.get_charge_time() == i


def test_band_plan():
    scanner.set_band_plan(False)
    assert not scanner.get_band_plan()

    scanner.set_band_plan(True)
    assert scanner.get_band_plan()


def test_weather_priority():
    scanner.set_weather_priority(False)
    assert not scanner.get_weather_priority()

    scanner.set_weather_priority(True)
    assert scanner.get_weather_priority()


def test_key_beep():
    scanner.set_key_beep(False, False)
    assert scanner.get_key_beep() == (False, False)

    scanner.set_key_beep(True, True)
    assert scanner.get_key_beep() == (True, True)


def test_priority_mode():
    scanner.set_priority_mode(PriorityMode.OFF)
    assert scanner.get_priority_mode() == PriorityMode.OFF

    scanner.set_priority_mode(PriorityMode.ON)
    assert scanner.get_priority_mode() == PriorityMode.ON

    scanner.set_priority_mode(PriorityMode.PLUS)
    assert scanner.get_priority_mode() == PriorityMode.PLUS

    scanner.set_priority_mode(PriorityMode.DND)
    assert scanner.get_priority_mode() == PriorityMode.DND


def test_backlight():
    scanner.set_backlight(BC125AT_BacklightMode.ALWAYS_ON)
    assert scanner.get_backlight() == BC125AT_BacklightMode.ALWAYS_ON

    scanner.set_backlight(BC125AT_BacklightMode.ALWAYS_OFF)
    assert scanner.get_backlight() == BC125AT_BacklightMode.ALWAYS_OFF

    scanner.set_backlight(BC125AT_BacklightMode.KEYPRESS)
    assert scanner.get_backlight() == BC125AT_BacklightMode.KEYPRESS

    scanner.set_backlight(BC125AT_BacklightMode.SQUELCH)
    assert scanner.get_backlight() == BC125AT_BacklightMode.SQUELCH

    scanner.set_backlight(BC125AT_BacklightMode.KEYPRESS_SQUELCH)
    assert scanner.get_backlight() == BC125AT_BacklightMode.KEYPRESS_SQUELCH


def test_custom_search_settings():
    min_freq = int(230e6)
    freq_step = int(10e6)
    for i in range(1, scanner.NUM_CUSTOM_SEARCH_GROUPS + 1):
        scanner.set_custom_search_settings(i, min_freq + i * freq_step, min_freq + (i + 1) * freq_step)

    for i in range(1, scanner.NUM_CUSTOM_SEARCH_GROUPS + 1):
        assert scanner.get_custom_search_settings(i) == (i, min_freq + i * freq_step, min_freq + (i + 1) * freq_step)


def test_close_call_settings():
    bands = [False] * scanner.NUM_FREQUENCY_BANDS
    scanner.set_close_call_settings(BC125AT_CloseCallMode.OFF, False, False, bands, False)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.OFF, False, False, bands, False)
    bands[0] = True
    scanner.set_close_call_settings(BC125AT_CloseCallMode.PRIORITY, True, False, bands, False)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.PRIORITY, True, False, bands, False)
    bands[1] = True
    scanner.set_close_call_settings(BC125AT_CloseCallMode.DND, True, True, bands, False)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.DND, True, True, bands, False)
    bands[2] = True
    scanner.set_close_call_settings(BC125AT_CloseCallMode.ONLY, True, True, bands, True)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.ONLY, True, True, bands, True)
    bands[3] = True
    scanner.set_close_call_settings(BC125AT_CloseCallMode.OFF, False, False, bands, False)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.OFF, False, False, bands, False)
    bands[4] = True
    scanner.set_close_call_settings(BC125AT_CloseCallMode.OFF, False, False, bands, False)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.OFF, False, False, bands, False)
    bands = [False] * scanner.NUM_FREQUENCY_BANDS
    scanner.set_close_call_settings(BC125AT_CloseCallMode.OFF, False, False, bands, False)
    assert scanner.get_close_call_settings() == (BC125AT_CloseCallMode.OFF, False, False, bands, False)


def test_search_close_call_settings():
    search = False
    for delay in BC125AT_DelayTime:
        scanner.set_search_close_call_settings(delay, search)
        assert scanner.get_search_close_call_settings() == (delay, search)
        search = not search


def test_reset():
    scanner.clear_all_memory()
    for i in range(1, scanner.TOTAL_CHANNELS + 1):
        channel = scanner.get_channel_info(i)
        assert channel.index == i
        assert not channel.name
        assert not channel.frequency
        assert channel.modulation == Modulation.AUTO
        assert not channel.tone_code
        assert channel.delay == BC125AT_DelayTime.TWO.value
        assert channel.lockout
        assert not channel.priority


def test_lock_out():
    freqs = [int(f) for f in [25e6, 28e6, 108e6, 137e6, 225e6, 400e6]]

    for f in freqs:
        scanner.lock_out_frequency(f)
        assert f in scanner.get_global_lockout_freqs()

    for f in scanner.get_global_lockout_freqs():
        scanner.unlock_global_lo(f)

    assert not scanner.get_global_lockout_freqs()


def test_custom_search_groups():
    groups = [False] * scanner.NUM_CUSTOM_SEARCH_GROUPS
    scanner.set_custom_search_group(groups)
    assert scanner.get_custom_search_group() == groups

    for i in range(scanner.NUM_CUSTOM_SEARCH_GROUPS):
        groups[i] = True
        scanner.set_custom_search_group(groups)
        assert scanner.get_custom_search_group() == groups

    for i in range(scanner.NUM_CUSTOM_SEARCH_GROUPS - 1, -1, -1):
        groups[i] = False
        scanner.set_custom_search_group(groups)
        assert scanner.get_custom_search_group() == groups


def test_scan_channel_groups():
    groups = [False] * scanner.NUM_SCAN_GROUPS
    scanner.set_scan_channel_group(groups)
    assert scanner.get_scan_channel_group() == groups

    for i in range(scanner.NUM_SCAN_GROUPS):
        groups[i] = True
        scanner.set_scan_channel_group(groups)
        assert scanner.get_scan_channel_group() == groups

    for i in range(scanner.NUM_SCAN_GROUPS - 1, -1, -1):
        groups[i] = False
        scanner.set_scan_channel_group(groups)
        assert scanner.get_scan_channel_group() == groups


def test_service_search_groups():
    groups = [False] * scanner.NUM_SERVICE_SEARCH_GROUPS
    scanner.set_service_search_group(groups)
    assert scanner.get_service_search_group() == groups

    for i in range(scanner.NUM_SERVICE_SEARCH_GROUPS):
        groups[i] = True
        scanner.set_service_search_group(groups)
        assert scanner.get_service_search_group() == groups

    for i in range(scanner.NUM_SERVICE_SEARCH_GROUPS - 1, -1, -1):
        groups[i] = False
        scanner.set_service_search_group(groups)
        assert scanner.get_service_search_group() == groups


def test_jump():
    scanner.jump_mode(OperationMode.SCAN)
    assert scanner.get_status()[0].lines[1].text.startswith('Scan Mode')
    scanner.jump_mode(OperationMode.SERVICE_SEARCH)
    assert scanner.get_status()[0].lines[1].text.startswith('Service Search')
    scanner.jump_mode(OperationMode.CUSTOM_SEARCH)
    assert scanner.get_status()[0].lines[1].text.startswith('Custom Search')
    scanner.jump_mode(OperationMode.CLOSE_CALL)
    assert scanner.get_status()[0].lines[1].text.startswith('Close Call')
    scanner.jump_mode(OperationMode.WEATHER)
    assert scanner.get_status()[0].lines[1].text.startswith('WX Scan')
    # TODO: not supported? scanner.jump_mode(OperationMode.TONE_OUT)
    scanner.jump_to_channel(1)
    assert scanner.get_status()[0].lines[2].text.startswith('CH001')
    scanner.jump_to_channel(scanner.TOTAL_CHANNELS)
    assert scanner.get_status()[0].lines[2].text.startswith(f'CH{scanner.TOTAL_CHANNELS:03}')


def test_press_key():
    scanner.press_key_sequence('462.5625')
    assert scanner.get_status()[0].lines[1].text.startswith('462.5625')
    scanner.press_key('H')
    assert scanner.get_status()[0].lines[1].text.startswith('Quick Search')
    assert '462.5625' in scanner.get_status()[0].lines[2].text
    scanner.press_key('F')
    scanner.press_key('R')
    assert scanner.get_status()[0].lines[1].text.startswith('Service Search')


def test_hold_and_release_key():
    scanner.go_to_quick_search_hold_mode(462562500)

    # only actual long press is to unlock all L/Os
    scanner.hold_key('L')
    sleep(3)
    scanner.release_key('L')

    # one of two prompts (there are L/Os to unlock or there are none)
    screen, _, _ = scanner.get_status()
    assert len(screen.lines) == 4
    assert screen.lines[0].text.strip() in ['Confirm Unlock', 'Nothing Locked']

    # test that key is no longer held by trying to exit
    scanner.press_key('.')
    screen, _, _ = scanner.get_status()
    assert screen.lines[0].text.strip() not in ['Confirm Unlock', 'Nothing Locked']


def test_long_press_key():
    scanner.go_to_quick_search_hold_mode(462562500)
    scanner.long_press_key('L')
    screen, _, _ = scanner.get_status()
    assert len(screen.lines) == 4
    assert screen.lines[0].text.strip() in ['Confirm Unlock', 'Nothing Locked']
    scanner.press_key('.')


def test_go_to_quick_search_hold_mode():
    scanner.go_to_quick_search_hold_mode(462562500)
    assert scanner.get_status()[0].lines[1].text.startswith('Quick Search')
    assert '462.5625' in scanner.get_status()[0].lines[2].text
    state, _, _ = scanner.get_reception_status()
    assert state.frequency == 462562500


def test_get_status():
    # put scanner in scan mode with no groups selected
    scanner.set_scan_channel_group([False] * 10)
    scanner.jump_mode(OperationMode.SCAN)

    screen, squelch, mute = scanner.get_status()
    assert len(screen.lines) == 6

    assert screen.lines[1].text.strip() == 'Scan Mode'
    assert not screen.lines[1].formatting
    assert screen.lines[1].large

    assert screen.lines[5].text.strip() == 'BNK:----------'
    assert not screen.lines[5].formatting
    assert not screen.lines[5].large

    assert not squelch
    assert mute


def test_get_reception_status():
    # go to WX mode and wait for a channel to be found
    scanner.jump_mode(OperationMode.WEATHER)
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
    set_info = Channel(24, 'Test Channel', 462562500, Modulation.NFM, 224, '1', False, True)
    scanner.set_channel_info(set_info)

    get_info = scanner.get_channel_info(24)
    assert str(get_info) == str(set_info)

    scanner.channel(24)
    state, _, _ = scanner.get_reception_status()
    set_info.tone_code = 0  # reception status doesn't return the tone code
    assert str(state) == super(Channel, set_info).__str__()

    scanner.clear_channel(24)
    get_info = scanner.get_channel_info(24)
    assert str(get_info) == str(Channel(24, modulation=Modulation.AUTO))


def test_power_off():
    scanner.power_off()
    sleep(1)  # allows serial port to disconnect
    with raises(SerialException):
        scanner.get_model()
