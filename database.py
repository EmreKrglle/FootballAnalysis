import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="football_analysis",
        user="postgres",
        password=os.getenv("DB_PASSWORD")
    )
    return conn

if __name__ == "__main__":
    conn = get_connection()
    print("Veritabanına bağlandı!")
    conn.close()