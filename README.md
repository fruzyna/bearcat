# Python Uniden Bearcat Library

Python library for communicating with Uniden Bearcat scanners.

Currently, this library implementation the following scanner's serial APIs.
Ideally as I acquire more scanners, this library will grow to incorporate those.
Go to the [Scanners with Serial Interface Docs](https://github.com/fruzyna/bearcat/wiki/Scanners-with-Serial-Interface-Docs) wiki page for more details on these scanners.
- BC125AT
- BC75XLT


## Official API Docs

Most Uniden scanners have an "operation specification" manual that outlines their API.
Uniden makes it hard to find these manuals, but they can be found with a Google search.
I find starting here helps: https://www.google.com/search?q=site%3Ainfo.uniden.com%2Ftwiki%2Fpub%2FUnidenMan4+operation+specification

## Example Usage

Below is an example of creating a connection to a BC125AT scanner and getting its screen.
There are several included example scripts in `/examples`.

```python
from src.handheld.bearcat import BC125AT

bc = BC125AT('/dev/ttyACM0')
screen, squelch, mute = bc.get_status()
print(screen)
```

## Linux Note

In order to see the UART interface of the scanner on Linux the following command may need to be run after your PC boots.
[More info can be found here.](https://github.com/rikus--/bc125at-perl/issues/1)

```
echo "1965 0017 2 076d 0006" >> /sys/bus/usb/drivers/cdc_acm/new_id
```