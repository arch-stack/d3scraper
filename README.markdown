d3scraper
---------

###Use
1. Run `python ./d3scraper.py`
1. Output of the scrape will be in `./time-pid/db.sqlite` where time represents a timestamp for when the scrape started and pid is the process id that created it
1. Images will be located in the same folder as the db file

###Purpose
To pull all items and their relevant information from the diablo3 website for any use in an easy to use format.

###Versions
0.3: This is intended to be the new beta release. It's a work in progress. Goals include unit-tests and code coverage.
0.2BROKEN: Broken version. Final commit of my primary design. Due to complications/limitations I decided to re-think how I am doing things and decided to go with a more clean/proper approach after learning python multiprocessing.
0.1: Initial partially working version