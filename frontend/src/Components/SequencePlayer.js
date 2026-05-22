import { useState, useEffect, useRef } from "react";
import Pitch from "./Pitch";

const EVENT_COLORS = {
  "Pass":         { bg: "rgba(56,189,248,0.15)",  color: "#38bdf8", label: "Pas" },
  "Carry":        { bg: "rgba(74,222,128,0.15)",  color: "#4ade80", label: "Carry" },
  "Shot":         { bg: "rgba(249,115,22,0.15)",  color: "#f97316", label: "Şut" },
  "Ball Receipt*":{ bg: "rgba(255,255,255,0.05)", color: "#64748b", label: "Top Alındı" },
  "Dribble":      { bg: "rgba(167,139,250,0.15)", color: "#a78bfa", label: "Dribling" },
  "default":      { bg: "rgba(255,255,255,0.05)", color: "#64748b", label: "—" },
};

export default function SequencePlayer({ sequences }) {
  const [seqIdx,   setSeqIdx]   = useState(0);
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing,  setPlaying]  = useState(false);
  const [speed,    setSpeed]    = useState(800);
  const [filter,   setFilter]   = useState("all"); // all | shot | loss
  const intervalRef = useRef(null);

  // Filtre
  const filtered = sequences.filter(s => {
    if (filter === "shot") return s.outcome === "Şut";
    if (filter === "loss") return s.outcome === "Top Kaybı";
    return true;
  });

  const seq    = filtered[seqIdx];
  const events = seq?.events ?? [];
  const frame  = events[frameIdx];

  // Seq değişince sıfırla
  useEffect(() => {
    setFrameIdx(0);
    setPlaying(false);
  }, [seqIdx, filter]);

  // Otomatik oynatma
  useEffect(() => {
    if (!playing) { clearInterval(intervalRef.current); return; }
    intervalRef.current = setInterval(() => {
      setFrameIdx(i => {
        if (i >= events.length - 1) { setPlaying(false); return i; }
        return i + 1;
      });
    }, speed);
    return () => clearInterval(intervalRef.current);
  }, [playing, speed, events.length]);

  if (!filtered.length) return (
    <div style={{ padding: 40, color: "#64748b", textAlign: "center" }}>
      Bu filtrede sekans yok
    </div>
  );

  // Freeze frame'den oyuncular — bu event'te var mı?
  const freezePlayers = frame?.freeze_frame ?? [];

  // Geçmiş event'lerin pas/carry çizgileri
  const trails = events.slice(0, frameIdx + 1);

  const evStyle = EVENT_COLORS[frame?.type] ?? EVENT_COLORS.default;

  return (
    <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>

      {/* Sol: Sekans Listesi */}
      <div style={{
        width: 240, background: "#1a1d27", borderRadius: 14,
        border: "1px solid #2a2d3e", overflow: "hidden", flexShrink: 0,
      }}>
        {/* Filtre */}
        <div style={{
          display: "flex", gap: 4, padding: "10px 12px",
          borderBottom: "1px solid #2a2d3e",
        }}>
          {[
            { k: "all",  l: "Tümü" },
            { k: "shot", l: "Şut" },
            { k: "loss", l: "Kayıp" },
          ].map(f => (
            <button key={f.k} onClick={() => { setFilter(f.k); setSeqIdx(0); }}
              style={{
                flex: 1, padding: "5px 0", borderRadius: 6, border: "none", cursor: "pointer",
                fontSize: 11, fontWeight: filter === f.k ? 700 : 400,
                background: filter === f.k ? "#4ade80" : "transparent",
                color: filter === f.k ? "#0f1117" : "#64748b",
                transition: "all .15s",
              }}>
              {f.l}
            </button>
          ))}
        </div>

        {/* Liste */}
        <div style={{ maxHeight: 480, overflowY: "auto" }}>
          {filtered.map((s, i) => {
            const isShot = s.outcome === "Şut";
            const active = i === seqIdx;
            return (
              <div key={s.id} onClick={() => setSeqIdx(i)}
                style={{
                  padding: "10px 14px", cursor: "pointer",
                  borderBottom: "1px solid #13151f",
                  background: active ? "rgba(74,222,128,0.08)" : "transparent",
                  borderLeft: active ? "3px solid #4ade80" : "3px solid transparent",
                  transition: "all .15s",
                }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: active ? "#4ade80" : "#64748b", fontFamily: "monospace" }}>
                    #{i + 1}
                  </span>
                  <span style={{
                    fontSize: 10, padding: "2px 7px", borderRadius: 4,
                    background: isShot ? "rgba(249,115,22,0.15)" : "rgba(100,116,139,0.15)",
                    color: isShot ? "#f97316" : "#64748b",
                  }}>
                    {s.outcome}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 3 }}>
                  {s.start_minute}:{String(s.start_second).padStart(2,"0")} · {s.event_count} event
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sağ: Animasyon */}
      <div style={{ flex: 1, minWidth: 300 }}>

        {/* Saha */}
        <div style={{ borderRadius: 12, overflow: "hidden", marginBottom: 12,
          boxShadow: "0 8px 40px rgba(0,0,0,.6)" }}>
          <PitchWithTrails
            trails={trails}
            freezePlayers={freezePlayers}
            currentEvent={frame}
          />
        </div>

        {/* Aktif Event Bilgisi */}
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 14px", borderRadius: 10, marginBottom: 10,
          background: evStyle.bg, border: `1px solid ${evStyle.color}44`,
        }}>
          <span style={{
            padding: "3px 10px", borderRadius: 6, fontSize: 11, fontWeight: 700,
            background: `${evStyle.color}22`, color: evStyle.color,
          }}>
            {evStyle.label}
          </span>
          <span style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>
            {frame?.player_name || "—"}
          </span>
          <span style={{ fontSize: 11, color: "#64748b", marginLeft: "auto" }}>
            {frame?.minute}:{String(frame?.second ?? 0).padStart(2,"0")}
          </span>
        </div>

        {/* Progress */}
        <div style={{ display: "flex", gap: 3, marginBottom: 10 }}>
          {events.map((e, i) => {
            const c = (EVENT_COLORS[e.type] ?? EVENT_COLORS.default).color;
            return (
              <div key={i} onClick={() => { setFrameIdx(i); setPlaying(false); }}
                title={`${e.type} — ${e.player_name}`}
                style={{
                  flex: 1, height: i === frameIdx ? 16 : 5,
                  borderRadius: 3, cursor: "pointer",
                  background: i <= frameIdx ? c : "rgba(255,255,255,0.08)",
                  transition: "all .15s",
                  boxShadow: i === frameIdx ? `0 0 8px ${c}` : "none",
                }} />
            );
          })}
        </div>

        {/* Kontroller */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <Btn onClick={() => { setFrameIdx(0); setPlaying(false); }}>⏮</Btn>
          <Btn onClick={() => setFrameIdx(i => Math.max(0, i - 1))}>◀</Btn>

          <button onClick={() => setPlaying(v => !v)} style={{
            padding: "10px 32px", borderRadius: 8, border: "none", cursor: "pointer",
            background: playing ? "rgba(74,222,128,0.2)" : "rgba(74,222,128,0.1)",
            color: "#4ade80", fontSize: 18,
            border: `1px solid ${playing ? "rgba(74,222,128,0.5)" : "rgba(74,222,128,0.2)"}`,
            transition: "all .2s",
          }}>
            {playing ? "⏸" : "▶"}
          </button>

          <Btn onClick={() => setFrameIdx(i => Math.min(events.length - 1, i + 1))}>▶</Btn>
          <Btn onClick={() => { setFrameIdx(events.length - 1); setPlaying(false); }}>⏭</Btn>

          {/* Hız */}
          <div style={{ marginLeft: "auto", display: "flex", gap: 4,
            background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "4px 6px" }}>
            {[{ l: "0.5×", v: 1600 }, { l: "1×", v: 800 }, { l: "2×", v: 400 }].map(s => (
              <button key={s.v} onClick={() => setSpeed(s.v)} style={{
                padding: "4px 10px", borderRadius: 6, border: "none", cursor: "pointer",
                fontSize: 11, fontFamily: "monospace",
                background: speed === s.v ? "rgba(74,222,128,0.15)" : "transparent",
                color: speed === s.v ? "#4ade80" : "#64748b",
                border: `1px solid ${speed === s.v ? "rgba(74,222,128,0.3)" : "transparent"}`,
              }}>
                {s.l}
              </button>
            ))}
          </div>
        </div>

        {/* Sekans özeti */}
        <div style={{ marginTop: 10, padding: "8px 14px", borderRadius: 8,
          background: "#1a1d27", border: "1px solid #2a2d3e",
          display: "flex", gap: 16, fontSize: 12, color: "#64748b" }}>
          <span>⚽ {seq?.event_count} event</span>
          <span>🕒 {seq?.start_minute}:{String(seq?.start_second ?? 0).padStart(2,"0")} –
                   {seq?.end_minute}:{String(seq?.end_second ?? 0).padStart(2,"0")}</span>
          <span style={{ marginLeft: "auto", color: seq?.outcome === "Şut" ? "#f97316" : "#64748b" }}>
            {seq?.outcome}
          </span>
        </div>
      </div>
    </div>
  );
}

// Sahayı çizgi ve oyuncularla beraber render et
function PitchWithTrails({ trails, freezePlayers, currentEvent }) {
  const W = 800, H = 533;
  const toX = x => (x / 120) * W;
  const toY = y => (y / 80)  * H;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      {/* Zemin */}
      <defs>
        <linearGradient id="sqGr" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a3a1e" />
          <stop offset="100%" stopColor="#142f18" />
        </linearGradient>
      </defs>
      <rect width={W} height={H} fill="url(#sqGr)" rx="8" />

      {/* Çim şeritleri */}
      {Array.from({ length: 8 }, (_, i) => (
        <rect key={i} x={toX(i * 15)} y={0} width={toX(15)} height={H}
          fill={i % 2 === 0 ? "rgba(255,255,255,0.022)" : "transparent"} />
      ))}

      {/* Saha çizgileri */}
      <g stroke="rgba(255,255,255,0.18)" strokeWidth="0.8" fill="none">
        <rect x={toX(0)}   y={toY(0)}  width={toX(120)} height={toY(80)} rx="1" />
        <line x1={toX(60)} y1={toY(0)} x2={toX(60)} y2={toY(80)} />
        <circle cx={toX(60)} cy={toY(40)} r={toX(10)} />
        <rect x={toX(0)}   y={toY(18)} width={toX(18)} height={toY(44)} />
        <rect x={toX(0)}   y={toY(30)} width={toX(6)}  height={toY(20)} />
        <rect x={toX(102)} y={toY(18)} width={toX(18)} height={toY(44)} />
        <rect x={toX(114)} y={toY(30)} width={toX(6)}  height={toY(20)} />
      </g>
      <g fill="rgba(255,255,255,0.25)">
        <circle cx={toX(60)}  cy={toY(40)} r="2.5" />
        <circle cx={toX(12)}  cy={toY(40)} r="2" />
        <circle cx={toX(108)} cy={toY(40)} r="2" />
      </g>

      {/* Geçmiş event çizgileri */}
      {trails.map((ev, i) => {
        if (!ev.x || !ev.end_x) return null;
        const isPas   = ev.type === "Pass";
        const isCarry = ev.type === "Carry";
        if (!isPas && !isCarry) return null;
        const col = isPas ? "#38bdf8" : "#4ade80";
        const x1 = toX(ev.x), y1 = toY(ev.y);
        const x2 = toX(ev.end_x), y2 = toY(ev.end_y);
        const mid = `tr-${i}`;
        return (
          <g key={i} opacity={0.5 + (i / trails.length) * 0.5}>
            <defs>
              <marker id={mid} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill={col} />
              </marker>
            </defs>
            {isPas && (
              <path d={`M${x1},${y1} Q${(x1+x2)/2},${(y1+y2)/2 - 20} ${x2},${y2}`}
                stroke={col} strokeWidth="1.5" fill="none" strokeDasharray="5 3"
                markerEnd={`url(#${mid})`} opacity="0.7" />
            )}
            {isCarry && (
              <line x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={col} strokeWidth="2" strokeDasharray="3 3"
                markerEnd={`url(#${mid})`} opacity="0.6" />
            )}
          </g>
        );
      })}

      {/* Aktif event top konumu */}
      {currentEvent?.x && (
        <g style={{ transition: "transform .35s cubic-bezier(.4,0,.2,1)" }}
           transform={`translate(${toX(currentEvent.x)},${toY(currentEvent.y)})`}>
          <circle r="11" fill="rgba(245,158,11,0.15)" />
          <circle r="6"  fill="#fffdf0" stroke="#f59e0b" strokeWidth="2.5" />
          <circle r="2"  fill="#f59e0b" />
        </g>
      )}
    </svg>
  );
}

function Btn({ onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: "10px 14px", borderRadius: 8,
      background: "rgba(255,255,255,0.05)",
      border: "1px solid rgba(255,255,255,0.08)",
      color: "rgba(255,255,255,0.7)", fontSize: 15, cursor: "pointer",
      transition: "all .15s",
    }}>
      {children}
    </button>
  );
}