from scrapy.item import Item, Field

class TypeItem(Item):
    category = Field()
    subcategory = Field()
    name = Field()
    url = Field()
    
class ItemItem(Item):
    pass