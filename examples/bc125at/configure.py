"""Script to configure my BC125AT to my liking."""
from bearcat import DelayTime
from bearcat.bc125at import BC125AT

bc = BC125AT('/dev/ttyACM0')

bc.set_volume(5)
bc.set_squelch(7)

bc.enter_program_mode()
bc.set_backlight(BC125AT.BacklightMode.ALWAYS_OFF)
bc.set_band_plan(False)
bc.set_charge_time(14)
bc.set_key_beep(True, False)
bc.set_priority_mode(BC125AT.PriorityMode.OFF)
bc.set_search_close_call_settings(DelayTime.TWO, True)
bc.set_close_call_settings(BC125AT.CloseCallMode.OFF, False, False, [False, False, False, False, False], False)
bc.set_weather_priority(False)
bc.set_contrast(7)
bc.exit_program_mode()
