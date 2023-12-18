import os
from flask import Flask, render_template, json, request, jsonify
import csv
from mouser_api import ApiSearch
from dbmanager import DBManager, debug

server = Flask(__name__)
server.run(debug=debug)

# TODO api calls -> make delayed calls when print all

# helper:
# https://stackoverflow.com/questions/13568508/python-mysql-handling-timeouts
# https://stackoverflow.com/questions/5504340/python-mysqldb-connection-close-vs-cursor-close
# https://stackoverflow.com/questions/26743103/how-to-check-the-connection-alive-in-python

# ------------------------------------------------------------------------------
# Globals
# ------------------------------------------------------------------------------
db = None
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

    rows = db.select_all_db(let_conn_open=False)

    try:
        file = open('/dbBackup/partList.csv', 'w')
        write = csv.writer(file)
        write.writerow([str('id'), str('mouserId')])
        for row in rows:
            write.writerow([row["id"], row["mouserId"]])
        file.close()

    except Exception as e:
        text = str(e)
        return jsonify(dict({'status': 'fail', 'message': text}))

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

@server.errorhandler(404)
def page_not_found_app(e):
    return render_template("404.html")

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    server.run()
