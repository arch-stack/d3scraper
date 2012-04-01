# Scrapy settings for d3 project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'd3'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['d3.spiders']
NEWSPIDER_MODULE = 'd3.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

