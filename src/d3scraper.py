#!/usr/bin/python
import re, urllib2, urllib, sqlite3, gzip, StringIO, os, multiprocessing
from xml.dom import minidom
from time import time

ROOTURL = 'http://us.battle.net'
D3ITEMPAGE = '%s/d3/en/item/' % ROOTURL

db = None
basetime = 0
directory = ''

processes = []

manager = multiprocessing.Manager()
dblock = manager.Lock()

delayedstatements = multiprocessing.Queue()

opener = None

headers = {
   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:7.0.1) Gecko/20100101 Firefox/7.0.1 Iceweasel/7.0.1',
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language': 'en-us,en;q=0.5',
   'Accept-Encoding': 'gzip, deflate',
   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
   'Connection': 'keep-alive',
   'Cache-Control': 'no-cache, no-cache',
   }

# Main regexs
re_itemcategoryblock = re.compile(r'<div class="(?P<class>column-[0-9])">', re.DOTALL)
re_itemcategory = re.compile(r'<div class="column-[0-9]">.*?<h3 class="category ">(?P<category>.*?)</h3>(?P<data>.*)</div>', re.DOTALL)
re_itemsubcategory = re.compile(r'<div class="box">(?:\s*?<h4 class="subcategory ">(?P<subcategory>.*?)</h4>|(?P<subcategory2>\s*?))(?P<data>.*?)</div>', re.DOTALL)
re_itemsubcategoryalt = re.compile(r'<a.*?href="(?P<href>.*?)">(?P<subcategory>.*?)(?:<span.*?</span>.*?)?</a>', re.DOTALL)

# Process regexs
re_itemsubcategoryaltdetails = re.compile(r'(?:<span class="item-class-specific">.*?>(?P<class>.*?)</a>.*?)?<div class="desc">(?P<desc>.*?)</div>', re.DOTALL)
re_itemitem = re.compile(r'(?P<item><tr class="row[0-9].*?</tr>)', re.DOTALL)
re_itemitemspecial = re.compile(r'<div class="data-cell".*?</div>', re.DOTALL)
re_itempredetails = re.compile(r'href="(?P<item>.*?)".*?src="(?P<image>.*?)"', re.DOTALL)
re_itemdetails = re.compile(r'<div class="detail-level">.*?<span>(?P<level>[0-9]+)</span>.*?<div class="detail-text">.*?<h2.*?>(?P<name>.*?)</h2>', re.DOTALL)
re_crafting = re.compile(r'<div class="artisan-content">.*?<div class="created-by">.*?<div class="name.*?>(?P<at>.*?)</div>.*?<div class="level">Level (?P<level>[0-9]*)</div>.*?<div class="material-list">.*?<div class="material-icons">(?P<data>.*?)</div>.*?<div class="cost">.*?<span class="d3-color-white">(?P<cost>[0-9,]*)</span>', re.DOTALL)
re_craftmaterials = re.compile(r'href="(?P<item>.*?)".*?<span class="no">(?P<quantity>[0-9]*)</span>', re.DOTALL)
re_craftitem = re.compile(r'<div class="item-taught-by">.*?<h4.*?>(?P<name>.*?)</h4>.*?(?:<p>(?P<desc>.*?)</p>)?', re.DOTALL)
re_striptags = re.compile(r'<.*?>', re.DOTALL)

def scrape():
    ''' Begin the scraping process
    '''
    
    global basetime
    basetime = time()
    
    global opener
    opener = makeod()
    
    global directory
    directory = '%d-%s' % (basetime, os.getpid())
    os.mkdir(directory)
    filename = os.path.join(directory, 'db.sqlite')
    
    try:
        msg('Starting up')
        global db
        db = sqlite3.connect(filename)
        initdb(db)
        
        msg('Load item index')
        data = readurl(D3ITEMPAGE, opener)
            
        parsecategories(data)
        
        msg('Waiting for all processes to finish')
        while(processes):
            processes.pop().join()
        msg('Processes finished')
        
        msg('Executing all delayed statements')
        execdelayed()
        
        msg('Closing db')
        db.close()
        
        msg('Finished\t\t\tDB file is %s' % filename)
    except Exception, e:
        msg('Error %s' % e.message)
        
        for process in processes:
            msg('Killing process: %d' % process.pid)
            process.terminate()
    
def parsecategories(data):
    ''' Parse main categories
    @type data: str
    '''
    msg('Parsing categories')
    
    # Need to use a dom due to a few inconsistencies that get in the way of simple regexs
    doc = minidom.parseString(data)
    nodes = doc.getElementsByTagName('div')
    
    matches = re_itemcategoryblock.findall(data)
    for match in matches:
        newdata = None
        
        for node in nodes:
            if node.attributes and node.getAttribute('class') == match:
                newdata = node.toxml()
                break
                
        if newdata:
            groups = re_itemcategory.search(newdata)
            category = groups.group('category').strip()
            
            msg('Found category: %s' % category)
            
            dblock.acquire()
            cursor = db.cursor()
            cursor.execute('INSERT INTO category VALUES(NULL, ?)', (category,))
            db.commit() 
            cursor.close()    
            dblock.release()
            
            parsesubcategories(category, groups.group('data'))
        
def parsesubcategories(category, data):
    ''' Parse subcategories
    @type category: str
    @type data: str
    '''
    msg('Parsing subcategories for: %s' % category)
    
    matches = re_itemsubcategory.findall(data)
    
    for match in matches:
        subcategory = match[0].strip()
        
        msg('Found subcategory group: %s' % subcategory)

        if subcategory:
            insertsubcategory(subcategory, '')
            
        # Parse alt subcategories
        altmatches = re_itemsubcategoryalt.findall(match[2])
        for altmatch in altmatches:
            altsubcategory = altmatch[1].strip()
            
            msg('Found alt subcategory: %s' % altsubcategory)
            prepprocess(category, subcategory, altsubcategory, altmatch[0])
            
def prepprocess(category, subcategory, altsubcategory, url):
    ''' Prepare a process to scrape all items in a specific altsubcategory page
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type url: str
    '''
    msg('Preparing process: %s, %s, %s' % (category, subcategory, altsubcategory))
    processes.append(multiprocessing.Process(target = itemlistscraper,
                                             args = (delayedstatements,
                                                     category,
                                                     subcategory,
                                                     altsubcategory,
                                                     url
                                                     )))
    processes[-1].start()
    msg('Process running(%d): %s, %s, %s' % (processes[-1].pid, category, subcategory, altsubcategory))
    
def itemlistscraper(ds, category, subcategory, altsubcategory, url):
    ''' Load the url and parse each item
    @type ds: multiprocessing.Queue
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type url: str
    '''
    od = makeod()
    data = readurl('%s%s' % (ROOTURL, url), od)
    
    groups = re_itemsubcategoryaltdetails.search(data)
    desc = cleanstr(groups.group('desc')).strip()
    insertsubcategory(altsubcategory, desc)
    
    attributes = []
    attribute = groups.group('class')
    if attribute:
        attributes.append(insertattribute('%s Only' % attribute.strip()))
        
    parseitemlist(ds, od, category, subcategory, altsubcategory, data, attributes)

def parseitemlist(ds, od, category, subcategory, altsubcategory, data, attributes):
    ''' Parse a list of items
    @type ds: multiprocessing.Queue
    @type od: urllib2.OpenerDirector
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type data: str
    @type attributes: list
    '''
    matches = []
    
    # Special lists
    if altsubcategory in ('Crafting Materials', 'Dyes', 'Gems', 'Runestones', 'Potions'):
        matches = re_itemitemspecial.findall(data)
    # Normal lists
    else:
        matches = re_itemitem.findall(data)
        
    if matches:
        msg('%s, %s, %s: Found %d item(s)' % (category, subcategory, altsubcategory, len(matches)))
    else:
        msg('WARNING %s, %s, %s: No matches found, did something go wrong?' % (category, subcategory, altsubcategory))
    
    for match in matches:
        groups = re_itempredetails.search(match)
        dlimage(groups.group('image'))
        
        itemdata = readurl('%s%s' % (ROOTURL, groups.group('item')), od)
        
        parseitem(ds, category, subcategory, altsubcategory, itemdata, attributes, groups.group('image'), '%s%s' % (ROOTURL, groups.group('item')))

def parseitem(ds, category, subcategory, altsubcategory, data, attributes, image, url):
    ''' Parse item data and store the item details (this is where the magic happens)
    @type ds: multiprocessing.Queue
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type data: str
    @type attributes: list
    @type image: str
    '''
    
    itemid = 0
    
    # Handle blacksmith plan special cases
    if altsubcategory == 'Blacksmith Plans':
        # Handle the plan item
        groups = re_craftitem.search(data)
        name = cleanstr(groups.group('name'))
        desc = groups.group('desc')
        if desc:
            # Clean up the text
            desc = re_striptags.sub('', cleanstr(desc).strip())
        else:
            desc = ''
                
        itemid = insertitem(name, desc, os.path.basename(image), category, 0, url)
        
        # Handle crafting
        craftitemgroups = re_itemdetails.search(data)
        craftitemname = cleanstr(craftitemgroups.group('name')).strip()
        
        craftinggroups = re_crafting.search(data)
        craftat = craftinggroups.group('at').strip()
        level = craftinggroups.group('level').strip()
        cost = craftinggroups.group('cost').replace(',', '').strip()
        materialsdata = craftinggroups.group('data')

        linkcraft(ds, craftitemname, itemid, craftat, level, cost)
        
        # Handle crafting materials
        materials = re_craftmaterials.findall(materialsdata)
        for material in materials:
            url = material[0]
            quantity = material[1]
            linkcraftmaterial(ds, itemid, url, quantity)      
        
    # Normal cases
    else:       
        groups = re_itemdetails.search(data)
        
        name = cleanstr(groups.group('name')).strip()
        level = groups.group('level')
        
        itemid = insertitem(name, '', os.path.basename(image), category, level, url)
    
    if itemid:
        if subcategory:
            linkitemsubcategory(itemid, subcategory)
        linkitemsubcategory(itemid, altsubcategory)    

def dlimage(url):
    ''' Download an image at url
    @type url: str
    '''
    image = urllib2.urlopen(url)
    fd = open(os.path.join(directory, os.path.basename(url)), 'w')
    fd.write(image.read())
    fd.close()
    image.close()

def linkitemsubcategory(itemid, subcategory):
    ''' Link an item and a subcategory
    @type itemid: str
    @type subcategory: str
    '''
    dblock.acquire()
    cursor = db.cursor()
    cursor.execute('INSERT OR IGNORE INTO itemsubcategory SELECT ?, id FROM subcategory WHERE name = ?', 
                   (int(itemid), unicode(subcategory)))
    db.commit() 
    cursor.close()    
    dblock.release()

def linkcraft(ds, craftitemname, itemid, craftat, level, cost):
    ''' Link a craft to items 
    @type ds: multiprocessing.Queue
    @type craftitemname: str
    @type itemid: str
    @type craftat: str
    @type level: int
    @type cost: int
    '''
    ds.put(('INSERT OR IGNORE INTO craft SELECT id, ?, ?, ?, ? FROM item WHERE name = ?',
                          (int(itemid), unicode(craftat), int(level), int(cost), unicode(craftitemname))))

def linkcraftmaterial(ds, craftid, itemurl, quantity):
    ''' Link a craft to items 
    @type ds: multiprocessing.Queue
    @type craftid: str
    @type itemurl: str
    @type quantity: int
    '''
    ds.put(('INSERT OR IGNORE INTO craftmaterial SELECT ?, id, ? FROM item WHERE url = ?',
                          (int(craftid), int(quantity), unicode('%s%s' % (ROOTURL, itemurl)))))

def insertitem(name, desc, image, category, level, url):
    ''' Insert an item in to the db, return the new id
    @type name: str
    @type image: str
    @type categoryid: str
    '''
    dblock.acquire()
    cursor = db.cursor()
    cursor.execute('INSERT OR IGNORE INTO item SELECT NULL, ?, ?, ?, id, ?, ? FROM category WHERE name = ?', 
                   (unicode(name), unicode(desc), unicode(image), int(level), unicode(url), unicode(category)))
    rval = cursor.lastrowid
    db.commit() 
    cursor.close()    
    dblock.release()
    
    return rval    

def insertsubcategory(name, desc):
    ''' Insert a subcategory in to the db, return the new id
    @type name: str
    @type desc: str
    '''
    dblock.acquire()
    cursor = db.cursor()
    cursor.execute('INSERT OR IGNORE INTO subcategory VALUES(NULL, ?, ?)', 
                   (unicode(name), unicode(desc)))
    rval = cursor.lastrowid
    db.commit() 
    cursor.close()    
    dblock.release()
    
    return rval
    
def insertattribute(name):
    ''' Insert an attribute in to the db, return the new id
    @type name: str
    '''
    dblock.acquire()
    cursor = db.cursor()
    cursor.execute('INSERT OR IGNORE INTO attribute VALUES(NULL, ?)', 
                   (unicode(name),))
    rval = cursor.lastrowid
    db.commit() 
    cursor.close()    
    dblock.release()
    
    return rval
    
def msg(text):
    ''' Print out a message with a duration time in seconds
    @type text: str
    '''
    print '[%3d] %s' % (time() - basetime, text)

def readurl(url, od):
    ''' Read a URL and return the HTML data
    @type url: str
    @type od: urllib2.OpenerDirector
    '''
    requestheaders = {}
    data = ''
    responseheaders = []
    
    while(True):
        msg('Requesting: %s' % url)
        
        req = urllib2.Request(url, urllib.urlencode(requestheaders), headers)
        
        res = od.open(req)
        
        # Normal case
        if not 'd3/en/age' in res.geturl():
            data = res.read()
            responseheaders = res.info()
            break
        # Agegate
        else:
            msg('Submitting to age gate')
            requestheaders['day'] = 21
            requestheaders['month'] = 7
            requestheaders['year'] = 1986
            url = res.geturl()
            
    
    if 'content-encoding' in responseheaders.keys() and responseheaders['content-encoding'] == 'gzip':
        sfd = StringIO.StringIO(data)
        gzfd = gzip.GzipFile(fileobj = sfd)
        data = gzfd.read()
        gzfd.close()
        sfd.close()
    
    return data

def cleanstr(string):
    ''' Remove some unicode chars blizzard uses
    @type string: str
    '''
    return unicode(string.decode('utf-8')).replace(u'\u2019', '\'').replace(u'\u2013', '-')

def makeod():
    ''' Create and return a urllib2.OpenerDirector
    '''
    rval = urllib2.build_opener()
    rval.add_handler(urllib2.HTTPHandler())
    rval.add_handler(urllib2.HTTPCookieProcessor())
    rval.add_handler(urllib2.HTTPRedirectHandler())
    rval.add_handler(urllib2.UnknownHandler())
    
    return rval

def initdb(db):
    ''' Initialize the database structure
    @type db: sqlite3.Connection
    '''
    
    msg('Init db')
    
    cursor = db.cursor()
    
    ### Tables
    
    # Category
    cursor.execute(
    '''CREATE TABLE category(
    id INTEGER PRIMARY KEY, 
    name TEXT UNIQUE
    )''')
    
    # Subcategory
    cursor.execute(
    '''CREATE TABLE subcategory(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    desc TEXT
    )''')
    
    # Item
    cursor.execute(
    '''CREATE TABLE item(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    desc TEXT,
    image TEXT,
    categoryid INTEGER,
    level INTEGER,
    url TEXT,
    FOREIGN KEY(categoryid) REFERENCES category(id)
    )''')
    
    # Attribute
    cursor.execute(
    '''CREATE TABLE attribute(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
    )''')    
    
    # Item-Subcategory
    cursor.execute(
    '''CREATE TABLE itemsubcategory(
    itemid INTEGER,
    subcategoryid INTEGER,
    FOREIGN KEY(itemid) REFERENCES item(id),
    FOREIGN KEY(subcategoryid) REFERENCES subcategory(id)
    )''')
    
    # Craft
    cursor.execute(
    '''CREATE TABLE craft(
    id INTEGER UNIQUE,
    requireditemid INTEGER UNIQUE,
    craftat TEXT,
    level INTEGER,
    cost INTEGER,
    FOREIGN KEY(id) REFERENCES item(id),
    FOREIGN KEY(requireditemid) REFERENCES item(id)
    )''')
    
    # Craft-Material
    cursor.execute(
    '''CREATE TABLE craftmaterial(
    craftid INTEGER,
    itemid INTEGER,
    quantity INTEGER,
    FOREIGN KEY(craftid) REFERENCES craft(id),
    FOREIGN KEY(itemid) REFERENCES item(id)
    )''')
    
    db.commit()
    cursor.close()
    
def execdelayed():
    ''' Execute all delayed statements
    A statement may be delayed if it's possible the dependancies are not yet met
    Ex: crafts may be parsed before items, delay the craft til after items are added
    '''
    msg('%d delayed statements' % delayedstatements.qsize())
    cursor = db.cursor()
    while(not delayedstatements.empty()):
        data = delayedstatements.get()
        cursor.execute(data[0], data[1])
    db.commit() 
    cursor.close()    

if __name__ == '__main__':
    scrape()