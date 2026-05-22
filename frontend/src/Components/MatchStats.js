import "./MatchStats.css";

function StatRow({ label, homeValue, awayValue }) {
  const total = homeValue + awayValue;
  const homePercent = total > 0 ? (homeValue / total) * 100 : 50;
  const awayPercent = total > 0 ? (awayValue / total) * 100 : 50;
  const homeHigher = homeValue > awayValue;
  const awayHigher = awayValue > homeValue;

  return (
    <div className="stat-row">
      {/* Home değer + bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className={`stat-value home ${homeHigher ? "higher" : ""}`}>
          {homeValue}
        </span>
        <div className="stat-bar" style={{ flex: 1 }}>
          <div
            className="stat-bar-fill home"
            style={{ width: `${homePercent}%`, marginLeft: "auto" }}
          />
        </div>
      </div>

      {/* Etiket */}
      <div className="stat-label">{label}</div>

      {/* Away bar + değer */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div className="stat-bar" style={{ flex: 1 }}>
          <div
            className="stat-bar-fill away"
            style={{ width: `${awayPercent}%` }}
          />
        </div>
        <span className={`stat-value away ${awayHigher ? "higher" : ""}`}>
          {awayValue}
        </span>
      </div>
    </div>
  );
}

function MatchStats({ stats }) {
  if (!stats) return null;

  const { match, team_stats } = stats;
  const home = team_stats.find(t => t.team === match.home_team) || {};
  const away = team_stats.find(t => t.team === match.away_team) || {};

  const rows = [
    { label: "Şut",           home: home.shots,           away: away.shots },
    { label: "Pas",           home: home.passes,          away: away.passes },
    { label: "Carry",         home: home.carries,         away: away.carries },
    { label: "Baskı",         home: home.pressures,       away: away.pressures },
    { label: "Dribling",      home: home.dribbles,        away: away.dribbles },
    { label: "Top Kazanma",   home: home.ball_recoveries, away: away.ball_recoveries },
    { label: "Faul",          home: home.fouls,           away: away.fouls },
    { label: "Müdahale",      home: home.interceptions,   away: away.interceptions },
  ];

  return (
    <div className="stats-container">

      {/* Skor */}
      <div className="stats-scoreboard">
        <div className="stats-teams">
          <div className="stats-team-name home">{match.home_team}</div>
          <div className="stats-score">
            {match.home_score} - {match.away_score}
          </div>
          <div className="stats-team-name away">{match.away_team}</div>
        </div>
        <div className="stats-competition">UEFA Euro 2024</div>
      </div>

      {/* İstatistik tablosu */}
      <div className="stats-grid">
        <div className="stats-grid-header">
          <span className="home">{match.home_team}</span>
          <span className="label">İstatistik</span>
          <span className="away" style={{ textAlign: "right" }}>{match.away_team}</span>
        </div>
        {rows.map(row => (
          <StatRow
            key={row.label}
            label={row.label}
            homeValue={row.home || 0}
            awayValue={row.away || 0}
          />
        ))}
      </div>

    </div>
  );
}

export default MatchStats;