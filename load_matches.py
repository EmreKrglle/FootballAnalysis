import json
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="football_analysis",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

with open("open-data/data/matches/55/282.json") as f:
    matches = json.load(f)

for m in matches:
    cursor.execute("""
        INSERT INTO matches (match_id, match_date, home_team, away_team, home_score, away_score, competition, season)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (match_id) DO NOTHING
    """, (
        m["match_id"],
        m["match_date"],
        m["home_team"]["home_team_name"],
        m["away_team"]["away_team_name"],
        m["home_score"],
        m["away_score"],
        m["competition"]["competition_name"],
        m["season"]["season_name"]
    ))

conn.commit()
cursor.close()
conn.close()
print(f"{len(matches)} maç yüklendi.")