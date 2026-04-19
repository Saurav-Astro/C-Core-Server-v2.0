import { useDeferredValue } from "react";
import { formatLatency, formatTimestamp, toneForStatus } from "../utils/format";

const toneClasses = {
  success: "border-brand-emerald/20 bg-brand-emerald/10 text-brand-emerald",
  warning: "border-brand-amber/20 bg-brand-amber/10 text-brand-amber",
  danger: "border-brand-rose/20 bg-brand-rose/10 text-brand-rose",
  info: "border-brand-cyan/20 bg-brand-cyan/10 text-brand-cyan",
  neutral: "border-white/10 bg-white/5 text-slate-400",
};

export function LogsPanel({ logs = [], query, onQueryChange }) {
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const filteredLogs = deferredQuery
    ? logs.filter((log) => {
        const haystack = [
          log.ip,
          log.method,
          log.path,
          log.status,
          log.thread,
          log.note,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(deferredQuery);
      })
    : logs;

  return (
    <section className="rounded-3xl border border-white/5 bg-panel/40 p-6 backdrop-blur-md shadow-surface">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-brand-cyan/80">Observability</p>
          <h2 className="mt-1 text-2xl font-medium tracking-tight text-white">Request Logs</h2>
          <p className="mt-2 text-[13px] text-slate-500">
            Real-time traffic monitor with multi-threaded execution context.
          </p>
        </div>
        <div className="relative w-full max-w-xs">
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search logs..."
            className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-4 py-2.5 text-[13px] text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-brand-cyan/40 focus:bg-slate-900/80"
          />
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-white/5">
        <div className="grid grid-cols-[1fr_0.8fr_1.5fr_0.8fr_0.8fr_0.8fr_0.6fr] gap-4 border-b border-white/5 bg-slate-900/30 px-5 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">
          <span>Timestamp</span>
          <span>Source</span>
          <span>Request</span>
          <span>Status</span>
          <span>Thread</span>
          <span>Latency</span>
          <span>Origin</span>
        </div>

        <div className="max-h-[500px] overflow-auto">
          {filteredLogs.length ? (
            filteredLogs.map((log, index) => {
              const tone = toneForStatus(log.status);
              const toneClass = toneClasses[tone] || toneClasses.neutral;
              return (
                <div
                  key={`${log.timestamp}-${log.ip}-${index}`}
                  className="grid grid-cols-[1fr_0.8fr_1.5fr_0.8fr_0.8fr_0.8fr_0.6fr] items-center gap-4 border-b border-white/[0.02] px-5 py-3.5 text-[13px] last:border-b-0 hover:bg-white/[0.01]"
                >
                  <div className="font-mono text-[12px] text-slate-500">{formatTimestamp(log.timestamp)}</div>
                  <div className="font-mono text-slate-400">{log.ip}</div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{log.method}</span>
                      <span className="truncate font-mono text-slate-300">{log.path}</span>
                    </div>
                    {log.note ? <div className="mt-0.5 text-[11px] text-slate-600">{log.note}</div> : null}
                  </div>
                  <div>
                    <span className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${toneClass}`}>
                      {log.status}
                    </span>
                  </div>
                  <div className="font-mono text-[12px] text-slate-400">{log.thread}</div>
                  <div className="font-mono text-slate-400">{formatLatency(log.latency_ms)}</div>
                  <div>
                    <span
                      className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        log.cached
                          ? "border-brand-emerald/20 bg-brand-emerald/10 text-brand-emerald"
                          : "border-white/5 bg-white/5 text-slate-600"
                      }`}
                    >
                      {log.cached ? "Cache" : "Disk"}
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="px-4 py-16 text-center text-sm text-slate-500">No log entries match the current filter.</div>
          )}
        </div>
      </div>
    </section>
  );
}
