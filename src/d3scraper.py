#!/usr/bin/python
import re, urllib2, urllib, sqlite3, gzip, StringIO, os, multiprocessing, socket
from xml.dom import minidom
from time import time

import d3utility

ROOTURL = 'http://us.battle.net'
D3ITEMPAGE = '%s/d3/en/item/' % ROOTURL
TIMEOUT = 15

db = None
basetime = 0
directory = ''

processes = []

manager = multiprocessing.Manager()
dblock = manager.Lock()

craftstatements = multiprocessing.Queue()
craftmaterialstatements = multiprocessing.Queue()
attributestatements = d3utility.largequeue()

opener = None

headers = {
#   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:7.0.1) Gecko/20100101 Firefox/7.0.1 Iceweasel/7.0.1',
   'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)',
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
re_itemsubcategoryaltdetails = re.compile(r'(?:<span class="item-class-specific">.*?>(?P<class>.*?)</a>.*?)?<div class="desc">(?P<desc>.*?)</div>', re.DOTALL)
re_itemitem = re.compile(r'(?P<item><tr class="row[0-9].*?</tr>)', re.DOTALL)
re_itemitemspecial = re.compile(r'<div class="data-cell".*?</div>', re.DOTALL)
re_itempredetails = re.compile(r'href="(?P<item>.*?)".*?src="(?P<image>.*?)"', re.DOTALL)

# Process regexs
re_itemdetails = re.compile(r'<div class="detail-level">.*?<span>(?P<level>[0-9]+)</span>.*?<div class="detail-text">.*?<h2.*?>(?P<name>.*?)</h2>.*?<div class="d3-item-properties">(?P<data>.*?)</div>\s*?</div>', re.DOTALL)
re_crafting = re.compile(r'<div class="artisan-content">.*?<div class="created-by">.*?<div class="name.*?>(?P<at>.*?)</div>.*?<div class="level">Level (?P<level>[0-9]*)</div>.*?<div class="material-list">.*?<div class="material-icons">(?P<data>.*?)</div>.*?<div class="cost">.*?<span class="d3-color-white">(?P<cost>[0-9,]*)</span>', re.DOTALL)
re_craftmaterials = re.compile(r'href="(?P<item>.*?)".*?<span class="no">(?P<quantity>[0-9]*)</span>', re.DOTALL)
re_craftitem = re.compile(r'<div class="item-taught-by">.*?<h4.*?>(?P<name>.*?)</h4>.*?(?:<p>(?P<desc>.*?)</p>)?', re.DOTALL)
re_itemattr = re.compile(r'(?:<ul class="item-type">(?P<type>.*?)</ul>.*?)?<ul class="item-armor-weapon">(?P<armorweapon>.*?)</ul>.*?(?:<div class="item-description">(?P<desc>.*?)</div>.*?)?(?:<ul class="item-effects">(?P<effects>.*?)</ul>.*?)?(?:<ul class="item-itemset">(?P<set>.*?)</ul>.*?)?(?:<ul class="item-extras">(?P<extras>.*?)</ul>)?', re.DOTALL)
re_itemattrlist = re.compile(r'<li>(?P<data>.*?)</li>', re.DOTALL)

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
            p = processes.pop()
            msg('Joining process: %d' % p.pid)
            p.join()
        msg('Processes finished')
        
        msg('Executing all delayed statements')
        execdelayed()
        
        msg('Closing db')
        db.close()
        
        msg('Finished\t\t\tDB file is %s' % filename)
    except Exception as e:
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
            listdata = readurl('%s%s' % (ROOTURL, altmatch[0]), opener)
            
            groups = re_itemsubcategoryaltdetails.search(listdata)
            desc = cleanstr(groups.group('desc')).strip()
            insertsubcategory(altsubcategory, desc)
            
            attributes = []
            attribute = groups.group('class')
            if attribute:
                attribute = '%s Only' % attribute.strip()
                insertattribute(attribute)
                attributes.append((attribute, 0, 0, 'NONE'))
                
            parseitemlist(category, subcategory, altsubcategory, listdata, attributes)
            
def parseitemlist(category, subcategory, altsubcategory, data, attributes):
    ''' Parse a list of items
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
        prepprocess(category, subcategory, altsubcategory, attributes, groups.group('image'), groups.group('item'))

def prepprocess(category, subcategory, altsubcategory, attributes, image, url):
    ''' Prepare a process to scrape all items in a specific altsubcategory page
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type url: str
    '''
    msg('Preparing process: %s, %s, %s' % (category, subcategory, altsubcategory))
    processes.append(multiprocessing.Process(target = parseitem,
                                             args = (craftstatements,
                                                     craftmaterialstatements,
                                                     attributestatements,
                                                     category,
                                                     subcategory,
                                                     altsubcategory,
                                                     attributes, 
                                                     image,
                                                     url
                                                     )))
    processes[-1].start()
    msg('Process running(%d): %s, %s, %s' % (processes[-1].pid, category, subcategory, altsubcategory))

def parseitem(cs, cms, ats, category, subcategory, altsubcategory, attributes, image, url):
    ''' Parse item data and store the item details (this is where the magic happens)
    @type cs: multiprocessing.Queue
    @type cms: multiprocessing.Queue
    @type ats: multiprocessing.Queue
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type attributes: list
    @type image: str
    @type url: str
    '''

    od = makeod()
    dlimage(image, od)
    data = readurl('%s%s' % (ROOTURL, url), od)
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

        linkcraft(cs, craftitemname, itemid, craftat, level, cost)
        
        # Handle crafting materials
        materials = re_craftmaterials.findall(materialsdata)
        msg('Materials found for %s: %d' % (name, len(materials)))
        for material in materials:
            url = material[0]
            quantity = material[1]
            linkcraftmaterial(cms, itemid, url, quantity)      
        
    # Normal cases
    else:       
        groups = re_itemdetails.search(data)
        
        name = cleanstr(groups.group('name')).strip()
        level = groups.group('level')
        attrdata = groups.group('data')
        desc = parseattributes(attrdata, attributes)
        
        itemid = insertitem(name, desc, os.path.basename(image), category, level, url)
    
    if itemid:
        if subcategory:
            linkitemsubcategory(itemid, subcategory)
        linkitemsubcategory(itemid, altsubcategory)
        
        for attribute in attributes:
            linkitemattribute(ats, itemid, attribute[0], attribute[1], attribute[2], attribute[3])
            
def parseattributes(data, attributes):
    ''' Parse item attributes and add to list, return description if found
    @type data: str
    @type attributes: list
    '''
    rval = ''
    
    groups = re_itemattr.search(data)
    if groups:
        val = groups.group('type')
        if val:
            attrname = cleanstr(re_striptags.sub('', val).strip())
            insertattribute(attrname)
            attributes.append([attrname, 0, 0, 'NONE'])
            
        val = groups.group('armorweapon')
        if val:
            pass
            
        val = groups.group('desc')
        if val:
            rval = re_striptags.sub('', val).strip().replace('\s+', ' ')
            
        val = groups.group('effects')
        if val:
            pass
            
        val = groups.group('set')
        if val:
            pass
            
        val = groups.group('extras')
        if val:
            pass
    else:
        msg('ERROR: Something went wrong parsing item attributes')
    return rval

def dlimage(url, od):
    ''' Download an image at url
    @type url: str
    @type od: urllib2.OpenerDirector
    '''
    fd = open(os.path.join(directory, os.path.basename(url)), 'w')
    fd.write(readurl(url, od, 30))
    fd.close()

def linkitemattribute(ats, itemid, attribute, minv, maxv, typev):
    ''' Link an item and an attribute
    @type ats: multiprocessing.Queue
    @type itemid: str
    @type attribute: str
    @type minv: float
    @type maxv: float
    @type typev: str
    '''
    msg('Pushing to itemattribute queue(size %d)' % ats.qsize())
    ats.put((int(itemid), float(minv), float(maxv), unicode(typev), unicode(attribute)))

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

def linkcraft(cs, craftitemname, itemid, craftat, level, cost):
    ''' Link a craft to items 
    @type cs: multiprocessing.Queue
    @type craftitemname: str
    @type itemid: str
    @type craftat: str
    @type level: int
    @type cost: int
    '''
    msg('Pushing to craft queue(size %d)' % cs.qsize())
    cs.put((int(itemid), unicode(craftat), int(level), int(cost), unicode(craftitemname)))

def linkcraftmaterial(cms, craftid, itemurl, quantity):
    ''' Link a craft to items 
    @type cms: multiprocessing.Queue
    @type craftid: str
    @type itemurl: str
    @type quantity: int
    '''
    msg('Pushing to material queue(size %d)' % cms.qsize())
    cms.put((int(craftid), int(quantity), unicode(itemurl)))

def insertitem(name, desc, image, category, level, url):
    ''' Insert an item in to the db, return the new id
    @type name: str
    @type desc: str
    @type image: str
    @type category: str
    @type level: int
    @type url: str
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

def readurl(url, od, timeout = TIMEOUT):
    ''' Read a URL and return the HTML data
    @type url: str
    @type od: urllib2.OpenerDirector
    @type timeout: int
    '''
    requestheaders = {}
    data = ''
    responseheaders = []
    
    while(True):
        msg('Requesting: %s' % url)
        
        req = urllib2.Request(url, headers = headers)
        
        if requestheaders:
            req.add_data(urllib.urlencode(requestheaders))
            requestheaders = {}
        
        res = None
        try:
            res = od.open(req, timeout = timeout)
        except urllib2.HTTPError as e:
            msg('Error getting url(%d): %s' % (e.code, url))
            continue
        except urllib2.URLError as e:
            msg('Error getting url(%s): %s' % (e.reason, url))    
            continue
        except socket.timeout as e:
            msg('Error getting url(%s): %s' % (e.message, url))    
            continue
        except Exception as e:
            msg('Error getting url(%s): %s' % (e.message, url))
            continue
        
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
    # Comment/uncomment the next line to disable/enable using a proxy
    #rval.add_handler(urllib2.ProxyHandler({'http': '24.139.43.249:8085'}))
    
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
    
    # Item-Attribute
    cursor.execute(
    '''CREATE TABLE itemattribute(
    itemid INTEGER,
    attributeid INTEGER,
    min REAL,
    max REAL,
    type TEXT,
    FOREIGN KEY(itemid) REFERENCES item(id),
    FOREIGN KEY(attributeid) REFERENCES attribute(id),
    CHECK (type IN ("PLUS", "PCNT", "VALU", "NONE"))
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
    statements = ('INSERT OR IGNORE INTO craft SELECT id, ?, ?, ?, ? FROM item WHERE name = ?',
                  'INSERT OR IGNORE INTO craftmaterial SELECT ?, id, ? FROM item WHERE url = ?',
                  'INSERT OR IGNORE INTO itemattribute SELECT ?, id, ?, ?, ? FROM attribute WHERE name = ?')
    
    msg('%d delayed craft statements' % craftstatements.qsize())
    msg('%d delayed material statements' % craftmaterialstatements.qsize())
    msg('%d delayed itemattribute statements' % attributestatements.qsize())
    cursor = db.cursor()
    while(not craftstatements.empty()):
        data = craftstatements.get()
        cursor.execute(statements[0], data)
        
    while(not craftmaterialstatements.empty()):
        data = craftmaterialstatements.get()
        cursor.execute(statements[1], data)
        
    while(not attributestatements.empty()):
        data = attributestatements.get()
        cursor.execute(statements[2], data)
    db.commit() 
    cursor.close()    

if __name__ == '__main__':
    scrape()