import React from 'react';
import { Clock, TrendingUp, AlertCircle, ShieldAlert } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function MetricCard({ metricData, onClick }) {
  if (!metricData) return null;

  const {
    metric,
    unit,
    current_value,
    threshold_percentage,
    operational_limit,
    effective_threshold,
    operator,
    predicted_value_30m,
    status,
    predicted_crossing_minutes,
    severity,
  } = metricData;

  const isCurrentBreach = status === 'CURRENT_BREACH';
  const isPredictedBreach = status === 'PREDICTED_BREACH';
  const isCritical = severity === 'CRITICAL';

  // Calculate percentage of effective threshold for visual bar
  const ratio = effective_threshold > 0 ? (current_value / effective_threshold) * 100 : 50;
  const progressWidth = Math.min(100, Math.max(5, Math.round(ratio)));

  let barColor = 'bg-blue-500';
  let cardBorder = 'border-slate-800 hover:border-slate-700';

  if (isCurrentBreach) {
    barColor = 'bg-rose-500';
    cardBorder = 'border-rose-800/80 bg-rose-950/20 shadow-rose-950/20';
  } else if (isPredictedBreach) {
    if (isCritical) {
      barColor = 'bg-rose-500';
      cardBorder = 'border-rose-800/50 bg-rose-950/10';
    } else {
      barColor = 'bg-amber-500';
      cardBorder = 'border-amber-800/50 bg-amber-950/10';
    }
  }

  const metricDisplayName = metric.replace(/_/g, ' ');

  return (
    <div
      onClick={onClick}
      className={`bg-slate-900 border rounded-2xl p-5 transition shadow-sm cursor-pointer hover:scale-[1.01] ${cardBorder}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
          {metricDisplayName}
        </span>
        <StatusBadge status={status} size="sm" />
      </div>

      {/* Main Numbers: Current vs Threshold */}
      <div className="mt-3 flex items-baseline justify-between">
        <div>
          <span className="text-2xl font-bold text-white tracking-tight">
            {typeof current_value === 'number' ? (current_value % 1 !== 0 ? current_value.toFixed(1) : current_value) : current_value}
          </span>
          <span className="text-xs font-medium text-slate-400 ml-1">{unit}</span>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-slate-400 block uppercase">Threshold</span>
          <span className="text-xs font-bold text-slate-200">
            {threshold_percentage}% ({operator} {effective_threshold} {unit})
          </span>
        </div>
      </div>

      {/* Progress towards threshold limit */}
      <div className="mt-3 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${progressWidth}%` }}
        ></div>
      </div>

      {/* Time-to-Threshold & Predicted +30m */}
      <div className="mt-3.5 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs">
        <span className="text-slate-400 flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          Time-to-Threshold:
        </span>
        <span className="font-extrabold">
          {isCurrentBreach ? (
            <span className="text-rose-400 animate-pulse font-black">CURRENT BREACH</span>
          ) : isPredictedBreach ? (
            <span className={isCritical ? 'text-rose-400' : 'text-amber-400'}>
              ~{predicted_crossing_minutes} min
            </span>
          ) : (
            <span className="text-emerald-400 font-semibold">Safe (No Breach)</span>
          )}
        </span>
      </div>

      <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
        <span>Predicted at +30m:</span>
        <strong className="text-slate-300 font-mono">
          {typeof predicted_value_30m === 'number' ? predicted_value_30m.toFixed(1) : predicted_value_30m} {unit}
        </strong>
      </div>
    </div>
  );
}
