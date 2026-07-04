"""Script to configure my BC75XLT to my liking."""
from sys import argv

from bearcat.scanners.bc75xlt import BC75XLT, BC75XLT_CloseCallMode, BC75XLT_DelayTime
from bearcat.scanners.handheld import PriorityMode


assert len(argv) > 1, "Script requires one argument, the address of the scanner."

bc = BC75XLT(argv[1])
bc.debug = True
bc.set_volume(5)
bc.set_squelch(7)

bc.enter_program_mode()
bc.set_band_plan(False)
bc.set_key_beep(False)
bc.set_priority_mode(PriorityMode.OFF)
bc.set_search_close_call_settings(BC75XLT_DelayTime.TWO, True)
bc.set_close_call_settings(BC75XLT_CloseCallMode.OFF, False, False, [False, False, False, False])
bc.exit_program_mode()
