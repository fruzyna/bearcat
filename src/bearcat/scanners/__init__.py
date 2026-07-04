"""Contains definitions of model classes."""
from bearcat import Bearcat
from bearcat.scanners.bc125at import BC125AT, UBC125XLT
from bearcat.scanners.bc75xlt import BC75XLT


SCANNERS: list[type[Bearcat]] = [BC75XLT, BC125AT, UBC125XLT]
