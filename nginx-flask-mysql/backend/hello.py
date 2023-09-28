import os
from flask import Flask, render_template, redirect, json, request, send_from_directory, session, jsonify
import mysql.connector
import csv
import re
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
                            'mouserId VARCHAR(40))')
        for i in range(len(partIds)):
            self.cursor.execute('INSERT INTO parts (mouserId) VALUES (%s);', [partIds[i]])

        self.connection.commit()

    def insert_db(self, mouser_id):
        self.cursor.execute('INSERT INTO parts (mouserId) VALUES (%s);', [mouser_id])
        self.cursor.execute('SELECT id FROM parts where mouserId=(%s);', [mouser_id])

        new_id = -1
        for c in self.cursor:
            new_id = c[0]

        self.connection.commit()
        return new_id



    def searchById_db(self, search_id, quick):
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

        if not quick and len(mouser_id) > 1:
            dic = ApiSearch(mouser_id)

        return dic, mouser_id

    def searchByMouserId_db(self, mouser_id):
        self.cursor.execute('SELECT id FROM parts WHERE mouserId=(%s);', [mouser_id])
        myId = -1
        for c in self.cursor:
            myId = c[0]
        if myId > -1:
            return myId
        else:
            return -1

@server.route('/<search_id>')
def fullSearch(search_id):
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()

    try:
        int(search_id)
    except ValueError:
        return "No Valid ID"
    search_id = int(search_id)

    if search_id < 0 or search_id > 255:
        return "No Valid ID"

    request, mouser_id = conn.searchById_db(search_id, False)
    if not request:
        # goto not found page
        return "NOT FOUND"

    dic = {}
    dic_links = {}
    dic['id'] = search_id
    dic['mouser_id'] = mouser_id
    dic['description'] = request["SearchResults"]["Parts"][0]["Description"]
    dic['manufacturer'] = request["SearchResults"]["Parts"][0]["Manufacturer"]
    dic['man_partNumber'] = request["SearchResults"]["Parts"][0]["ManufacturerPartNumber"]

    dic_links['url'] = request["SearchResults"]["Parts"][0]["ProductDetailUrl"]
    dic_links['datasheet_url'] = request["SearchResults"]["Parts"][0]["DataSheetUrl"]

    dic_keyBeatify = ["Id", "Mouser Id", "Description", "Manufact.", "Manufact. Nr.", "Link", "Datasheet"]

    return render_template('search_result.html', values = dic.values(), headrow = dic_keyBeatify, links = dic_links.values())

@server.route('/search', methods = ['POST'])
def quickSearch():
    search_id = request.json['search_id']
    response, mouser_id = conn.searchById_db(search_id, True)

    if not mouser_id:
        return jsonify (dict({'status' : 'fail'}))
    return jsonify (dict({'status' : 'success', 'id' : search_id }))


@server.route('/add', methods=['POST'])
def addNewItem():
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()

    # check for  already existing
    mouser_id = request.json['add_id']

    exists =  conn.searchByMouserId_db(mouser_id)
    if exists > -1:
        return jsonify (dict({'status' : 'exists', 'id' : exists}))

    # check for valid mouser id
    dic = ApiSearch(mouser_id)

    if dic['SearchResults']['NumberOfResult'] > 1 or dic['SearchResults']['NumberOfResult'] < 0:
        return jsonify (dict({'status' : 'fail'}))

    # insert
    new_id = conn.insert_db(mouser_id)
    if new_id > -1:
        return jsonify (dict({'status' : 'success', 'id' : new_id}))
    else:
        return jsonify(dict({'status': 'fail'}))

@server.route('/')
def listBlog():
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')
        conn.populate_db()

    return render_template("home.html")

@server.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")

if __name__ == '__main__':
    server.run()
