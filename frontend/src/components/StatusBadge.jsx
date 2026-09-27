import React from 'react';

export default function StatusBadge({ status, text, size = "md" }) {
  const norm = (status || "").toUpperCase();

  let colors = "bg-slate-800 text-slate-300 border-slate-700";
  let dotColor = "bg-slate-400";

  if (norm.includes("HEALTHY") || norm.includes("NORMAL") || norm === "NOT_REACHED_WITHIN_HORIZON") {
    colors = "bg-emerald-950/70 text-emerald-300 border-emerald-800/60";
    dotColor = "bg-emerald-400 animate-pulse";
  } else if (norm.includes("WARNING") || norm.includes("DEGRADED") || norm === "APPROACHING_THRESHOLD") {
    colors = "bg-amber-950/70 text-amber-300 border-amber-800/60";
    dotColor = "bg-amber-400 animate-ping";
  } else if (norm.includes("CRITICAL") || norm.includes("DOWN") || norm === "CURRENTLY_EXCEEDED" || norm === "IMMINENT_BREACH") {
    colors = "bg-rose-950/70 text-rose-300 border-rose-800/60";
    dotColor = "bg-rose-400 animate-ping";
  }

  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs md:text-sm";

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium border rounded-full ${padding} ${colors}`}>
      <span className={`w-2 h-2 rounded-full ${dotColor}`}></span>
      {text || status}
    </span>
  );
}
