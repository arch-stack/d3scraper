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
        item['url'] = response.url
        
        content = hxs.select('//div[@class="body-bot"]')
        item['category'] = content.select('.//h2[@class="header "]/a/text()').extract()
        item['subcategory'] = content.select('.//h2[@class="header "]/small/text()').extract()
        item['name'] = content.select('.//div[@class="detail-text"]/h2/text()').extract()
        item['itemtype'] = content.select('.//div[@class="detail-text"]//ul[@class="item-type"]//span/text()').extract()
        item['level'] = content.select('.//div[@class="detail-level"]/span/text()').extract()
        icons = content.select(
                   './/div[@class="page-section item-appearance"]//span[@class="icon-item-inner icon-item-default"]/@style'
                   ).extract()
        
        if len(icons) > 0:
            item['imgbarb'] = icons[0]
            item['imgdh'] = icons[1]
            item['imgmonk'] = icons[2]
            item['imgwd'] = icons[3]
            item['imgwizard'] = icons[4]
        else:
            # Need to use the one image for all
            icon = content.select('//*[@class="icon-item-inner icon-item-default"]/@style').extract()
            if len(icon) > 0:
                item['imgbarb'] = icon[0]
                item['imgdh'] = icon[0]
                item['imgmonk'] = icon[0]
                item['imgwd'] = icon[0]
                item['imgwizard'] = icon[0]
            else:
                item['imgbarb'] = ''
                item['imgdh'] = ''
                item['imgmonk'] = ''
                item['imgwd'] = ''
                item['imgwizard'] = ''

            
        item['stats'] = content.select('.//ul[@class="item-armor-weapon"]/li').extract()
        item['effects'] = content.select('.//ul[@class="item-before-effects"]/li').extract()
        item['extras'] = content.select('.//ul[@class="item-extras"]/li').extract()
        
        return item
    