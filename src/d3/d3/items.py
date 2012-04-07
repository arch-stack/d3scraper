from scrapy.item import Item, Field

class TypeItem(Item):
    category = Field()
    subcategory = Field()
    name = Field()
    url = Field()
    
class ItemItem(Item):
    category = Field()
    subcategory = Field()
    name = Field()
    itemtype = Field()
    level = Field()
    imgbarb = Field()
    imgdh = Field()
    imgmonk = Field()
    imgwd = Field()
    imgwizard = Field()
    stats = Field()
    effects = Field()
    extras = Field()