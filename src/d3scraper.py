#!/usr/bin/python
import os, urllib2, sqlite3, multiprocessing, StringIO, gzip, urllib, socket
from time import time
from lxml import etree

class d3scraper(object):
    ROOTURL = 'http://us.battle.net'
    D3ITEMPAGE = '%s/d3/en/item/' % ROOTURL
    TIMEOUT = 15
    NSREMOVE = 'xmlns="http://www.w3.org/1999/xhtml"'
    NUMPROC = 24
    
    db = None
    dblock = multiprocessing.Lock()
    basetime = 0
    directory = ''
    pool = None
    
    badchars = {u'\u2019': '\'', u'\u2013': '-'}
    
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

    def __init__(self):
        self.basetime = time()
        

    def scrape(self):
        ''' Begin the scraping process
        '''
        
        self.pool = multiprocessing.Pool(self.NUMPROC)
        self.opener = self.makeod()
        
        self.directory = '%d-%s' % (self.basetime, os.getpid())
        os.mkdir(self.directory)
        filename = os.path.join(self.directory, 'db.sqlite')
        
        try:
            self.msg('Starting up')
            global db
            db = sqlite3.connect(filename)
            self.initdb(db)
            
            self.pool.join()
            
            self.msg('Closing db')
            db.close()
            
            self.msg('Finished\t\t\tDB file is %s' % filename)
        except Exception as e:
            self.msg('Error %s' % e.message)
        
    def parsecategories(self, text):
        cats = []
        
        xml = etree.fromstring(text)
        for element in xml.xpath('//div[@id="equipment"]/div'):
            name = element.xpath('h3[@class="category "]')[0].text
            cats.append((name, etree.tostring(element)))
        
        return cats
    
    def parsesubcategories(self, text):
        subcats = []
        
        xml = etree.fromstring(text)
        for element in xml.xpath('//div[@class="box"]'):
            subcategory = element.xpath('h4[@class="subcategory "]')
            subcatlist = []
            if len(subcategory):
                subcatlist.append(subcategory[0].text.strip())
            
            for a in element.xpath('.//a'):
                subcatlist.append(a.text.strip())
                url = a.attrib['href']
                
                subcats.append((url, subcatlist, etree.tostring(element)))

        return subcats
    
    def parsesubcategory(self, text):
        items = []
        
        xml = etree.fromstring(text)
        items.append(xml.xpath('//div[@class="browse-right"]/div[@class="page-header"]/div[@class="desc"]')[0].text.strip())
        
        items.append([])
        for element in xml.xpath('//div[@id="table-items"]//tbody//div[@class="item-details-icon"]//a'):
            items[1].append(element.attrib['href'])
        
        return items
    
    def dlimage(self, url, od):
        ''' Download an image at url
        @type url: str
        @type od: urllib2.OpenerDirector
        '''
        fd = open(os.path.join(self.directory, os.path.basename(url)), 'w')
        fd.write(self.readurl(url, od, 30))
        fd.close()
    
    def linkitemattribute(self, ats, itemid, attribute, minv, maxv, typev):
        ''' Link an item and an attribute
        @type ats: multiprocessing.Queue
        @type itemid: str
        @type attribute: str
        @type minv: float
        @type maxv: float
        @type typev: str
        '''
        self.msg('Pushing to itemattribute queue(size %d)' % ats.qsize())
        ats.put((int(itemid), float(minv), float(maxv), unicode(typev), unicode(attribute)))
    
    def linkitemsubcategory(self, itemid, subcategory):
        ''' Link an item and a subcategory
        @type itemid: str
        @type subcategory: str
        '''
        self.dblock.acquire()
        cursor = db.cursor()
        cursor.execute('INSERT OR IGNORE INTO itemsubcategory SELECT ?, id FROM subcategory WHERE name = ?', 
                       (int(itemid), unicode(subcategory)))
        db.commit() 
        cursor.close()    
        self.dblock.release()
    
    def linkcraft(self, cs, craftitemname, itemid, craftat, level, cost):
        ''' Link a craft to items 
        @type cs: multiprocessing.Queue
        @type craftitemname: str
        @type itemid: str
        @type craftat: str
        @type level: int
        @type cost: int
        '''
        self.msg('Pushing to craft queue(size %d)' % cs.qsize())
        cs.put((int(itemid), unicode(craftat), int(level), int(cost), unicode(craftitemname)))
    
    def linkcraftmaterial(self, cms, craftid, itemurl, quantity):
        ''' Link a craft to items 
        @type cms: multiprocessing.Queue
        @type craftid: str
        @type itemurl: str
        @type quantity: int
        '''
        self.msg('Pushing to material queue(size %d)' % cms.qsize())
        cms.put((int(craftid), int(quantity), unicode(itemurl)))
    
    def insertitem(self, name, desc, image, category, level, url):
        ''' Insert an item in to the db, return the new id
        @type name: str
        @type desc: str
        @type image: str
        @type category: str
        @type level: int
        @type url: str
        '''
        self.dblock.acquire()
        cursor = db.cursor()
        cursor.execute('INSERT OR IGNORE INTO item SELECT NULL, ?, ?, ?, id, ?, ? FROM category WHERE name = ?', 
                       (unicode(name), unicode(desc), unicode(image), int(level), unicode(url), unicode(category)))
        rval = cursor.lastrowid
        db.commit() 
        cursor.close()    
        self.dblock.release()
        
        return rval    
    
    def insertsubcategory(self, name, desc):
        ''' Insert a subcategory in to the db, return the new id
        @type name: str
        @type desc: str
        '''
        self.dblock.acquire()
        cursor = db.cursor()
        cursor.execute('INSERT OR IGNORE INTO subcategory VALUES(NULL, ?, ?)', 
                       (unicode(name), unicode(desc)))
        rval = cursor.lastrowid
        db.commit() 
        cursor.close()    
        self.dblock.release()
        
        return rval
        
    def insertattribute(self, name):
        ''' Insert an attribute in to the db, return the new id
        @type name: str
        '''
        self.dblock.acquire()
        cursor = db.cursor()
        cursor.execute('INSERT OR IGNORE INTO attribute VALUES(NULL, ?)', 
                       (unicode(name),))
        rval = cursor.lastrowid
        db.commit() 
        cursor.close()    
        self.dblock.release()
        
        return rval
        
    def msg(self, text):
        ''' Print out a message with a duration time in seconds
        @type text: str
        '''
        print '[%3d] %s' % (time() - self.basetime, text)
    
    def readurl(self, url, od, timeout = TIMEOUT):
        ''' Read a URL and return the HTML data
        @type url: str
        @type od: urllib2.OpenerDirector
        @type timeout: int
        '''
        requestheaders = {}
        data = ''
        responseheaders = []
        
        while(True):
            self.msg('Requesting: %s' % url)
            
            req = urllib2.Request(url, headers = self.headers)
            
            if requestheaders:
                req.add_data(urllib.urlencode(requestheaders))
                requestheaders = {}
            
            res = None
            try:
                res = od.open(req, timeout = timeout)
            except urllib2.HTTPError as e:
                self.msg('Error getting url(%d): %s' % (e.code, url))
                continue
            except urllib2.URLError as e:
                self.msg('Error getting url(%s): %s' % (e.reason, url))    
                continue
            except socket.timeout as e:
                self.msg('Error getting url(%s): %s' % (e.message, url))    
                continue
            except Exception as e:
                self.msg('Error getting url(%s): %s' % (e.message, url))
                continue
            
            # Normal case
            if not 'd3/en/age' in res.geturl():
                data = res.read()
                responseheaders = res.info()
                break
            # Agegate
            else:
                self.msg('Submitting to age gate')
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
    
    def cleanstr(self, string):
        ''' Remove some unicode chars blizzard uses
        @type string: str
        '''
        newstr = unicode(string.decode('utf-8'))
        for (key, value) in self.badchars.items():
            newstr = newstr.replace(key, value)
            
        return newstr
    
    def makeod(self):
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
    
    def initdb(self, db):
        ''' Initialize the database structure
        @type db: sqlite3.Connection
        '''
        
        self.msg('Init db')
        
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

if __name__ == '__main__':
    d3scraper().scrape()