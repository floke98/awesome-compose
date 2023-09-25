import os
from flask import Flask
import mysql.connector
import csv


class DBManager:
    def __init__(self, database='example', host="db", user="root", password_file=None):
        pf = open(password_file, 'r')
        self.connection = mysql.connector.connect(
            user=user, 
            password=pf.read(),
            host=host, # name of the mysql service as set in the docker compose file
            database=database,
            auth_plugin='mysql_native_password'
        )
        pf.close()
        self.cursor = self.connection.cursor()
    
    def populate_db(self):

        file = open('partList.csv', 'r')
        partList = csv.DictReader(file)

        partIds = []
        for col in partList:
            partIds.append(col['id'])
        print(partIds)

        self.cursor.execute('DROP TABLE IF EXISTS blog')
        self.cursor.execute('DROP TABLE IF EXISTS parts')

        self.cursor.execute('CREATE TABLE parts ('
                            'id INT AUTO_INCREMENT PRIMARY KEY, '
                            'mouserId VARCHAR(255))')
        for i in range(len(partIds)):
            self.cursor.execute('INSERT INTO parts (mouserId) VALUES (%s);', [partIds[i]])

        self.connection.commit()
    
    def query_titles(self, searchId):
        self.cursor.execute('SELECT id, mouserId FROM parts WHERE id=(%s);', [searchId])
        # rec = []
        # for c in self.cursor:
        #     rec.append(str(c[0]))
        #     rec.append(c[1])
        # return rec
        id = 0
        mouserId = ""
        for c in self.cursor:
            id = c[0]
            mouserId = c[1]
        return id, mouserId


server = Flask(__name__)
conn = None

@server.route('/<searchId>')
def listItem(searchId):
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()

    id, mouserId = conn.query_titles(searchId)


    response = '<div> Id | MouserId </div> <br>' + '<div>' + str(id) + '|' + mouserId + '</div>'
    return response

@server.route('/add')
def addNewItem():
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()

    return "HI I am the adder page"

@server.route('/')
def defaultPage():
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()
    response = 'Search for parts by inserting the ID in the link url like example.at/yourSearchId  <br><br>'
    response = response + 'Add new parts: <input type="submit" value="ADDER" onclick="window.location=\'/add\';" />'

    return response

if __name__ == '__main__':
    server.run()
