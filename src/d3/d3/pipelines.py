from d3.items import TypeItem, ItemItem
from d3.spiders.typespider import TypeSpider
import MySQLdb
from d3.config import Config
from d3.spiders.itemspider import ItemSpider
import re

class TypeCleanerPipeline(object):
    def process_item(self, item, spider):
        if isinstance(item, TypeItem) and isinstance(spider, TypeSpider):
            item['category'] = item['category'].strip()
            item['subcategory'] = item['subcategory'].strip()
            item['name'] = item['name'].strip()
        
        return item

class ItemCleanerPipeline(object):
    def __init__(self):
        self.stripre = re.compile(r'<[^>]*>', re.MULTILINE)
    
    def process_item(self, item, spider):
        if isinstance(item, ItemItem) and isinstance(spider, ItemSpider):
            item['category'] = self.__parsetext(item['category'])         
            item['subcategory'] = self.__parsetext(item['subcategory'])          
            item['name'] = self.__parsetext(item['name'])
            item['itemtype'] = self.__parsetext(item['itemtype'])
            item['level'] = self.__parsetext(item['level'])
            
            item['imgbarb'] = self.__parseimg(item['imgbarb'])
            item['imgdh'] = self.__parseimg(item['imgdh'])
            item['imgmonk'] = self.__parseimg(item['imgmonk'])
            item['imgwd'] = self.__parseimg(item['imgwd'])
            item['imgwizard'] = self.__parseimg(item['imgwizard'])
            
#            item['stats'] = self.stripre.sub(item['stats'], '')
#            item['effects'] = self.stripre.sub(item['effects'], '')
#            item['extras'] = self.stripre.sub(item['extras'], '')
        
        return item

    def __parseimg(self, item):
        rval = ''
        
        if item:
            data = item.split('()')
            if len(data) > 1:
                rval = data[1]
        
        return rval
                
    def __parsetext(self, item):
        rval = ''
        
        if isinstance(item, list):
            if len(item) > 0:
                rval = item[0]
            else:
                rval = ''
        rval = rval.strip()
        
        return rval
    
    
class MySQLPipeline(object):
    db = None
    
    def __init__(self):
        self.db = MySQLdb.connect(host = Config.mysqlserver, user = Config.mysqlusername, 
                             passwd = Config.mysqlpassword, db = Config.mysqldatabase)
    
    def process_item(self, item, spider):
        if isinstance(spider, TypeSpider) and isinstance(item, TypeItem):
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO foundtypes
                (category, subcategory, name, url)
                VALUES(%s, %s, %s, %s)
            ''',
            (item['category'], item['subcategory'], item['name'], item['url'])
            )
            self.db.commit()
            cursor.close()
        return item