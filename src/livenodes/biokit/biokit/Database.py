import datetime
import sqlite3
import time

from legacy import JanusCompatibility


class Database:

    def __init__(self, filename, queryretries=10, retryinterval=0.5):
        print("******************* DB INIT ***************************")
        self.db = sqlite3.connect(filename)
        self.db.row_factory = sqlite3.Row
        self.db.text_factory = str
        self.db_cursor = self.db.cursor()
        self.queryretries = queryretries
        self.retryinterval = retryinterval

    def log(self, level, text):
        print("Python log: " + str(datetime.datetime.now()) + " - " + level +
              ": " + text)

    def logsql(self, query):
        self.log("Info", "Executing SQL Statement: " + query)

    def logres(self, result):
        self.log("Info", "SQL query result:")
        self.log("Info", str(len(result)))
        for res in result:
            self.log("Info", "Res: " + str(res))

    def close(self):
        self.db.close()

    def executeStatement(self, statement, log=True):
        if (log == True):
            self.logsql(statement)
        for trycount in range(self.queryretries):
            try:
                self.db_cursor.execute(statement)
                res = self.db_cursor.fetchall()
                break
            except RuntimeError as e:
                if (e.message == "sqlite3: database is locked"
                        and trycount < self.queryretries):
                    self.log("Info",
                             "<Database> Error: " + str(e) + " retry...")
                    time.sleep(self.retryinterval)
                    trycount += 1
                else:
                    self.log("Error", "<Database> Error: " + str(e))
                    raise e
        return res

    def selectRows(self, table, key, value):
        sqlcmd = "SELECT * FROM " + table + " WHERE " + key + " = " + str(
            value)
        self.db_cursor.execute(sqlcmd)
        result = self.db_cursor.fetchall()
        return [x for x in result]

    def getUniqueValue(self, table, retrieveKey, key, value):
        sqlcmd = "SELECT " + retrieveKey + " FROM " + table + " WHERE "\
            + key + " = " + str(value)
        self.logsql(sqlcmd)
        self.db_cursor.execute(sqlcmd)
        result = self.db_cursor.fetchall()
        if (result.size() == 1):
            for r in result:
                print(r)
            return next(result.__iter__())[retrieveKey]
        else:
            raise LookupError

    def exportTableToJanusArrays(self, table, filename):
        sqlcmd = "SELECT * FROM " + table
        result = self.executeStatement(sqlcmd)

        entries = [JanusCompatibility.convertDictToJanus(x) for x in result]
        JanusCompatibility.writeJanusArraysToFile(entries, filename)

    def doesTableExist(self, tableName):
        sqlcmd = "SELECT count(*) FROM sqlite_master where type='table' \
            and name=\'" + tableName + "\'"
        result = self.executeStatement(sqlcmd)
        if (result.size() == 1):
            if [x for x in result][0]['count(*)'] == 1:
                return True
            else:
                return False
        else:
            raise LookupError

    def getNumberOfRecords(self, table):
        sqlcmd = "SELECT count(*) FROM " + table
        result = self.executeStatement(sqlcmd)
        if (result.size() == 1):
            return [x for x in result][0]['count(*)']
        else:
            raise LookupError
