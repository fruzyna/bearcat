"""Script to configure my BC125AT to my liking."""
from sys import argv

from bearcat import DelayTime
from bearcat.handheld.bc75xlt import BC75XLT


assert len(argv) > 1, "Script requires one argument, the address of the scanner."

bc = BC75XLT(argv[1])
bc.debug = True
bc.set_volume(5)
bc.set_squelch(7)

bc.enter_program_mode()
bc.set_band_plan(False)
bc.set_key_beep(False)
bc.set_priority_mode(BC75XLT.PriorityMode.OFF)
bc.set_search_close_call_settings(DelayTime.TWO, True)
bc.set_close_call_settings(BC75XLT.CloseCallMode.OFF, False, False, [False, False, False, False, False])
bc.exit_program_mode()
