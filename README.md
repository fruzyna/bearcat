# Python Uniden Bearcat Library

Python library for communicating with Uniden Bearcat scanners.

Currently, this library only contains an implementation of the BC125AT serial API.
Ideally as I acquire more scanners, this library will grow to incorporate those.

## Official API Docs

Most Uniden scanners have an "operation specification" manual that outlines their API.
Uniden makes it hard to find these manuals, but they can be found with a Google search.
I find starting here helps: https://www.google.com/search?q=site%3Ainfo.uniden.com%2Ftwiki%2Fpub%2FUnidenMan4+operation+specification

## Example Usage

Below is an example of creating a connection to a BC125AT scanner and getting its screen.
There are several included example scripts in `/examples`.

```python
from src.bearcat import BC125AT

bc = BC125AT('/dev/ttyACM0')
screen, squelch, mute = bc.get_status()
print(screen)
```
