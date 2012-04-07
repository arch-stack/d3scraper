BOT_NAME = 'd3'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['d3.spiders']
NEWSPIDER_MODULE = 'd3.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

CONCURRENT_REQUESTS = 24
CONCURRENT_REQUESTS_PER_DOMAIN = 24
ITEM_PIPELINES = ['d3.pipelines.TypeCleanerPipeline',
                  'd3.pipelines.ItemCleanerPipeline',
                  'd3.pipelines.MySQLPipeline']

