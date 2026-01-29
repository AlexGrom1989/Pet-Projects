import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    def __init__(self, host='localhost', db='parking_db', user='postgres', pwd='postgres'):
        self.conn = psycopg2.connect(host=host, database=db, user=user, password=pwd)
        self.conn.autocommit = False
        self.init_db()
    
    def init_db(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY, plate VARCHAR(20) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL, phone VARCHAR(20) NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, truth_number_plate VARCHAR(50))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS entry_logs (
            id SERIAL PRIMARY KEY, plate VARCHAR(20), confirm_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            photo_path VARCHAR(500), confirm_type VARCHAR(20))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS exit_logs (
            id SERIAL PRIMARY KEY, plate VARCHAR(20), confirm_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            photo_path VARCHAR(500), confirm_type VARCHAR(20))''')
        
        self.conn.commit()
    
    def add_tenant(self, plate: str, name: str, phone: str) -> bool:
        try:
            c = self.conn.cursor()
            c.execute("INSERT INTO tenants (plate, full_name, phone) VALUES (%s, %s, %s)",
                     (plate.upper(), name, phone))
            self.conn.commit()
            return True
        except:
            self.conn.rollback()
            return False
    
    def get_tenant(self, plate: str):
        try:
            c = self.conn.cursor(cursor_factory=RealDictCursor)
            c.execute("SELECT * FROM tenants WHERE plate = %s", (plate.upper(),))
            return c.fetchone()
        except:
            return None
    
    def get_all_tenants(self):
        try:
            c = self.conn.cursor(cursor_factory=RealDictCursor)
            c.execute("SELECT * FROM tenants ORDER BY added_date DESC")
            return c.fetchall() or []
        except:
            return []
    
    def add_entry(self, plate: str, photo: str, conf_type: str) -> bool:
        try:
            c = self.conn.cursor()
            c.execute("INSERT INTO entry_logs (plate, photo_path, confirm_type) VALUES (%s, %s, %s)",
                     (plate.upper(), photo, conf_type))
            self.conn.commit()
            return True
        except:
            self.conn.rollback()
            return False
    
    def add_exit(self, plate: str, photo: str, conf_type: str) -> bool:
        try:
            c = self.conn.cursor()
            c.execute("INSERT INTO exit_logs (plate, photo_path, confirm_type) VALUES (%s, %s, %s)",
                     (plate.upper(), photo, conf_type))
            self.conn.commit()
            return True
        except:
            self.conn.rollback()
            return False
    
    def get_entry_logs(self, limit=20):
        try:
            c = self.conn.cursor(cursor_factory=RealDictCursor)
            c.execute("SELECT * FROM entry_logs ORDER BY confirm_time DESC LIMIT %s", (limit,))
            return c.fetchall() or []
        except:
            return []
    
    def get_exit_logs(self, limit=20):
        try:
            c = self.conn.cursor(cursor_factory=RealDictCursor)
            c.execute("SELECT * FROM exit_logs ORDER BY confirm_time DESC LIMIT %s", (limit,))
            return c.fetchall() or []
        except:
            return []
    
    def close(self):
        if self.conn:
            self.conn.close()