from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from d3.items import TypeItem

class TypeSpider(BaseSpider):
    name = 'D3Scraper'
    start_urls = ['http://us.battle.net/d3/en/item/']
    allowed_domains = ['battle.net']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="equipment"]/div')
        self.log('Found %d categories' % len(categories))
        
        items = []
        
        for category in categories:
            catname = category.select('.//h3/text()').extract()
            if len(catname) >= 1:
                catname = catname[0]
            else:
                catname = ''
                
            self.log('Category %s' % catname)
            subcategories = category.select('.//div[@class="box"]')
            self.log('Found %d subcategories' % len(subcategories))
            
            for subcategory in subcategories:
                subcatname = subcategory.select('.//h4/text()').extract()
                if len(subcatname) >= 1:
                    subcatname = subcatname[0]
                else:
                    subcatname = ''

                self.log('Subcategory %s' % subcatname)
                links = subcategory.select('.//a')
                self.log('Found %d links' % len(links))
                
                for link in links:
                    name = link.select('.//text()').extract()
                    if len(name) >= 1:
                        name = name[0]
                    else:
                        name = ''

                    url = link.select('.//@href').extract()
                    if len(url) >= 1:
                        url = url[0]
                    else:
                        url = ''

                    self.log('Link [%s]: %s' % (name, url))
                    
                    item = TypeItem()
                    item['category'] = catname
                    item['subcategory'] = subcatname
                    item['name'] = name
                    item['url'] = url
                    
                    items.append(item)
                    self.log('Item added %d' % len(items))
                
        return items