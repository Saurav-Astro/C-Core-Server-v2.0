import { useAnimatedNumber } from "../hooks/useAnimatedNumber";
import { formatNumber } from "../utils/format";

const toneStyles = {
  cyan: "border-brand-cyan/20 bg-panel/40",
  green: "border-brand-emerald/20 bg-panel/40",
  amber: "border-brand-amber/20 bg-panel/40",
  rose: "border-brand-rose/20 bg-panel/40",
};

const accentPill = {
  cyan: "text-brand-cyan",
  green: "text-brand-emerald",
  amber: "text-brand-amber",
  rose: "text-brand-rose",
};

export function MetricCard({ title, value, subtitle, suffix = "", tone = "cyan" }) {
  const animatedValue = useAnimatedNumber(value);
  const resolvedTone = toneStyles[tone] || toneStyles.cyan;
  const resolvedPill = accentPill[tone] || accentPill.cyan;

  return (
    <article className={`rounded-3xl border p-5 backdrop-blur-md transition-all duration-300 hover:border-white/20 hover:bg-slate-900/40 hover:shadow-surface ${resolvedTone}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">{title}</p>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-mono text-3xl font-medium tracking-tight text-white">{formatNumber(animatedValue)}</span>
            {suffix ? <span className="text-sm font-medium text-slate-400">{suffix}</span> : null}
          </div>
        </div>
        <div className="mt-1 flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${resolvedPill.replace("text-", "bg-")}`} />
          <span className={`text-[10px] font-bold uppercase tracking-widest ${resolvedPill}`}>
            Live
          </span>
        </div>
      </div>
      {subtitle ? <p className="mt-4 text-[13px] leading-relaxed text-slate-500">{subtitle}</p> : null}
    </article>
  );
}
