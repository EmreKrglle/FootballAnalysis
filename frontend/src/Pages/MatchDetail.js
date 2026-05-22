import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Pitch from "../Components/Pitch";
import MatchStats from "../Components/MatchStats";
import LineupView from "../Components/LineupView";
import SequencePlayer from "../Components/SequencePlayer";
import { getEvents, getFreezeFrames, getMatchStats } from "../Services/api";
import "./MatchDetail.css";

function MatchDetail() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [events,    setEvents]    = useState([]);
  const [freezeFrames, setFreezeFrames] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [matchInfo, setMatchInfo] = useState(null);
  const [stats,     setStats]     = useState(null);
  const [sequences, setSequences] = useState([]);
  const [activeTab, setActiveTab] = useState("lineup");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/matches")
      .then(res => res.json())
      .then(data => {
        const match = data.find(m => m.match_id === parseInt(matchId));
        setMatchInfo(match);
      });
    getEvents(matchId).then(setEvents);
    getMatchStats(matchId).then(setStats);
  }, [matchId]);

  // Sekansları matchInfo gelince çek
  useEffect(() => {
    if (!matchInfo) return;
    fetch(`http://127.0.0.1:8000/matches/${matchId}/sequences/${encodeURIComponent(matchInfo.home_team)}`)
      .then(res => res.json())
      .then(data => setSequences(data.sequences ?? []));
  }, [matchId, matchInfo]);

  function handleEventClick(event) {
    setSelectedEvent(event);
    getFreezeFrames(event.id).then(setFreezeFrames);
  }

  const tabs = [
    { k: "lineup",    l: "👥 Kadro" },
    { k: "sequences", l: "🎬 Sekanslar" },
    { k: "events",    l: "⚽ Events" },
    { k: "stats",     l: "📊 İstatistik" },
  ];

  return (
    <div className="match-detail">

      {/* ── Header ── */}
      <div className="match-detail-header">
        <button className="back-button" onClick={() => navigate("/")}>
          ← Geri
        </button>
        {matchInfo && (
          <div className="match-title">
            {matchInfo.home_team}
            <span> {matchInfo.home_score} - {matchInfo.away_score} </span>
            {matchInfo.away_team}
          </div>
        )}
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
          {tabs.map(({ k, l }) => (
            <button key={k} onClick={() => setActiveTab(k)} style={{
              background: activeTab === k ? "#4ade80" : "#1a1d27",
              border: `1px solid ${activeTab === k ? "#4ade80" : "#2a2d3e"}`,
              color: activeTab === k ? "#0f1117" : "#64748b",
              padding: "8px 18px", borderRadius: "8px", cursor: "pointer",
              fontSize: "13px", fontWeight: activeTab === k ? 700 : 400,
              transition: "all 0.2s ease",
            }}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* ── Kadro ── */}
      {activeTab === "lineup" && (
        <LineupView matchId={matchId} matchInfo={matchInfo} />
      )}

      {/* ── Sekanslar ── */}
      {activeTab === "sequences" && (
        <div style={{ padding: "0 0 32px" }}>
          {sequences.length === 0 ? (
            <div style={{ padding: 48, textAlign: "center", color: "#64748b" }}>
              Sekans yükleniyor...
            </div>
          ) : (
            <SequencePlayer sequences={sequences} />
          )}
        </div>
      )}

      {/* ── İstatistik ── */}
      {activeTab === "stats" && (
        <MatchStats stats={stats} />
      )}

      {/* ── Events ── */}
      {activeTab === "events" && (
        <div className="match-detail-body">
          <div className="event-list">
            <div className="event-list-header">
              Events · {events.length} toplam
            </div>
            <div className="event-list-scroll">
              {events.slice(0, 100).map(event => (
                <div
                  key={event.id}
                  className={`event-item ${selectedEvent?.id === event.id ? "selected" : ""}`}
                  onClick={() => handleEventClick(event)}
                >
                  <div className="event-type-badge">{event.type}</div>
                  <div className="event-info">
                    <div className="event-player">{event.player_name || "—"}</div>
                    <div className="event-time">
                      {event.minute}:{String(event.second).padStart(2, "0")}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pitch-panel">
            <div className="pitch-panel-header">
              <div className="pitch-panel-title">
                {selectedEvent
                  ? `${selectedEvent.type} — ${selectedEvent.player_name || "—"}`
                  : "Freeze Frame"}
              </div>
              <div className="pitch-panel-subtitle">
                {selectedEvent
                  ? `${selectedEvent.minute}:${String(selectedEvent.second).padStart(2, "0")}`
                  : "Event seç"}
              </div>
            </div>
            <div className="pitch-container">
              {selectedEvent ? (
                <Pitch freezeFrames={freezeFrames} />
              ) : (
                <div className="pitch-empty">
                  <span>⚽</span>
                  Soldaki listeden bir event seç
                </div>
              )}
            </div>
            <div className="pitch-legend">
              <div className="legend-item">
                <div className="legend-dot" style={{ background: "#3b82f6" }} />
                Takım arkadaşı
              </div>
              <div className="legend-item">
                <div className="legend-dot" style={{ background: "#ef4444" }} />
                Rakip
              </div>
              <div className="legend-item">
                <div className="legend-dot" style={{ background: "#facc15" }} />
                Topu oynayan
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default MatchDetail;