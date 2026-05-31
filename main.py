# -*- coding: utf-8 -*-
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

# ---------------------------------------------------------
#  4 SINIFLI OUTCOME SINIFLANDIRICI
# ---------------------------------------------------------
# Sinif isimleri - Turkce karakter YOK (encoding sorunu onlenir)
#   "Tehlikeli Kayip"  → kendi yarisinda top kaybi   (0)
#   "Notr Kayip"       → rakip yarisinda top kaybi   (1)
#   "Ilerleme"         → faul / rakip yarisina gecis (2)
#   "Yuksek Tehlike"   → sut / ceza sahasina giris   (3)

def classify_outcome(last_event: dict) -> str:
    event_type = last_event.get("type", "")
    x          = last_event.get("x") or 0
    end_x      = last_event.get("end_x") or x

    # Yuksek Tehlike
    if event_type == "Shot":
        return "Yuksek Tehlike"
    if event_type == "Carry" and end_x > 102:
        return "Yuksek Tehlike"
    if event_type == "Dribble" and x > 102:
        return "Yuksek Tehlike"

    # Ilerleme
    if event_type == "Foul Won":
        return "Ilerleme"
    if x > 60 and event_type in ("Pass", "Carry", "Dribble", "Ball Receipt*"):
        return "Ilerleme"

    # Tehlikeli Kayip
    if x < 40:
        return "Tehlikeli Kayip"

    # Notr Kayip
    return "Notr Kayip"


# ---------------------------------------------------------
#  MEVCUT ENDPOINTLER
# ---------------------------------------------------------

@app.get("/matches")
def get_matches():
    conn   = get_connection()
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
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT id, index, period, minute, second, type, team,
               player_name, x, y, end_x, end_y
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
    conn   = get_connection()
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
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT home_team, away_team, home_score, away_score
        FROM matches WHERE match_id = %s
    """, (match_id,))
    match = cursor.fetchone()

    cursor.execute("""
        SELECT
            team,
            COUNT(*) FILTER (WHERE type = 'Pass')           as passes,
            COUNT(*) FILTER (WHERE type = 'Shot')           as shots,
            COUNT(*) FILTER (WHERE type = 'Carry')          as carries,
            COUNT(*) FILTER (WHERE type = 'Pressure')       as pressures,
            COUNT(*) FILTER (WHERE type = 'Dribble')        as dribbles,
            COUNT(*) FILTER (WHERE type = 'Tackle')         as tackles,
            COUNT(*) FILTER (WHERE type = 'Interception')   as interceptions,
            COUNT(*) FILTER (WHERE type = 'Ball Recovery')  as ball_recoveries,
            COUNT(*) FILTER (WHERE type = 'Foul Committed') as fouls
        FROM events
        WHERE match_id = %s
        GROUP BY team
    """, (match_id,))
    team_stats = cursor.fetchall()

    cursor.close()
    conn.close()
    return {"match": match, "team_stats": team_stats}


@app.get("/matches/{match_id}/lineup")
def get_lineup(match_id: int):
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT team, player_id, player_name, COUNT(*) as event_count
        FROM events
        WHERE match_id = %s
          AND type NOT IN ('Starting XI', 'Half Start', 'Tactical Shift')
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
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT
            player_name,
            team,
            COUNT(*) FILTER (WHERE type = 'Pass')           as passes,
            COUNT(*) FILTER (WHERE type = 'Shot')           as shots,
            COUNT(*) FILTER (WHERE type = 'Carry')          as carries,
            COUNT(*) FILTER (WHERE type = 'Pressure')       as pressures,
            COUNT(*) FILTER (WHERE type = 'Dribble')        as dribbles,
            COUNT(*) FILTER (WHERE type = 'Ball Recovery')  as ball_recoveries,
            COUNT(*) FILTER (WHERE type = 'Foul Committed') as fouls,
            COUNT(*) FILTER (WHERE type = 'Interception')   as interceptions,
            COUNT(*) FILTER (WHERE type = 'Tackle')         as tackles
        FROM events
        WHERE match_id = %s AND player_id = %s
        GROUP BY player_name, team
    """, (match_id, player_id))
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    return stats


# ---------------------------------------------------------
#  GUNCELLENMIS SEQUENCES ENDPOINT
# ---------------------------------------------------------

@app.get("/matches/{match_id}/sequences/{team}")
def get_sequences(match_id: int, team: str):
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT id, index, period, minute, second, type, team,
               player_name, x, y, end_x, end_y
        FROM events
        WHERE match_id = %s
        ORDER BY index
    """, (match_id,))
    events = cursor.fetchall()
    cursor.close()
    conn.close()

    sequences    = []
    current_seq  = []
    ignored_types = {
        "Starting XI", "Half Start", "Tactical Shift",
        "Player On", "Player Off", "Injury Stoppage",
        "Referee Ball-Drop", "50/50", "Error"
    }

    def save_sequence(seq):
        if len(seq) < 3:
            return
        last    = seq[-1]
        outcome = classify_outcome(last)
        sequences.append({
            "id":           "seq_{}".format(seq[0]["index"]),
            "start_minute": seq[0]["minute"],
            "start_second": seq[0]["second"],
            "end_minute":   last["minute"],
            "end_second":   last["second"],
            "event_count":  len(seq),
            "outcome":      outcome,
            "last_x":       last.get("x") or 0,
            "last_type":    last["type"],
            "events":       seq,
        })

    for ev in events:
        ev = dict(ev)
        if ev["type"] in ignored_types:
            continue
        if ev["team"] == team:
            current_seq.append(ev)
        else:
            save_sequence(current_seq)
            current_seq = []

    save_sequence(current_seq)

    outcome_counts = {
        "Yuksek Tehlike":  0,
        "Ilerleme":        0,
        "Notr Kayip":      0,
        "Tehlikeli Kayip": 0,
    }
    for s in sequences:
        key = s["outcome"]
        if key in outcome_counts:
            outcome_counts[key] += 1

    return {
        "team":           team,
        "match_id":       match_id,
        "sequence_count": len(sequences),
        "outcome_counts": outcome_counts,
        "sequences":      sequences,
    }


@app.get("/matches/{match_id}/sequence-summary")
def get_sequence_summary(match_id: int):
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT home_team, away_team, home_score, away_score
        FROM matches WHERE match_id = %s
    """, (match_id,))
    match = cursor.fetchone()
    cursor.close()
    conn.close()

    if not match:
        return {"error": "Mac bulunamadi"}

    summary = {}
    for team in [match["home_team"], match["away_team"]]:
        seq_data = get_sequences(match_id, team)
        counts   = seq_data["outcome_counts"]
        total    = seq_data["sequence_count"]
        summary[team] = {
            "total_sequences":     total,
            "outcome_counts":      counts,
            "threat_rate":         round(counts.get("Yuksek Tehlike",  0) / max(total, 1), 3),
            "progression_rate":    round(counts.get("Ilerleme",        0) / max(total, 1), 3),
            "safe_loss_rate":      round(counts.get("Notr Kayip",      0) / max(total, 1), 3),
            "dangerous_loss_rate": round(counts.get("Tehlikeli Kayip", 0) / max(total, 1), 3),
        }

    return {
        "match_id":   match_id,
        "home_team":  match["home_team"],
        "away_team":  match["away_team"],
        "home_score": match["home_score"],
        "away_score": match["away_score"],
        "summary":    summary,
    }