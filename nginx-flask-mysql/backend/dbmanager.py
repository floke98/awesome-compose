import mysql.connector
import csv
import sys
import os
from mouser_api import ApiSearch
import logging

debug = False


if debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# ------------------------------------------------------------------------------
# Database Class
# ------------------------------------------------------------------------------
def check_first_run():
    logging.debug('This will get logged')
    if os.path.isfile('/pickle/Flag.pkl'):
        with open('/pickle/Flag.pkl', 'rb') as f:
            return f.read()
    else:
        logging.debug('File not exists but 0 returned')
        return b'\x00'
class DBManager:
    # --------------------------------------------------------------------------
    # Private
    # --------------------------------------------------------------------------
    def __init__(self):
        self.connection = None
        self.cursor = None

        if check_first_run() == b'\x00':
            self.populate_db()

            #write csv backup file
            rows = self.select_all_db(let_conn_open=True)

            try:
                file = open('/dbBackup/partList.csv', 'w')
                write = csv.writer(file)
                write.writerow([str('id'), str('mouserId')])
                for row in rows:
                    write.writerow([row["id"], row["mouserId"]])
                file.close()

            except Exception as e:
                text = str(e)
                logging.error("Could save backup file in init!" + text)

        return

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
                    logging.debug("\n OPENED a CONNECTION \n")
                    return 1

            except Exception as error:
                logging.debug("ERROR. Connection to DB in attempt {0}, not established\n{1}".format(attempts, error))

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
                logging.debug("During Query: {0}\n{1}\n".format(num_affected_rows, return_val))
        except mysql.connector.Error as e:
            logging.debug("ERROR. Could not execute query!!\n{}{}".format(e.errno, e.msg))

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
            logging.debug("ERROR. Cant close cursor!\n{}".format(error))

        try:
            self.connection.close()
            logging.debug("\n CLOSED THE CONNECTION \n")
        except Exception as error:
            logging.debug("ERROR. Cant close connection!\n{}".format(error))

    def populate_db(self):
        if not self.__connect_to_db():
            return

        if check_first_run() ==  b'\x00':
            file = open('partList.csv', 'r')
        else:
            file = open('/dbBackup/partList.csv', 'r')

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
            with open('/pickle/Flag.pkl', 'wb') as f:
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
        logging.debug("my logging.debugf {0} \n".format(ret))

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