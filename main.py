from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_connection():
    return psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="football_analysis",
        user="postgres",
        password=os.getenv("DB_PASSWORD")
    )

@app.get("/matches")
def get_matches():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT match_id, match_date, home_team, away_team, home_score, away_score
        FROM matches
        ORDER BY match_date DESC
    """)
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    return matches
@app.get("/matches/{match_id}/events")
def get_events(match_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT id, index, period, minute, second, type, team, player_name, x, y, end_x, end_y
        FROM events
        WHERE match_id = %s
        ORDER BY index
    """, (match_id,))
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return events
@app.get("/events/{event_id}/freeze-frames")
def get_freeze_frames(event_id: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT x, y, teammate, actor, keeper
        FROM freeze_frames
        WHERE event_id = %s
    """, (event_id,))
    frames = cursor.fetchall()
    cursor.close()
    conn.close()
    return frames
@app.get("/matches/{match_id}/stats")
def get_match_stats(match_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Takım isimlerini al
    cursor.execute("""
        SELECT home_team, away_team, home_score, away_score
        FROM matches WHERE match_id = %s
    """, (match_id,))
    match = cursor.fetchone()

    # Her takım için istatistikler
    cursor.execute("""
        SELECT
            team,
            COUNT(*) FILTER (WHERE type = 'Pass') as passes,
            COUNT(*) FILTER (WHERE type = 'Shot') as shots,
            COUNT(*) FILTER (WHERE type = 'Carry') as carries,
            COUNT(*) FILTER (WHERE type = 'Pressure') as pressures,
            COUNT(*) FILTER (WHERE type = 'Dribble') as dribbles,
            COUNT(*) FILTER (WHERE type = 'Tackle') as tackles,
            COUNT(*) FILTER (WHERE type = 'Interception') as interceptions,
            COUNT(*) FILTER (WHERE type = 'Ball Recovery') as ball_recoveries,
            COUNT(*) FILTER (WHERE type = 'Foul Committed') as fouls
        FROM events
        WHERE match_id = %s
        GROUP BY team
    """, (match_id,))
    team_stats = cursor.fetchall()

    # Gol sayısı
    cursor.execute("""
        SELECT team, COUNT(*) as goals
        FROM events
        WHERE match_id = %s AND type = 'Shot'
        AND player_name IS NOT NULL
        GROUP BY team
    """, (match_id,))

    cursor.close()
    conn.close()

    return {
        "match": match,
        "team_stats": team_stats
    }
@app.get("/matches/{match_id}/lineup")
def get_lineup(match_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Starting XI eventlerinden kadroyu al
    cursor.execute("""
        SELECT team, player_id, player_name, COUNT(*) as event_count
        FROM events
        WHERE match_id = %s
        AND type != 'Starting XI'
        AND type != 'Half Start'
        AND type != 'Tactical Shift'
        AND player_name IS NOT NULL
        GROUP BY team, player_id, player_name
        ORDER BY team, event_count DESC
    """, (match_id,))
    players = cursor.fetchall()

    cursor.close()
    conn.close()
    return players

@app.get("/matches/{match_id}/player/{player_id}/stats")
def get_player_stats(match_id: int, player_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT
            player_name,
            team,
            COUNT(*) FILTER (WHERE type = 'Pass') as passes,
            COUNT(*) FILTER (WHERE type = 'Shot') as shots,
            COUNT(*) FILTER (WHERE type = 'Carry') as carries,
            COUNT(*) FILTER (WHERE type = 'Pressure') as pressures,
            COUNT(*) FILTER (WHERE type = 'Dribble') as dribbles,
            COUNT(*) FILTER (WHERE type = 'Ball Recovery') as ball_recoveries,
            COUNT(*) FILTER (WHERE type = 'Foul Committed') as fouls,
            COUNT(*) FILTER (WHERE type = 'Interception') as interceptions,
            COUNT(*) FILTER (WHERE type = 'Tackle') as tackles
        FROM events
        WHERE match_id = %s AND player_id = %s
        GROUP BY player_name, team
    """, (match_id, player_id))

    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    return stats
@app.get("/matches/{match_id}/sequences/{team}")
def get_sequences(match_id: int, team: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id, index, period, minute, second, type, team, player_name, x, y, end_x, end_y
        FROM events
        WHERE match_id = %s
        ORDER BY index
    """, (match_id,))
    events = cursor.fetchall()
    cursor.close()
    conn.close()

    # Sekansları bul — top o takımdan ayrılana kadar devam et
    sequences = []
    current_seq = []
    ignored_types = {
        "Starting XI", "Half Start", "Tactical Shift",
        "Player On", "Player Off", "Injury Stoppage",
        "Referee Ball-Drop", "50/50", "Error"
    }

    for ev in events:
        ev = dict(ev)
        if ev["type"] in ignored_types:
            continue

        if ev["team"] == team:
            current_seq.append(ev)
        else:
            # Top rakibe geçti — sekansı kaydet
            if len(current_seq) >= 3:
                # Son event rakibe geçişi açıklar
                last = current_seq[-1]
                outcome = (
                    "Şut" if last["type"] == "Shot" else
                    "Faul Kazanıldı" if last["type"] == "Foul Won" else
                    "Top Kaybı"
                )
                sequences.append({
                    "id": f"seq_{current_seq[0]['index']}",
                    "start_minute": current_seq[0]["minute"],
                    "start_second": current_seq[0]["second"],
                    "end_minute": last["minute"],
                    "end_second": last["second"],
                    "event_count": len(current_seq),
                    "outcome": outcome,
                    "events": current_seq
                })
            current_seq = []

    return {
        "team": team,
        "match_id": match_id,
        "sequence_count": len(sequences),
        "sequences": sequences
    }