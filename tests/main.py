import unittest, sqlite3
from src.d3scraper import d3scraper

class Testd3scraper(unittest.TestCase):
    def setUp(self):
        self.d3 = d3scraper()
    
    def tearDown(self):
        pass
    
    def test_cleanstr(self):
        badstr = ''.join(self.d3.badchars.keys())
        goodstr = self.d3.cleanstr(badstr)
        matches = len(set(badstr) & set(goodstr))
        self.assertFalse(matches, 'Bad chars still found: {0} {1} {2}'.format(str(matches), str(badstr), str(goodstr)))
        
    def test_makeod(self):
        od = self.d3.makeod()
        self.assertTrue(od, 'OD was not created')
        self.assertEqual(od.open('http://google.ca').getcode(), 200, 'OD could not access google')
        
    def test_parsecategories(self):
        fd = open('data/categories.html', 'r')
        data = fd.read()
        fd.close()
        
        res = self.d3.parsecategories(data)
        
        self.assertEqual(len(res), 3, 'Wrong number of categories %d' % len(res))
        self.assertEqual(res[0][0], 'Armor', 'First category\'s text is wrong %s' % res[0][0])
        
    def test_parsesubcategories(self):
        fd = open('data/categories.html', 'r')
        data = fd.read()
        fd.close()
        
        res = self.d3.parsesubcategories(data)
        
        self.assertEqual(len(res), 52, 'Wrong number of subcategories found %d' % len(res))
                
        for subcat in res:
            self.assertNotEqual(subcat[0], '', 'URL is blank')
            self.assertTrue(len(subcat[1]) > 0, 'No subcategories on a subcategory')
            
        self.assertEqual(res[0][1][0], 'Head', 'First subcategory\' primary subcategory is wrong %s' % res[0][1][0])
        self.assertEqual(res[0][1][1], 'Helms', 'First subcategory\' secondary subcategory is wrong %s' % res[0][1][1])

    def test_parsesubcategory(self):
        fd = open('data/subcategory.html', 'r')
        data = fd.read()
        fd.close()
        
        res = self.d3.parsesubcategory(data)
        
        self.assertEqual(res[0], 'Helms have a common enough purpose: to protect the vulnerable, fleshy parts of the head from skull cracks, and make gouging eyes out a bit harder. Sturdier helms can weigh quite a bit in exchange for providing ample protection.', 'Description is incorrect')
        self.assertEqual(len(res[1]), 43, 'Incorrect number of items found %d' % len(res[1]))


class TestDB(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        if self.db:
            d3scraper().initdb(self.db)

    def tearDown(self):
        self.db.close()

    def test_DBStructure(self):
        queries = {
                   'category': "0, 'test'",
                   'subcategory': "0, 'test', ''",
                   'item': "0, 'test', '', '', 0, 0, ''",
                   'attribute': "0, 'test'",
                   'itemattribute': "0, 0, 0.0, 1.1, 'PLUS'",
                   'itemsubcategory': "0, 0",
                   'craft': "0, 0, 'test', 0, 0",
                   'craftmaterial': "0, 0, 1"
                   }
        
        cursor = self.db.cursor()
        
        for (table, values) in queries.items():
            cursor.execute('''
            INSERT OR IGNORE INTO ''' + table + '''
            VALUES (''' + values + ''')
            ''')
            
            cursor.execute('''
            SELECT *
            FROM ''' + table + '''
            ''')
            
            self.assertEqual(1, len(cursor.fetchall()), 'Incorrect results from ' + table + ' table')
        
        cursor.close()
        
        

if __name__ == "__main__":
    unittest.main()