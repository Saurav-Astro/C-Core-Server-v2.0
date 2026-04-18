import { formatNumber, formatTimestamp } from "../utils/format";

export function RequestsChart({ samples = [] }) {
  const values = samples.map((sample) => Number(sample?.value || 0));
  const width = 960;
  const height = 320;
  const padding = 28;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;
  const maxValue = Math.max(4, ...values);
  const minValue = 0;
  const range = Math.max(maxValue - minValue, 1);

  const points = values.map((value, index) => {
    const x = padding + (values.length === 1 ? innerWidth / 2 : (index / (values.length - 1)) * innerWidth);
    const y = height - padding - ((value - minValue) / range) * innerHeight;
    return { x, y, value };
  });

  const linePath =
    points.length > 0
      ? points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ")
      : "";
  const areaPath =
    points.length > 1
      ? `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`
      : "";

  const latestValue = values.at(-1) || 0;
  const peakValue = values.length ? Math.max(...values) : 0;
  const latestTimestamp = samples.at(-1)?.timestamp || null;


  return (
    <section className="rounded-3xl border border-white/5 bg-panel/40 p-6 backdrop-blur-md shadow-surface">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-brand-cyan/80">Compute Throughput</p>
          <h2 className="mt-1 text-2xl font-medium tracking-tight text-white">Requests Per Second</h2>
          <p className="mt-2 text-[13px] text-slate-500">
            Current ingestion rate sampled from the server's telemetry thread.
          </p>
        </div>
        <div className="rounded-xl border border-white/5 bg-slate-900/40 px-5 py-3 text-right">
          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Peak Rate</div>
          <div className="mt-1 font-mono text-2xl font-medium text-brand-cyan">{formatNumber(latestValue)}</div>
          <div className="mt-1 text-[10px] text-slate-500 uppercase tracking-wider">
            MAX {formatNumber(peakValue)} {latestTimestamp ? `· SYNCED` : ""}
          </div>
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-white/5 bg-slate-900/20">
        {values.length ? (
          <svg viewBox={`0 0 ${width} ${height}`} className="h-[320px] w-full">
            <defs>
              <linearGradient id="rpsFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(6, 182, 212, 0.2)" />
                <stop offset="100%" stopColor="rgba(6, 182, 212, 0)" />
              </linearGradient>
            </defs>

            {[0.25, 0.5, 0.75, 1].map((ratio) => (
              <line
                key={ratio}
                x1={padding}
                x2={width - padding}
                y1={padding + innerHeight * ratio}
                y2={padding + innerHeight * ratio}
                stroke="rgba(255,255,255,0.05)"
                strokeDasharray="4 6"
              />
            ))}

            {areaPath ? <path d={areaPath} fill="url(#rpsFill)" /> : null}
            {linePath ? (
              <path
                d={linePath}
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ) : null}

            {points.map((point, index) => (
              <circle key={`${point.x}-${index}`} cx={point.x} cy={point.y} r="3" fill="#06b6d4" className="shadow-glow" />
            ))}
          </svg>
        ) : (
          <div className="flex h-[320px] items-center justify-center text-sm text-slate-500">
            Waiting for live samples...
          </div>
        )}
      </div>
    </section>
  );
}
