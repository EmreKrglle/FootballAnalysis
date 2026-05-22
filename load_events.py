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

def load_events_for_match(match_id):
    filepath = f"open-data/data/events/{match_id}.json"
    
    if not os.path.exists(filepath):
        print(f"Dosya bulunamadı: {filepath}")
        return 0

    with open(filepath) as f:
        events = json.load(f)

    count = 0
    for e in events:
        # Koordinatlar her event'te olmayabilir
        location = e.get("location")
        x = location[0] if location else None
        y = location[1] if location else None

        # Bitiş koordinatı — pass ve carry'de var
        end_location = None
        if "pass" in e:
            end_location = e["pass"].get("end_location")
        elif "carry" in e:
            end_location = e["carry"].get("end_location")

        end_x = end_location[0] if end_location else None
        end_y = end_location[1] if end_location else None

        player = e.get("player", {})

        cursor.execute("""
            INSERT INTO events (id, match_id, index, period, minute, second, type, team, player_id, player_name, x, y, end_x, end_y)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            e["id"],
            match_id,
            e["index"],
            e["period"],
            e["minute"],
            e["second"],
            e["type"]["name"],
            e["team"]["name"],
            player.get("id"),
            player.get("name"),
            x, y, end_x, end_y
        ))
        count += 1

    conn.commit()
    return count

# Önce tek maçla test et — İspanya vs İngiltere finali
count = load_events_for_match(3943043)
print(f"{count} event yüklendi.")

cursor.close()
conn.close()