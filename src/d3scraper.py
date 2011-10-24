#!/usr/bin/python
import re, urllib2, sqlite3, gzip, StringIO, os, multiprocessing
from xml.dom import minidom
from time import time

ROOTURL = 'http://us.battle.net'
D3ITEMPAGE = '%s/d3/en/item/' % ROOTURL

db = None
basetime = 0

processes = []

manager = multiprocessing.Manager()
dblock = manager.Lock()

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

#Main regexs
re_itemcategoryblock = re.compile(r'<div class="(?P<class>column-[0-9])">', re.DOTALL)
re_itemcategory = re.compile(r'<div class="column-[0-9]">.*?<h3 class="category ">(?P<category>.*?)</h3>(?P<data>.*)</div>', re.DOTALL)
re_itemsubcategory = re.compile(r'<div class="box">(?:\s*?<h4 class="subcategory ">(?P<subcategory>.*?)</h4>|(?P<subcategory2>\s*?))(?P<data>.*?)</div>', re.DOTALL)
re_itemsubcategoryalt = re.compile(r'<a.*?href="(?P<href>.*?)">(?P<subcategory>.*?)(?:<span.*?</span>.*?)?</a>', re.DOTALL)

#Process regexs
re_itemsubcategoryaltdetails = re.compile(r'(?:<span class="item-class-specific">.*?>(?P<class>.*?)</a>.*?)?<div class="desc">(?P<desc>.*?)</div>', re.DOTALL)
re_itemitem = re.compile(r'(?P<item><tr class="row[0-9].*?</tr>)', re.DOTALL)

def scrape():
    ''' Begin the scraping process
    '''
    
    global basetime
    basetime = time()
    
    global opener
    opener = makeod()
    
    filename = '%d-%s.sqlite' % (basetime, os.getpid())
    
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
        
        msg('Closing db')
        db.close()
        
        msg('Finished\t\t\tDB file is %s' % filename)
    except Exception, e:
        msg('Error! %s' % e.message)
        
        for process in processes:
            msg('Killing process: %d' % process.pid)
            process.terminate()
    
def parsecategories(data):
    ''' Parse main categories
    @type data: str
    '''
    msg('Parsing categories')
    
    #Need to use a dom due to a few inconsistencies that get in the way of simple regexs
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
            
        #Parse alt subcategories
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
                                             args = (category,
                                                     subcategory,
                                                     altsubcategory,
                                                     url
                                                     )))
    processes[-1].start()
    msg('Process running(%d): %s, %s, %s' % (processes[-1].pid, category, subcategory, altsubcategory))
    
def itemlistscraper(category, subcategory, altsubcategory, url):
    ''' Load the url and parse each item
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type url: str
    '''
    od = makeod()
    data = readurl('%s%s' % (ROOTURL, url), od)
    
    groups = re_itemsubcategoryaltdetails.search(data)
    #Swap out two unicode chars blizzard seems to like to use instead of ascii equivalents
    desc = unicode(groups.group('desc').decode('utf-8')).replace(u'\u2019', '\'').replace(u'\u2013', '-').strip()
    insertsubcategory(altsubcategory, desc)
    
    attributes = []
    attribute = groups.group('class')
    if attribute:
        attributes.append(insertattribute('%s Only' % attribute.strip()))
        
    parseitemlist(category, subcategory, altsubcategory, data, attributes)

def parseitemlist(category, subcategory, altsubcategory, data, attributes):
    ''' Parse a list of items
    @type category: str
    @type subcategory: str
    @type altsubcategory: str
    @type data: str
    @type attributes: list
    '''
    matches = re_itemitem.findall(data)
    if matches:
        msg('%s, %s, %s: Found %d item(s)' % (category, subcategory, altsubcategory, len(matches)))
    else:
        msg('%s, %s, %s: No matches found, did something go wrong?' % (category, subcategory, altsubcategory))
    
    for match in matches:
        pass

def insertsubcategory(name, desc):
    ''' Insert a subcategory in to the db, return the new id
    @type name: str
    @type desc: str
    '''
    dblock.acquire()
    cursor = db.cursor()
    cursor.execute('INSERT OR IGNORE INTO subcategory VALUES(NULL, ?, ?)', (unicode(name), unicode(desc)))
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
    cursor.execute('INSERT OR IGNORE INTO attribute VALUES(NULL, ?)', (unicode(name),))
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
    msg('Requesting: %s' % url)
    
    req = urllib2.Request(url, None, headers)
    
    res = od.open(req)
    
    data = res.read()
    
    responseheaders = res.info()
    
    if 'content-encoding' in responseheaders.keys() and responseheaders['content-encoding'] == 'gzip':
        sfd = StringIO.StringIO(data)
        gzfd = gzip.GzipFile(fileobj = sfd)
        data = gzfd.read()
        gzfd.close()
        sfd.close()
    
    return data

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
    
    ###Tables
    
    #Category
    cursor.execute(
    '''CREATE TABLE category(
    id INTEGER PRIMARY KEY, 
    name TEXT UNIQUE
    )''')
    
    #Subcategory
    cursor.execute(
    '''CREATE TABLE subcategory(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    desc TEXT
    )''')
    
    #Item
    cursor.execute(
    '''CREATE TABLE item(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
    )''')
    
    #Attribute
    cursor.execute(
    '''CREATE TABLE attribute(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
    )''')    
    
    db.commit()
    cursor.close()
    
if __name__ == '__main__':
    scrape()