from d3.items import TypeItem
from d3.spiders.typespider import TypeSpider

class TypeCleanerPipeline(object):
    def process_item(self, item, spider):
        if item is TypeItem and spider is TypeSpider:
            item['category'] = item['category'].strip()
            item['subcategory'] = item['subcategory'].strip()
            item['name'] = item['name'].strip()
        
        return item

class MySQLPipeline(object):
    def __init__(self):
        pass
    
    def process_item(self, item, spider):
        return item