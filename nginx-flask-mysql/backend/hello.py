import os
from flask import Flask, redirect, json, request, send_from_directory, session, jsonify, render_template
import mysql.connector
import csv
from mouser_api import ApiSearch

server = Flask(__name__)
conn = None

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

        self.cursor.execute('DROP TABLE IF EXISTS parts')

        self.cursor.execute('CREATE TABLE parts ('
                            'id INT AUTO_INCREMENT PRIMARY KEY, '
                            'mouserId VARCHAR(255))')
        for i in range(len(partIds)):
            self.cursor.execute('INSERT INTO parts (mouserId) VALUES (%s);', [partIds[i]])

        self.connection.commit()
    
    def queryDb(self, search_id):
        self.cursor.execute('SELECT mouserId FROM parts WHERE id=(%s);', [search_id])
        # rec = []
        # for c in self.cursor:
        #     rec.append(str(c[0]))
        #     rec.append(c[1])
        # return rec
        mouser_id = ""
        dic = {}
        for c in self.cursor:
            mouser_id = c[0]

        if len(mouser_id) > 1:
            dic = ApiSearch(mouser_id)

        return dic, mouser_id

@server.route('/<search_id>')
def listItem(search_id):
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()

    request, mouser_id = conn.queryDb(search_id)
    if not request:
        # goto not found page
        return "NOT FOUND"

    dic = {}
    dic['id'] = search_id
    dic['mouser_id'] = mouser_id
    dic['description'] = request["SearchResults"]["Parts"][0]["Description"]
    dic['manufacturer'] = request["SearchResults"]["Parts"][0]["Manufacturer"]
    dic['man_partNumber'] = request["SearchResults"]["Parts"][0]["ManufacturerPartNumber"]
    dic['url'] = request["SearchResults"]["Parts"][0]["ProductDetailUrl"]
    dic['datasheet_url'] = request["SearchResults"]["Parts"][0]["DataSheetUrl"]

    response = "<div>"
    for item in dic.values():
        response = response + str(item) + '<br>'
    response = response + '</div>'

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

    return render_template("home.html")

    response = 'Search for parts by inserting the ID in the link url like example.at/yourSearchId  <br><br>'
    response = response + 'Add new parts: <input type="submit" value="ADDER" onclick="window.location=\'/add\';" />'

    return response

@server.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")

if __name__ == '__main__':
    server.run()
