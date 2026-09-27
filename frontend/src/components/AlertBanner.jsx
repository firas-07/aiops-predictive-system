import React from 'react';
import { AlertTriangle, Clock, ShieldAlert, CheckCircle2, Info } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function AlertBanner({ earliestThreshold, overallStatus, failureProb, failureRisk }) {
  if (!earliestThreshold) {
    return (
      <div className="bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-800/40 rounded-2xl p-5 shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-white">All Infrastructure Metrics Normal</h3>
              <StatusBadge status="NORMAL" text="Normal Operating State" size="sm" />
            </div>
            <p className="text-sm text-slate-400 mt-0.5">
              No configured metric thresholds are projected to be reached within the 60-minute forecast horizon.
            </p>
          </div>
        </div>
        {failureProb !== null && failureProb !== undefined && (
          <div className="bg-slate-800/80 px-4 py-2 rounded-xl border border-slate-700/60 shrink-0">
            <span className="text-xs text-slate-400 block">Failure Risk Model (2nd Stage)</span>
            <span className="text-sm font-semibold text-slate-200">
              {(failureProb * 100).toFixed(1)}% prob ({failureRisk || 'LOW'})
            </span>
          </div>
        )}
      </div>
    );
  }

  const isCritical = earliestThreshold.risk_level === "CRITICAL" || earliestThreshold.minutes_until_threshold <= 15;
  const isWarning = !isCritical && earliestThreshold.minutes_until_threshold <= 45;

  const bgStyle = isCritical 
    ? "from-rose-950/50 via-slate-900 to-slate-900 border-rose-800/50 shadow-rose-950/30"
    : "from-amber-950/40 via-slate-900 to-slate-900 border-amber-800/40 shadow-amber-950/20";

  const iconBg = isCritical ? "bg-rose-500/20 border-rose-500/30 text-rose-400" : "bg-amber-500/20 border-amber-500/30 text-amber-400";

  return (
    <div className={`bg-gradient-to-r ${bgStyle} border rounded-2xl p-6 shadow-xl relative overflow-hidden`}>
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        {/* Main Alert Info */}
        <div className="flex items-start gap-4">
          <div className={`w-14 h-14 rounded-2xl border flex items-center justify-center shrink-0 ${iconBg}`}>
            {isCritical ? <ShieldAlert className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs uppercase tracking-wider font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {isCritical ? "CRITICAL ALERT" : "EARLY WARNING"}
              </span>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Predicted Threshold Crossing: {earliestThreshold.metric.replace(/_/g, ' ').toUpperCase()}
              </h2>
            </div>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              Based on historical telemetry patterns and recursive LightGBM forecasting, this metric is projected to cross its configured limit ({earliestThreshold.threshold}) in approximately:
            </p>
            <div className="flex items-center gap-4 mt-3 flex-wrap text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" />
                Crossing Time: <strong className="text-white">{earliestThreshold.predicted_time || 'Calculated'}</strong>
              </span>
              <span>•</span>
              <span>Current Value: <strong className="text-white">{earliestThreshold.current_value}</strong></span>
              <span>•</span>
              <span>Threshold Limit: <strong className="text-white">{earliestThreshold.threshold}</strong></span>
            </div>
          </div>
        </div>

        {/* Big Countdown / Time-to-threshold Display */}
        <div className="flex items-center gap-4 shrink-0 bg-slate-800/80 p-4 rounded-xl border border-slate-700/80">
          <div className="text-right">
            <span className="text-xs text-slate-400 uppercase font-semibold tracking-wider block">Estimated Time Remaining</span>
            <div className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-rose-400">
              ~{earliestThreshold.minutes_until_threshold} min
            </div>
          </div>
        </div>
      </div>

      {/* Distinction Notice (Required by Section 1 & Section 19) */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center gap-2 text-xs text-slate-400">
        <Info className="w-4 h-4 text-blue-400 shrink-0" />
        <span>
          <strong>Operational Notice:</strong> Resource threshold crossing indicates impending capacity degradation, not guaranteed total application failure. Second-stage failure probability: <strong>{failureProb !== null ? `${(failureProb * 100).toFixed(1)}%` : 'N/A'}</strong>.
        </span>
      </div>
    </div>
  );
}
