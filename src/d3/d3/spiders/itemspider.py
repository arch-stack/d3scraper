from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector
from d3.config import Config
import MySQLdb
from d3.items import ItemItem

class ItemSpider(CrawlSpider):
    name = 'Item'
    allowed_domains = ['battle.net']
    start_urls = []
    rules = (Rule(
              SgmlLinkExtractor(
                allow = ('/d3/en/item/',), 
                deny = (),
                restrict_xpaths = ('//div[@class="table db-table db-table-padded"]//tr//*[@class="item-details-icon"]',),
                tags = ('a',)
              ), 
             callback = 'parse_item')
             ,)
    
    def __init__(self):
        CrawlSpider.__init__(self)
        
        db = MySQLdb.connect(host = Config.mysqlserver, user = Config.mysqlusername, 
                             passwd = Config.mysqlpassword, db = Config.mysqldatabase)
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT *
            FROM foundtypes
        ''')
        
        rows = cursor.fetchall()
        
        for row in rows:
            if len(row) >= 4:
                self.start_urls.append('http://battle.net%s' % row[4])
        cursor.close()
        db.close()

    def parse_item(self, response):
        self.log('Item found') 
        hxs = HtmlXPathSelector(response)
        
        item = ItemItem()
        return item