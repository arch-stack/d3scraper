#!/usr/bin/python
import re, urllib2, sqlite3, gzip, StringIO, os
from time import time

ROOTURL = 'http://us.battle.net'
D3ITEMPAGE = '%s/d3/en/item/' % ROOTURL

opener = urllib2.build_opener()
opener.add_handler(urllib2.HTTPHandler())
opener.add_handler(urllib2.HTTPCookieProcessor())
opener.add_handler(urllib2.HTTPRedirectHandler())
opener.add_handler(urllib2.UnknownHandler())

headers = {
   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:7.0.1) Gecko/20100101 Firefox/7.0.1 Iceweasel/7.0.1',
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language': 'en-us,en;q=0.5',
   'Accept-Encoding': 'gzip, deflate',
   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
   'Connection': 'keep-alive',
   'Cache-Control': 'no-cache, no-cache',
   }

re_itemcategory = re.compile(r'<div class="column-[0-9]">.*?<h3 class="category ">(?P<category>.*?)</h3>(?P<data>.*?)</div>', re.DOTALL)
re_itemsubcategory = re.compile(r'<div class="box">.*?</div>', re.DOTALL)

def scrape():
    ''' Begin the scraping process
    '''
    db = sqlite3.connect('%s-%s.sqlite' % (int(time()), os.getpid()))
    initdb(db)
    
    data = readurl(D3ITEMPAGE, opener)
    
#    fd = open('/tmp/%f.txt' % time(), 'w')
#    fd.write(data)
#    fd.close()
    
    print len(re_itemcategory.findall(data))
    
    db.close()

def readurl(url, od):
    ''' Read a URL and return the HTML data
    @type url: str
    @type od: urllib2.OpenerDirector
    '''
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

def initdb(db):
    ''' Initialize the database structure
    @type db: sqlite3.Connection
    '''
    cursor = db.cursor()
    
    ###Tables
    
    #Category
    cursor.execute(
    '''CREATE TABLE category(
    id INTEGER PRIMARY KEY, 
    name TEXT
    )''')
    
    #Subcategory
    cursor.execute(
    '''CREATE TABLE subcategory(
    id INTEGER PRIMARY KEY,
    name TEXT
    )''')
    
    #Item
    cursor.execute(
    '''CREATE TABLE item(
    id INTEGER PRIMARY KEY,
    name TEXT
    )''')
    
    #Attribute
    cursor.execute(
    '''CREATE TABLE attribute(
    id INTEGER PRIMARY KEY,
    name TEXT
    )''')    
    
    db.commit()
    cursor.close()
    
if __name__ == '__main__':
    scrape()