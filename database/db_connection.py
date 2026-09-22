import sqlite3
from pathlib import Path
import traceback

class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connection = None
        return cls._instance
    
    def connect(self):
        try:
            from config import Config
            self.connection = sqlite3.connect(Config.DB_PATH)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.row_factory = sqlite3.Row
            return self.connection
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return None
    
    def get_connection(self):
        if self.connection is None:
            return self.connect()
        return self.connection
    
    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except sqlite3.Error as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def fetch_all(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            return [dict(row) for row in result]
        except sqlite3.Error as e:
            print(f"Ошибка запроса: {e}")
            return []
        finally:
            cursor.close()
    
    def fetch_one(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            return dict(result) if result else None
        except sqlite3.Error as e:
            print(f"Ошибка запроса: {e}")
            return None
        finally:
            cursor.close()