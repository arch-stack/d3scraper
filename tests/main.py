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