Custom functionality for the `Szkopuł <https://szkopul.edu.pl>`_ platform.

To run locally instance with same configuration as szkopul production write this to settings.py in docker container:
```
from oioioi.szkopul.settings import *
```
And then run in container shell:
```
python manage.py compress
```
