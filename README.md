d3scraper
---------

###Use
1. Run `src/d3/d3/setup.py`
1. Go in to the `src/d3` directory
1. Run `scrapy crawl d3`
1. Output of the scrape will be in the mySQL server and database specified in the config.

###Purpose
To pull all items and their relevant information from the diablo3 website for any use in an easy to use format.

###Configuration
Modify the `src/d3/d3/config.py` file

###Versions
0.4: Changed my mind of things again. Word of a D3 API was out (but I wasn't sure if it was real or not). It may include items but from what I've read it's limited to profile data. This means there might be no items so I will start on the scraping again. This time around I am going to use a scraping framework.
 
0.3BROKEN: This is intended to be the new beta release. It's a work in progress. Goals include unit-tests and code coverage.

0.2BROKEN: Broken version. Final commit of my primary design. Due to complications/limitations I decided to re-think how I am doing things and decided to go with a more clean/proper approach after learning python multiprocessing.

0.1: Initial partially working version