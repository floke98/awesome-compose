import os
from flask import Flask, render_template, redirect, json, request, send_from_directory, session, jsonify
import mysql.connector
from mysql.connector.errors import Error
import csv
import sys
import re
from mouser_api import ApiSearch

server = Flask(__name__)
server.run(debug=True)

# helper:
# https://stackoverflow.com/questions/13568508/python-mysql-handling-timeouts
# https://stackoverflow.com/questions/5504340/python-mysqldb-connection-close-vs-cursor-close
# https://stackoverflow.com/questions/26743103/how-to-check-the-connection-alive-in-python

#TODO
# outsource the dbmanager into another file
# cleanup

# ------------------------------------------------------------------------------
# Globals
# ------------------------------------------------------------------------------
db = None
def check_first_run():
    if os.path.isfile('./Flag.pkl'):
        with open('./Flag.pkl', 'rb') as f:
            return f.read()
    else:
        # print('File not exists but 0 returned', file=sys.stderr)
        return b'\x00'

# ------------------------------------------------------------------------------
# Database Class
# ------------------------------------------------------------------------------
class DBManager:
    # --------------------------------------------------------------------------
    # Private
    # --------------------------------------------------------------------------
    def __init__(self):
        self.connection = None
        self.cursor = None

        first_run = b'\x00'
        if os.path.isfile('./Flag.pkl'):
            with open('./Flag.pkl', 'rb') as f:
                first_run =  f.read()

        if first_run == b'\x00':
            self.populate_db()

    def __connect_to_db( self, attempts=3, database='example', host="db",
                    user="root", password_file="/run/secrets/db-password"):
        # check for a valid connection still holding,
            # should not happen too often
        try:
            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                return 1
        except Exception:
            pass

        pf = open(password_file, 'r')
        pw = pf.read()
        pf.close()

        while attempts > 0:
            attempts = attempts - 1
            try:
                conn = mysql.connector.connect(
                    user=user,
                    password=pw,
                    host=host, # name of the mysql service as set in the docker compose file
                    database=database,
                    auth_plugin='mysql_native_password'
                )
                if conn and conn.is_connected():
                    self.connection = conn
                    self.cursor = conn.cursor(dictionary=True)
                    print("\n OPENED a CONNECTION \n", file=sys.stderr)
                    return 1

            except Exception as error:
                print("ERROR. Connection to DB in attempt {0}, not established\n{1}".format(attempts, error), file=sys.stderr)
        self.connection = None
        self.cursor = None
        return 0
    def __execute_sql_query_db(self, sql_query, data=None):
        success = False
        num_affected_rows = 0
        return_val = None
        try:
            if self.__connect_to_db(attempts=1):
                if data is None or len(data) < 1:
                    num_affected_rows = self.cursor.execute(sql_query)
                else:
                    num_affected_rows = self.cursor.execute(sql_query, data)

                if 'SELECT' in sql_query:
                    try:
                        return_val = self.cursor.fetchall()
                    except Exception as e:
                        pass

                self.cursor.close()
                self.connection.commit()
                success = True
                print("During Query: {0}\n{1}\n".format(num_affected_rows, return_val), file=sys.stderr)
        except mysql.connector.Error as e:
            print("ERROR. Could not execute query!!\n{}{}".format(e.errno, e.msg), file=sys.stderr)

        return success, num_affected_rows, return_val

    def __execute_sql_query_with_retry_db(self, sql_query, data=None, attempts=3):
        success = False
        num_affected_rows = 0
        return_val = None

        if attempts < 1:
            return (False, 0, None)
        attempts_after_this = attempts - 1

        try:
            (success, num_affected_rows, return_val) = self.__execute_sql_query_db(sql_query, data)
        except BaseException as e:
            success = False

        if success:
            return success, num_affected_rows, return_val
        else:
            return self.__execute_sql_query_with_retry_db(sql_query, data, attempts_after_this)

    # --------------------------------------------------------------------------
    # Public Functions
    # --------------------------------------------------------------------------
    def close_after_every_use_db(self):
        try:
            self.cursor.close()
        except Exception as error:
            print("ERROR. Cant close cursor!\n{}".format(error), file=sys.stderr)

        try:
            self.connection.close()
            print("\n CLOSED THE CONNECTION \n", file=sys.stderr)
        except Exception as error:
            print("ERROR. Cant close connection!\n{}".format(error), file=sys.stderr)

    def populate_db(self):
        if not self.__connect_to_db():
            return

        file = open('partList.csv', 'r')
        partlist = csv.DictReader(file)

        ids = []
        mouserIds = []
        for row in partlist:
            ids.append(row["id"])
            mouserIds.append(row['mouserId'])


        self.__execute_sql_query_with_retry_db('DROP TABLE IF EXISTS parts')
        retval = self.__execute_sql_query_with_retry_db('CREATE TABLE parts ('
                                               'id INT PRIMARY KEY, '
                                               'mouserId VARCHAR(40))')

        for i in range(len(ids)):
            self.__execute_sql_query_with_retry_db('INSERT INTO parts (id, mouserId) VALUES (%s, %s);',
                                                   [ids[i], mouserIds[i]])
        # write the pickle flag after initialising the db
        if retval[0]:
            with open('./Flag.pkl', 'wb') as f:
                f.write(b'\x01')

        self.close_after_every_use_db()

    def insert_db(self, mouser_id):
        suc, num, ids = self.__execute_sql_query_with_retry_db(
            'SELECT id FROM parts ORDER BY id ASC')

        ids_list = [entry["id"] for entry in ids]
        min_id = 1
        max_id = max(ids_list)
        new_id = next((min_id + i for i, id_val in enumerate(ids_list) if id_val != min_id + i), max_id + 1)

        self.__execute_sql_query_with_retry_db(
            'INSERT INTO parts (id, mouserId) VALUES (%s, %s);',
            [new_id, mouser_id])
        self.close_after_every_use_db()
        return new_id

    def remove_db(self, mouser_id):
        exists = self.search_by_id_db(mouser_id, True)
        if not exists:
            return False

        ret = self.__execute_sql_query_with_retry_db('DELETE FROM parts WHERE id=(%s);',
                                            [mouser_id])
        self.close_after_every_use_db()
        return ret[0]

    def search_by_id_db(self, search_id, quick, let_conn_open=False):
        suc, num, ret = self.__execute_sql_query_with_retry_db(
            'SELECT mouserId FROM parts WHERE id=(%s);',
            [search_id])
        print("my printf {0} \n".format(ret), file=sys.stderr)

        mouser_id = ""
        dic = {}
        for row in ret:
            mouser_id = row['mouserId']

        if not quick and len(mouser_id) > 1:
            dic = ApiSearch(mouser_id)

        if not let_conn_open:
            self.close_after_every_use_db()

        return dic, mouser_id

    def search_by_mouser_id_db(self, mouser_id, let_conn_open=False):
        suc, num, ret = self.__execute_sql_query_with_retry_db(
            'SELECT id FROM parts WHERE mouserId=(%s);',
            [mouser_id])

        my_id = -1
        for row in ret:
            my_id = row['id']

        if not let_conn_open:
            self.close_after_every_use_db()

        return my_id

    def select_all_db(self, let_conn_open=False):
        suc, num, ret = self.__execute_sql_query_with_retry_db(
            'SELECT * FROM parts ORDER BY id ASC;')
        if not let_conn_open:
            self.close_after_every_use_db()
        return ret

# ------------------------------------------------------------------------------
# Server Functions GET
# ------------------------------------------------------------------------------
@server.route('/<search_id>')
def full_search_app(search_id):
    global db
    if not db:
        db = DBManager()

    try:
        int(search_id)
    except ValueError:
        return "No Valid ID"

    search_id = int(search_id)
    if search_id < 0 or search_id > 255:
        return "No Valid ID"

    request, mouser_id = db.search_by_id_db(search_id, False)
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

    dic_key_beatify = ["Id", "Mouser Id", "Description", "Manufact.", "Manufact. Nr.", "Link", "Datasheet"]

    return render_template('search_result.html', value_id = search_id,
                                                 values = dic.values(),
                                                 headrow = dic_key_beatify,
                                                 links = dic_links.values())
@server.route('/all', methods = ['GET'])
def print_all_app():
    global db
    if not db:
        db = DBManager()

    rows = db.select_all_db()
    dic = {}
    for row in rows:
        dic[row["id"]] = row["mouserId"]
    dic_key_beatify = ["Id", "Mouser Id"]

    return render_template('print_all.html', rows = dic, headrow = dic_key_beatify)

# ------------------------------------------------------------------------------
# Server Functions POST
# ------------------------------------------------------------------------------
@server.route('/all', methods=['POST'])
def remove_part():
    global db
    if not db:
        db = DBManager()

    rem_id = request.json['rem_id']
    if not rem_id:
        return jsonify(dict({'status' : 'fail'}))
    elif db.remove_db(rem_id):
        return jsonify(dict({'status': 'success'}))
    else:
        return jsonify(dict({'status' : 'fail'}))

@server.route('/add', methods=['POST'])
def add_item_app():
    global db
    if not db:
        db = DBManager()

    # check for  already existing
    mouser_id = request.json['add_id']

    if not mouser_id:
        return jsonify (dict({'status' : 'fail'}))

    exists =  db.search_by_mouser_id_db(mouser_id, True)
    if exists > -1:
        db.close_after_every_use_db()
        return jsonify (dict({'status' : 'exists', 'id' : exists}))

    # check for valid mouser id
    dic = ApiSearch(mouser_id)

    if dic['SearchResults']['NumberOfResult'] > 1 or dic['SearchResults']['NumberOfResult'] < 0:
        return jsonify (dict({'status' : 'fail'}))
    # insert
    new_id = db.insert_db(mouser_id)

    if new_id > -1:
        return jsonify (dict({'status' : 'success', 'id' : new_id}))
    else:
        return jsonify(dict({'status': 'fail'}))

@server.route('/search', methods = ['POST'])
def quick_search_app():
    global db
    if not db:
        db = DBManager()

    search_id = request.json['search_id']
    response, mouser_id = db.search_by_id_db(search_id, True, False)

    if not mouser_id:
        return jsonify (dict({'status' : 'fail'}))
    return jsonify (dict({'status' : 'success', 'id' : search_id }))

# ------------------------------------------------------------------------------
# CSV Document Operations
# ------------------------------------------------------------------------------
@server.route('/save', methods = ['GET'])
def save_db_to_csv_app():
    global db
    if not db:
        db = DBManager()

    rows = db.select_all_db(let_conn_open=True)

    try:
        file = open('partList.csv', 'w')
        write = csv.writer(file)
    except Exception as e:
        text = str(e)
        return jsonify(dict({'status': 'fail', 'message': text}))

    write.writerow([str('id'), str('mouserId')])
    for row in rows:
        write.writerow([row["id"], row["mouserId"]])
    file.close()

    # reload new csv File
    db.populate_db()
    return jsonify(dict({'status': 'success'}))

@server.route('/undo', methods = ['GET'])
def undo_db_reload_csv():
    global db
    if not db:
        db = DBManager()

    db.populate_db()
    return home_app()

# ------------------------------------------------------------------------------
# Main Pages
# ------------------------------------------------------------------------------
@server.route('/')
def home_app():
    global db
    if not db:
        db = DBManager()
    return render_template("home.html")

@server.errorhandler(404)git 
def page_not_found_app(e):
    return render_template("404.html")

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    server.run()
