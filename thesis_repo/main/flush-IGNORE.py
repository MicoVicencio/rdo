import sqlite3
import os

DB_FILE = "thesis_repository.db"

def clear_database():
    if not os.path.exists(DB_FILE):
        print("❌ Database file not found:", DB_FILE)
        return
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        # Get all table names
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()

        for table in tables:
            table_name = table[0]
            if table_name != "sqlite_sequence":  # keep autoincrement metadata safe
                cur.execute(f"DELETE FROM {table_name};")  # remove all rows
                print(f"✅ Cleared table: {table_name}")

        conn.commit()
        conn.close()
        print("🎉 Database cleared successfully!")

    except Exception as e:
        print("❌ Error clearing database:", e)

if __name__ == "__main__":
    clear_database()
