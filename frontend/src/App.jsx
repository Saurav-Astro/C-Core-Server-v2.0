import { useEffect, useState, startTransition } from "react";
import { API_BASE, fetchJson } from "./api";
import { MetricCard } from "./components/MetricCard";
import { RequestsChart } from "./components/RequestsChart";
import { LogsPanel } from "./components/LogsPanel";
import { ThreadMonitor } from "./components/ThreadMonitor";
import { formatDateTime, formatNumber } from "./utils/format";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "logs", label: "Logs Viewer" },
  { id: "threads", label: "Thread Monitor" },
];

const surfaceClass =
  "rounded-3xl border border-white/5 bg-panel/40 shadow-surface backdrop-blur-md";

export default function App() {
  const [view, setView] = useState("dashboard");
  const [query, setQuery] = useState("");
  const [payload, setPayload] = useState({
    stats: null,
    logs: [],
    threads: null,
  });
  const [connection, setConnection] = useState({
    online: false,
    updatedAt: null,
    error: null,
  });

  useEffect(() => {
    let alive = true;

    const refresh = async () => {
      try {
        const [stats, logs, threads] = await Promise.all([
          fetchJson("/api/stats"),
          fetchJson("/api/logs?limit=50"),
          fetchJson("/api/threads"),
        ]);
        if (!alive) {
          return;
        }
        startTransition(() => {
          setPayload({
            stats,
            logs: logs.logs || [],
            threads,
          });
        });
        setConnection({
          online: true,
          updatedAt: new Date().toISOString(),
          error: null,
        });
      } catch (error) {
        if (!alive) {
          return;
        }
        setConnection((previous) => ({
          ...previous,
          online: false,
          error: error.message || "Unable to reach backend",
        }));
      }
    };

    refresh();
    const intervalId = setInterval(refresh, 2000);
    return () => {
      alive = false;
      clearInterval(intervalId);
    };
  }, []);

  const stats = payload.stats || {};
  const connections = stats.connections || {};
  const performance = stats.performance || {};
  const cache = stats.cache || {};
  const rpsSamples = performance.recent_rps_samples || [];
  const threads = payload.threads || {};

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#020611] text-slate-100">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(102,255,209,0.15),transparent_25%),radial-gradient(circle_at_top_right,rgba(77,215,255,0.12),transparent_22%),linear-gradient(180deg,rgba(4,8,20,1)_0%,rgba(2,6,17,1)_100%)]" />
      <div className="absolute inset-0 bg-cyber-grid bg-[length:42px_42px] opacity-[0.12]" />
      <div className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
      <div className="absolute right-0 top-40 h-96 w-96 rounded-full bg-cyan-400/10 blur-3xl" />

      <main className="relative mx-auto flex min-h-screen max-w-7xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
        <header className={`${surfaceClass} p-8`}>
          <div className="flex flex-wrap items-start justify-between gap-8">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-lg border border-brand-emerald/20 bg-brand-emerald/5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-brand-emerald">
                <span className={`h-1.5 w-1.5 rounded-full ${connection.online ? "bg-brand-emerald animate-pulse" : "bg-brand-rose"}`} />
                {connection.online ? "System Operational" : "System Offline"}
              </div>
              <h1 className="mt-6 text-4xl font-medium tracking-tight text-white sm:text-6xl">
                C-Core Server <span className="text-slate-500 font-light">v2.0</span>
              </h1>
              <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-slate-400">
                A high-performance observability suite for multi-threaded socket operations, 
                featuring real-time telemetry, kernel-level thread monitors, and advanced request analysis.
              </p>
            </div>

            <div className="rounded-2xl border border-white/5 bg-slate-900/40 px-6 py-4">
              <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Controller Entry</div>
              <div className="mt-1 font-mono text-[13px] text-brand-cyan">{API_BASE}</div>
              <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-500">
                <span className="h-1 w-1 rounded-full bg-slate-700" />
                {connection.updatedAt ? `Last Sync: ${formatDateTime(connection.updatedAt)}` : "Syncing..."}
              </div>
            </div>
          </div>

          <div className="mt-8 flex flex-wrap gap-2">
            {TABS.map((tab) => {
              const active = tab.id === view;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setView(tab.id)}
                  className={`rounded-xl border px-5 py-2 text-[13px] font-semibold transition-all duration-200 ${
                    active
                      ? "border-brand-cyan/20 bg-brand-cyan/10 text-white shadow-[0_0_20px_rgba(6,182,212,0.1)]"
                      : "border-white/5 bg-white/5 text-slate-500 hover:border-white/10 hover:bg-white/[0.08] hover:text-slate-300"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {connection.error ? (
            <div className="mt-5 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {connection.error}
            </div>
          ) : null}
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            title="Active Connections"
            value={connections.active || 0}
            subtitle="Sockets currently open and tracked by the server."
            tone="green"
          />
          <MetricCard
            title="Total Requests"
            value={connections.total_requests || 0}
            subtitle="All processed requests, including static files and API calls."
            tone="cyan"
          />
          <MetricCard
            title="Requests / Second"
            value={performance.current_rps || 0}
            subtitle="Recent one-second throughput from the sampler thread."
            tone="amber"
          />
          <MetricCard
            title="Queue Size"
            value={connections.queued || 0}
            subtitle="Accepted sockets waiting in the request queue."
            tone="rose"
          />
          <MetricCard
            title="Cache Hit Rate"
            value={cache.hit_rate || 0}
            suffix="%"
            subtitle="How often the file cache served static assets without disk reads."
            tone="green"
          />
        </section>

        {view === "dashboard" ? (
          <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
            <RequestsChart samples={rpsSamples} />

            <aside className={`${surfaceClass} p-8`}>
              <p className="text-[11px] font-bold uppercase tracking-widest text-brand-cyan/80">System Analytics</p>
              <h2 className="mt-1 text-2xl font-medium tracking-tight text-white">Instance State</h2>

              <div className="mt-8 space-y-4">
                <div className="flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/40 p-4">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-slate-600">Runtime</div>
                  <div className="font-mono text-sm text-white">{formatNumber(performance.uptime_seconds || 0)}s</div>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/40 p-4">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-slate-600">Last Seen</div>
                  <div className="font-mono text-sm text-white">
                    {formatDateTime(performance.last_request_at) || "—"}
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/40 p-4">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-slate-600">Rate Limits</div>
                  <div className="font-mono text-sm text-white">{formatNumber(connections.rate_limited || 0)}</div>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/40 p-4">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-slate-600">Faults</div>
                  <div className="font-mono text-sm text-white">{formatNumber(connections.server_errors || 0)}</div>
                </div>
              </div>
            </aside>
          </section>
        ) : null}

        {view === "logs" ? (
          <LogsPanel logs={payload.logs} query={query} onQueryChange={setQuery} />
        ) : null}

        {view === "threads" ? <ThreadMonitor threads={threads} /> : null}

        <footer className="pb-2 text-center text-xs text-slate-500">
          Polling every 2 seconds. Dashboard data comes from {API_BASE}.
        </footer>
      </main>
    </div>
  );
}
