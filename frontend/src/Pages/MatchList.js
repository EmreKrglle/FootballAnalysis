import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./MatchList.css";

function MatchList() {
  const [matches, setMatches] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("http://127.0.0.1:8000/matches")
      .then(res => res.json())
      .then(data => setMatches(data));
  }, []);

  return (
    <div className="match-list">
      <h1>EURO <span>2024</span></h1>
      <p className="subtitle">{matches.length} maç · UEFA European Championship</p>

      {matches.map(match => (
        <div
          key={match.match_id}
          className="match-card"
          onClick={() => navigate(`/match/${match.match_id}`)}
        >
          <div className="match-teams">
            <span>{match.home_team}</span>
            <div className="match-score">
              {match.home_score} - {match.away_score}
            </div>
            <span>{match.away_team}</span>
          </div>
          <div className="match-date">{match.match_date}</div>
        </div>
      ))}
    </div>
  );
}

export default MatchList;