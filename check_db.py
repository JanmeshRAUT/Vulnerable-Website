
import sqlite3

def check_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    print("Users in DB:", users)
    conn.close()

if __name__ == "__main__":
    check_users()
