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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INT AUTO_INCREMENT,
            category NVARCHAR(100),
            subcategory NVARCHAR(100),
            name NVARCHAR(100),
            itemtype NVARCHAR(100),
            level INT UNSIGNED,
            imgbarb NVARCHAR(250),
            imgdh NVARCHAR(250),
            imgmonk NVARCHAR(250),
            imgwd NVARCHAR(250),
            imgwizard NVARCHAR(250),
            url NVARCHAR(250),
            PRIMARY KEY(id)
        )
        ENGINE = InnoDB,
        AUTO_INCREMENT = 0
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS details (
            id INT AUTO_INCREMENT,
            detail NVARCHAR(2000),
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