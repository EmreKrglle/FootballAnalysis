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

def load_freeze_frames_for_match(match_id):
    filepath = f"open-data/data/three-sixty/{match_id}.json"

    if not os.path.exists(filepath):
        print(f"Dosya bulunamadı: {filepath}")
        return 0

    with open(filepath) as f:
        frames = json.load(f)

    count = 0
    for frame in frames:
        event_id = frame["event_uuid"]

        for player in frame["freeze_frame"]:
            location = player["location"]
            cursor.execute("""
                INSERT INTO freeze_frames (event_id, x, y, teammate, actor, keeper)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                location[0],
                location[1],
                player["teammate"],
                player["actor"],
                player["keeper"]
            ))
            count += 1

    conn.commit()
    return count

# Tüm maçları yükle
with open("open-data/data/matches/55/282.json") as f:
    matches = json.load(f)

total = 0
for m in matches:
    match_id = m["match_id"]
    count = load_freeze_frames_for_match(match_id)
    print(f"Maç {match_id}: {count} freeze frame yüklendi.")
    total += count

print(f"\nToplam: {total} freeze frame yüklendi.")
cursor.close()
conn.close()