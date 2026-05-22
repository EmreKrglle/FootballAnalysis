function Pitch({ freezeFrames }) {
  // Saha boyutları — StatsBomb koordinat sistemi 120x80
  const width = 800;
  const height = 533;

  // StatsBomb koordinatını SVG koordinatına çevir
  const toX = (x) => (x / 120) * width;
  const toY = (y) => (y / 80) * height;

  return (
    <svg
      width={width}
      height={height}
      style={{ border: "1px solid #ccc", borderRadius: 8 }}
    >
      {/* Zemin */}
      <rect width={width} height={height} fill="#4a7c59" />

      {/* Saha çizgileri */}
      <g stroke="white" strokeWidth="1.5" fill="none" opacity="0.8">
        {/* Dış çizgi */}
        <rect x={toX(0)} y={toY(0)} width={toX(120)} height={toY(80)} />

        {/* Orta çizgi */}
        <line x1={toX(60)} y1={toY(0)} x2={toX(60)} y2={toY(80)} />

        {/* Orta daire */}
        <circle cx={toX(60)} cy={toY(40)} r={toX(10)} />

        {/* Sol ceza sahası */}
        <rect x={toX(0)} y={toY(18)} width={toX(18)} height={toY(44)} />

        {/* Sol küçük ceza sahası */}
        <rect x={toX(0)} y={toY(30)} width={toX(6)} height={toY(20)} />

        {/* Sağ ceza sahası */}
        <rect x={toX(102)} y={toY(18)} width={toX(18)} height={toY(44)} />

        {/* Sağ küçük ceza sahası */}
        <rect x={toX(114)} y={toY(30)} width={toX(6)} height={toY(20)} />
      </g>

      {/* Oyuncular */}
      {freezeFrames.map((player, index) => (
        <g key={index}>
          {/* Oyuncu dairesi */}
          <circle
            cx={toX(player.x)}
            cy={toY(player.y)}
            r={10}
            fill={player.teammate ? "#3b82f6" : "#ef4444"}
            stroke="white"
            strokeWidth="2"
            opacity={0.9}
          />
          {/* Topu oynayan oyuncuyu büyük göster */}
          {player.actor && (
            <circle
              cx={toX(player.x)}
              cy={toY(player.y)}
              r={14}
              fill="none"
              stroke="yellow"
              strokeWidth="2.5"
            />
          )}
        </g>
      ))}
    </svg>
  );
}

export default Pitch;