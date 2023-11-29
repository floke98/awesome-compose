import os
from flask import Flask, render_template, redirect, json, request, send_from_directory, session, jsonify
import mysql.connector
import csv
import pickle
import re
from mouser_api import ApiSearch

server = Flask(__name__)
server.run(debug=True)
conn = None

class DBManager:
    def __init__(self, database='example', host="db", user="root", password_file=None):
        pf = open(password_file, 'r')

        try:
            self.connection = mysql.connector.connect(
                user=user,
                password=pf.read(),
                host=host, # name of the mysql service as set in the docker compose file
                database=database,
                auth_plugin='mysql_native_password'
            )
        except Exception as error:
            print("ERROR. Connection to DB not established\n{}".format(error))

        pf.close()
        self.cursor = self.connection.cursor(dictionary=True)

        if checkFirstRun():
            self.populate_db()
    
    def populate_db(self):
        if not self.cursor:
            DBManager(password_file='/run/secrets/db-password')

        # write the pickle flag after initialising the db
        with open('./Flag.pkl', 'wb') as f:
            pickle.dump("1", f)

        file = open('partList.csv', 'r')
        partList = csv.DictReader(file)

        partIds = []
        for col in partList:
            partIds.append(col['id'])

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
        for row in self.cursor:
            new_id = row['id']

        self.connection.commit()
        return new_id

    def searchById_db(self, search_id, quick):
        self.cursor.execute('SELECT mouserId FROM parts WHERE id=(%s);', [search_id])
        mouser_id = ""
        dic = {}
        for row in self.cursor:
            mouser_id = row['mouserId']

        if not quick and len(mouser_id) > 1:
            dic = ApiSearch(mouser_id)

        return dic, mouser_id

    def searchByMouserId_db(self, mouser_id):
        self.cursor.execute('SELECT id FROM parts WHERE mouserId=(%s);', [mouser_id])
        my_id = -1
        for row in self.cursor:
            my_id = row['id']

        return my_id

    def selectAll_db(self):
        self.cursor.execute('SELECT * FROM parts ORDER BY id ASC;')
        return self.cursor.fetchall()

@server.route('/<search_id>')
def fullSearch(search_id):
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')

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
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')

    search_id = request.json['search_id']
    response, mouser_id = conn.searchById_db(search_id, True)

    if not mouser_id:
        return jsonify (dict({'status' : 'fail'}))
    return jsonify (dict({'status' : 'success', 'id' : search_id }))

@server.route('/all')
def printAll():
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')

    rows = conn.selectAll_db()
    dic = {}
    for row in rows:
        dic[row["id"]] = row["mouserId"]

    dic_keyBeatify = ["Id", "Mouser Id"]

    return render_template('print_all.html', rows = dic, headrow = dic_keyBeatify)


@server.route('/add', methods=['POST'])
def addNewItem():
    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')

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

    return render_template("home.html")

@server.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")

def checkFirstRun():
    if os.path.isfile('./Flag.pkl'):
        with open('./Flag.pkl', 'rb') as f:
            return pickle.load(f)
    else:
        return 0

@server.route('/save', methods = ['GET'])
def saveDb():

    # todo, but could not be bad to refill the db sometimes
    # clear the pickle file, for reinitialising the db connection afterwards
    with open('./Flag.pkl', 'wb') as f:
        pickle.dump("1", f)

    global conn
    if not conn:
        conn = DBManager(password_file='/run/secrets/db-password')

    rows = conn.selectAll_db()
    file = open('partList.csv', 'w')
    write = csv.writer(file)

    write.writerow("id")
    for row in rows:
        write.writerow(row["mouserId"])
    file.close()

    return jsonify(dict({'status' : 'success'}))

if __name__ == '__main__':
    server.run()
