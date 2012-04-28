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
        self.stripre = re.compile(r'<[^>]*?>', re.MULTILINE)
    
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
            
            item['stats'] = self.__parsedetails(item['stats'])
            item['effects'] = self.__parsedetails(item['effects'])
            item['extras'] = self.__parsedetails(item['extras'])
        
        return item

    def __parsedetails(self, data):
        newdata = []
        
        for item in data:
            newdata.append(self.stripre.sub('', item))
        
        return newdata

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
                             passwd = Config.mysqlpassword, db = Config.mysqldatabase,
                             use_unicode = True, charset='utf8')
    
    def process_item(self, item, spider):
        if isinstance(spider, TypeSpider) and isinstance(item, TypeItem):
            # Store types to scrape in the ItemSpider
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
        elif isinstance(spider, ItemSpider) and isinstance(item, ItemItem):
            # Store an item
            cursor = self.db.cursor()
            
            cursor.execute('''
                INSERT INTO items
                (category, subcategory, name, itemtype, level, 
                    imgbarb, imgdh, imgmonk, imgwd, imgwizard, url)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (item['category'], item['subcategory'], item['name'], item['itemtype'], int(item['level']), 
             item['imgbarb'], item['imgdh'], item['imgmonk'], item['imgwd'], item['imgwizard'], 
             item['url'])
            )
            
            itemid = self.db.insert_id()
            
            for stat in item['stats']: 
                cursor.execute('''
                    INSERT INTO details
                    (detail, itemid, type)
                    VALUES(%s, %s, 'stat')
                ''',
                (stat, itemid)
                )
            
            for effect in item['effects']: 
                cursor.execute('''
                    INSERT INTO details
                    (detail, itemid, type)
                    VALUES(%s, %s, 'effect')
                ''',
                (effect, itemid)
                )
            
            for extra in item['extras']: 
                cursor.execute('''
                    INSERT INTO details
                    (detail, itemid, type)
                    VALUES(%s, %s, 'extra')
                ''',
                (extra, itemid)
                )
            
            self.db.commit()
            cursor.close()
            
        return item