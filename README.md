# Python Uniden Bearcat Library

Python library for communicating with Uniden Bearcat scanners.

Currently, this library implements the following scanner's serial APIs.
Ideally as I acquire more scanners, this library will grow to incorporate those.
- BC125AT
- BC75XLT

## Official API Docs

Most Uniden scanners have an "operation specification" manual that outlines their API.
Uniden makes it hard to find these manuals, but they can be found with a Google search.
[I find starting here helps](https://www.google.com/search?q=site%3Ainfo.uniden.com%2Ftwiki%2Fpub%2FUnidenMan4+operation+specification).
A list of known operation specs can be found on the [Scanners with Serial Interface Docs](https://github.com/fruzyna/bearcat/wiki/Scanners-with-Serial-Interface-Docs) wiki page.

## Example Usage

Below is an example of creating a connection to a BC125AT scanner and getting its screen.
There are several included example scripts in `/examples`.

```python
from bearcat.scanners import BC125AT

bc = BC125AT('/dev/ttyACM0')
screen, squelch, mute = bc.get_status()
print(screen)
```

Alternatively there is a function to automatically detect and construct scanners.
```python
from bearcat import find_scanners

scanners = find_scanners()
if scanners:
    bc = scanners[0]
    screen, squelch, mute = bc.get_status()
    print(screen)
```

## Linux Notes

In order to see the UART interface of the scanner on Linux the following command may need to be run after your PC boots.
[More info can be found here.](https://github.com/rikus--/bc125at-perl/issues/1)

```
echo "1965 0017 2 076d 0006" >> /sys/bus/usb/drivers/cdc_acm/new_id
```

Once that command is run, you should have a new serial device `/dev/ttyACM[X]`.
To access this device you will likely need to either use the root user / sudo or add your user to the dialout group. Try one of the following to do this:
- `sudo adduser $USER dialout`
- `sudo usermod -aG dialout $USER`

Some scanners (such as the BC75XLT) will show up at `/dev/ttyUSB[X]`.