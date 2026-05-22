import { useState, useEffect } from "react";
import { getLineup, getPlayerStats } from "../Services/api";
import "./LineupView.css";

function LineupView({ matchId, matchInfo }) {
  const [players, setPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [playerStats, setPlayerStats] = useState(null);

  useEffect(() => {
    getLineup(matchId).then(setPlayers);
  }, [matchId]);

  function handlePlayerClick(player) {
    setSelectedPlayer(player);
    setPlayerStats(null);
    getPlayerStats(matchId, player.player_id).then(setPlayerStats);
  }

  function closePopup() {
    setSelectedPlayer(null);
    setPlayerStats(null);
  }

  if (!matchInfo) return null;

  const homePlayers = players.filter(p => p.team === matchInfo.home_team).slice(0, 15);
  const awayPlayers = players.filter(p => p.team === matchInfo.away_team).slice(0, 15);

  const getInitials = (name) => {
    if (!name) return "?";
    const parts = name.split(" ");
    return parts.length >= 2
      ? parts[0][0] + parts[parts.length - 1][0]
      : name[0];
  };

  const TeamList = ({ teamPlayers, teamName, color }) => (
    <div className="lineup-team">
      <div className="lineup-team-header">
        <div className="dot" style={{ background: color }} />
        {teamName}
      </div>
      {teamPlayers.map(player => (
        <div
          key={player.player_id}
          className="player-row"
          onClick={() => handlePlayerClick(player)}
        >
          <div className="player-avatar"
            style={{ background: `${color}22`, color: color }}>
            {getInitials(player.player_name)}
          </div>
          <div className="player-name">{player.player_name}</div>
          <div className="player-events">{player.event_count} aksiyon</div>
        </div>
      ))}
    </div>
  );

  return (
    <>
      <div className="lineup-container">
        <TeamList
          teamPlayers={homePlayers}
          teamName={matchInfo.home_team}
          color="#3b82f6"
        />
        <TeamList
          teamPlayers={awayPlayers}
          teamName={matchInfo.away_team}
          color="#ef4444"
        />
      </div>

      {/* Oyuncu İstatistik Popup */}
      {selectedPlayer && (
        <div className="player-popup-overlay" onClick={closePopup}>
          <div className="player-popup" onClick={e => e.stopPropagation()}>

            <div className="player-popup-header">
              <div>
                <div className="player-popup-name">
                  {selectedPlayer.player_name}
                </div>
                <div className="player-popup-team">
                  {selectedPlayer.team}
                </div>
              </div>
              <button className="close-button" onClick={closePopup}>✕</button>
            </div>

            <div className="player-popup-stats">
              {!playerStats ? (
                <div style={{ color: "#64748b", textAlign: "center", padding: 32 }}>
                  Yükleniyor...
                </div>
              ) : (
                [
                  { label: "Pas",          value: playerStats.passes },
                  { label: "Şut",          value: playerStats.shots },
                  { label: "Carry",        value: playerStats.carries },
                  { label: "Baskı",        value: playerStats.pressures },
                  { label: "Dribling",     value: playerStats.dribbles },
                  { label: "Top Kazanma", value: playerStats.ball_recoveries },
                  { label: "Müdahale",    value: playerStats.interceptions },
                  { label: "Faul",         value: playerStats.fouls },
                ].map(stat => (
                  <div key={stat.label} className="popup-stat-row">
                    <span className="popup-stat-label">{stat.label}</span>
                    <span className="popup-stat-value">{stat.value || 0}</span>
                  </div>
                ))
              )}
            </div>

          </div>
        </div>
      )}
    </>
  );
}

export default LineupView;