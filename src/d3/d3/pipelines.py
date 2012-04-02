from d3.items import TypeItem
from d3.spiders.typespider import TypeSpider
import MySQLdb
from d3.config import Config

class TypeCleanerPipeline(object):
    def process_item(self, item, spider):
        if isinstance(item, TypeItem) and isinstance(spider, TypeSpider):
            item['category'] = item['category'].strip()
            item['subcategory'] = item['subcategory'].strip()
            item['name'] = item['name'].strip()
        
        return item

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