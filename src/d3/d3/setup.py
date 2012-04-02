#!/usr/bin/python
import sys

sys.path.append('.')

import MySQLdb
from d3.config import Config

def setup():
    db = MySQLdb.connect(host = Config.mysqlserver, user = Config.mysqlusername, 
                         passwd = Config.mysqlpassword, db = Config.mysqldatabase)
    cursor = db.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foundtypes (
            id INT AUTO_INCREMENT,
            category NVARCHAR(100),
            subcategory NVARCHAR(100),
            name NVARCHAR(100),
            url NVARCHAR(200),
            PRIMARY KEY(id)
        )
        ENGINE = InnoDB,
        AUTO_INCREMENT = 0
    ''')
    db.commit()
    
    cursor.close()
    db.close()

if __name__ == '__main__':
    setup()