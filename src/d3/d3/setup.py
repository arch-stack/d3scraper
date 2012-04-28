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
            category VARCHAR(100) UNICODE,
            subcategory VARCHAR(100) UNICODE,
            name VARCHAR(100) UNICODE,
            url VARCHAR(200) UNICODE,
            PRIMARY KEY(id)
        )
        ENGINE = InnoDB,
        AUTO_INCREMENT = 0
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INT AUTO_INCREMENT,
            category VARCHAR(100) UNICODE,
            subcategory VARCHAR(100) UNICODE,
            name VARCHAR(100) UNICODE,
            itemtype VARCHAR(100) UNICODE,
            level INT UNSIGNED,
            imgbarb VARCHAR(250) UNICODE,
            imgdh VARCHAR(250) UNICODE,
            imgmonk VARCHAR(250) UNICODE,
            imgwd VARCHAR(250) UNICODE,
            imgwizard VARCHAR(250) UNICODE,
            url VARCHAR(250) UNICODE,
            PRIMARY KEY(id)
        )
        ENGINE = InnoDB,
        AUTO_INCREMENT = 0
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS details (
            id INT AUTO_INCREMENT,
            detail VARCHAR(2000) UNICODE,
            itemid INT,
            type ENUM('stat', 'effect', 'extra'),
            PRIMARY KEY(id),
            FOREIGN KEY(itemid) REFERENCES items(id)
        )
        ENGINE = InnoDB,
        AUTO_INCREMENT = 0
    ''')
    db.commit()
    
    cursor.close()
    db.close()

if __name__ == '__main__':
    setup()