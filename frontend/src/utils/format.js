const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
});

const compactFormatter = new Intl.NumberFormat(undefined, {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatNumber(value) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  return numberFormatter.format(safe);
}

export function formatCompact(value) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  return compactFormatter.format(safe);
}

export function formatTimestamp(value) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatDateTime(value) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatLatency(value) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  return `${safe.toFixed(2)} ms`;
}

export function formatBytes(value) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  if (safe < 1024) {
    return `${formatNumber(safe)} B`;
  }
  if (safe < 1024 ** 2) {
    return `${(safe / 1024).toFixed(1)} KB`;
  }
  if (safe < 1024 ** 3) {
    return `${(safe / 1024 ** 2).toFixed(1)} MB`;
  }
  return `${(safe / 1024 ** 3).toFixed(1)} GB`;
}

export function toneForStatus(status) {
  const code = Number(status);
  if (code >= 500) {
    return "danger";
  }
  if (code >= 400) {
    return "warning";
  }
  if (code >= 300) {
    return "info";
  }
  if (code >= 200) {
    return "success";
  }
  return "neutral";
}

export function toneForWorker(status) {
  switch (status) {
    case "busy":
      return "warning";
    case "idle":
      return "success";
    case "terminated":
    case "stopping":
      return "danger";
    default:
      return "neutral";
  }
}
