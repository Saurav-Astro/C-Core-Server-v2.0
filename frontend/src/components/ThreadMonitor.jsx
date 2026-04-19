import { formatDateTime, formatNumber, toneForWorker } from "../utils/format";

const workerToneClasses = {
  success: "border-brand-emerald/20 bg-brand-emerald/10 text-brand-emerald",
  warning: "border-brand-amber/20 bg-brand-amber/10 text-brand-amber",
  danger: "border-brand-rose/20 bg-brand-rose/10 text-brand-rose",
  neutral: "border-white/5 bg-white/5 text-slate-500",
};

export function ThreadMonitor({ threads }) {
  const workers = threads?.workers ?? [];
  const total = Number(threads?.worker_count || workers.length || 0);
  const busy = Number(threads?.busy_workers || 0);
  const idle = Number(threads?.idle_workers || Math.max(0, total - busy));
  const queued = Number(threads?.queue_size || 0);
  const completed = workers.reduce((sum, worker) => sum + Number(worker.tasks_completed || 0), 0);


  return (
    <section className="rounded-3xl border border-white/5 bg-panel/40 p-6 backdrop-blur-md shadow-surface">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-brand-cyan/80">Kernel Scheduling</p>
          <h2 className="mt-1 text-2xl font-medium tracking-tight text-white">Thread Pool Monitor</h2>
          <p className="mt-2 text-[13px] text-slate-500">
            Fixed worker pool managing non-blocking socket I/O operations.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-white/5 bg-slate-900/40 px-4 py-2.5">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Active</div>
            <div className="mt-0.5 font-mono text-xl font-medium text-white">{formatNumber(busy)}</div>
          </div>
          <div className="rounded-xl border border-white/5 bg-slate-900/40 px-4 py-2.5">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Pending</div>
            <div className="mt-0.5 font-mono text-xl font-medium text-white">{formatNumber(queued)}</div>
          </div>
        </div>
      </div>

      <div className="mt-8 rounded-2xl border border-white/5 bg-slate-900/20 p-5">
        <div className="flex items-center justify-between gap-4 text-[12px] font-medium text-slate-500">
          <span className="uppercase tracking-widest">Pool Utilization</span>
          <span className="font-mono text-slate-300">
            {formatNumber(busy)} / {formatNumber(total)} Threads
          </span>
        </div>
        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-emerald via-brand-cyan to-brand-blue transition-all duration-700 ease-out"
            style={{ width: `${total ? (busy / total) * 100 : 0}%` }}
          />
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        {workers.length ? (
          workers.map((worker) => {
            const tone = toneForWorker(worker.status);
            const toneClass = workerToneClasses[tone] || workerToneClasses.neutral;
            return (
              <article key={worker.name} className="rounded-2xl border border-white/5 bg-slate-900/30 p-4 transition-colors hover:border-white/10">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={`h-2 w-2 rounded-full ${toneClass.split(' ')[2].replace('text-', 'bg-')}`} />
                    <h3 className="text-sm font-medium text-white">{worker.name}</h3>
                  </div>
                  <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${toneClass}`}>
                    {worker.status}
                  </span>
                </div>
                
                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Route</div>
                    <div className="mt-1 truncate font-mono text-[12px] text-slate-300">{worker.current_path || "—"}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Tasks</div>
                    <div className="mt-1 font-mono text-[12px] text-white">{formatNumber(worker.tasks_completed)}</div>
                  </div>
                </div>
              </article>
            );
          })
        ) : (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/60 p-10 text-center text-sm text-slate-500 xl:col-span-2">
            Worker information will appear once the server starts and threads begin accepting connections.
          </div>
        )}
      </div>
    </section>
  );
}
