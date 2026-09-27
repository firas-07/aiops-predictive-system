import React from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle2, Clock, ArrowRight } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function AlertPanel({ metrics = [], onSelectMetric }) {
  const activeAlerts = metrics.filter(
    (m) => m.status === 'CURRENT_BREACH' || m.status === 'PREDICTED_BREACH'
  );

  // Sort: CURRENT_BREACH first, then lowest predicted crossing time
  activeAlerts.sort((a, b) => {
    if (a.status === 'CURRENT_BREACH' && b.status !== 'CURRENT_BREACH') return -1;
    if (b.status === 'CURRENT_BREACH' && a.status !== 'CURRENT_BREACH') return 1;
    return (a.predicted_crossing_minutes || 0) - (b.predicted_crossing_minutes || 0);
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Active Predictions & Threshold Alerts
          </h2>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
          {activeAlerts.length} Active {activeAlerts.length === 1 ? 'Alert' : 'Alerts'}
        </span>
      </div>

      <div className="mt-4 space-y-2.5">
        {activeAlerts.length === 0 ? (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-emerald-300 text-xs">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>All 8 metrics are projected to operate within safe thresholds across the 30-minute horizon.</span>
          </div>
        ) : (
          activeAlerts.map((alert) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isCurrent = alert.status === 'CURRENT_BREACH';

            return (
              <div
                key={alert.metric}
                onClick={() => onSelectMetric && onSelectMetric(alert.metric)}
                className={`p-3.5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 cursor-pointer transition hover:scale-[1.01] ${
                  isCritical
                    ? 'bg-rose-950/30 border-rose-800/60 hover:bg-rose-950/50'
                    : 'bg-amber-950/30 border-amber-800/60 hover:bg-amber-950/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                      isCritical
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {isCritical ? 'CRIT' : 'WARN'}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-white">
                        {alert.metric.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <StatusBadge status={alert.status} size="sm" />
                    </div>
                    <p className="text-xs text-slate-300 mt-0.5">
                      {isCurrent ? (
                        <span className="text-rose-300 font-semibold">
                          Currently breaching threshold ({alert.current_value} vs {alert.effective_threshold} {alert.unit})
                        </span>
                      ) : (
                        <span>
                          Predicted to cross limit in{' '}
                          <strong className="text-white">~{alert.predicted_crossing_minutes} min</strong> (Threshold: {alert.operator} {alert.effective_threshold} {alert.unit})
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center">
                  <div className="text-right text-xs">
                    <span className="text-slate-400 block text-[10px] uppercase">Predicted +30m</span>
                    <strong className="text-white text-xs font-mono">
                      {alert.predicted_value_30m} {alert.unit}
                    </strong>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 hover:text-slate-300" />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
