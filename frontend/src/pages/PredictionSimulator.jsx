import React, { useState } from 'react';
import { api } from '../services/api';
import { Sliders, Play, RefreshCw, AlertTriangle, ShieldCheck, Zap } from 'lucide-react';
import StatusBadge from '../components/StatusBadge';

export default function PredictionSimulator({ thresholdConfig }) {
  const defaultMetrics = {
    cpu_percent: 72.0,
    memory_percent: 70.0,
    disk_io_mb_s: 45.0,
    latency_ms: 300.0,
    http_errors: 12.0,
    http_success: 2400.0,
    network_mb_s: 35.0,
    request_volume: 2500.0,
  };

  const [metrics, setMetrics] = useState(defaultMetrics);
  const [horizon, setHorizon] = useState(60);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Presets for quick operational scenarios
  const applyPreset = (type) => {
    if (type === 'normal') {
      setMetrics({
        cpu_percent: 38.0,
        memory_percent: 52.0,
        disk_io_mb_s: 22.0,
        latency_ms: 120.0,
        http_errors: 2.0,
        http_success: 1600.0,
        network_mb_s: 18.0,
        request_volume: 1605.0,
      });
    } else if (type === 'high_cpu') {
      setMetrics({
        cpu_percent: 86.0,
        memory_percent: 68.0,
        disk_io_mb_s: 60.0,
        latency_ms: 380.0,
        http_errors: 25.0,
        http_success: 3800.0,
        network_mb_s: 48.0,
        request_volume: 3850.0,
      });
    } else if (type === 'memory_leak') {
      setMetrics({
        cpu_percent: 55.0,
        memory_percent: 82.5,
        disk_io_mb_s: 35.0,
        latency_ms: 410.0,
        http_errors: 18.0,
        http_success: 2100.0,
        network_mb_s: 25.0,
        request_volume: 2120.0,
      });
    } else if (type === 'incident_spike') {
      setMetrics({
        cpu_percent: 94.0,
        memory_percent: 86.0,
        disk_io_mb_s: 78.0,
        latency_ms: 550.0,
        http_errors: 75.0,
        http_success: 4400.0,
        network_mb_s: 68.0,
        request_volume: 4500.0,
      });
    }
  };

  const handleInputChange = (field, val) => {
    setMetrics(prev => ({ ...prev, [field]: parseFloat(val) || 0 }));
  };

  const runPrediction = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        app_id: 'chatgpt-azure-prod',
        latest_metrics: metrics,
        forecast_horizon_minutes: horizon,
      };
      const res = await api.predict(payload);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Presets */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Sliders className="w-5 h-5 text-blue-400" />
              What-If Prediction Simulator
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Submit custom latest telemetry metrics to forecast exact time-to-threshold crossings using trained LightGBM models.
            </p>
          </div>

          {/* Preset Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400 mr-1 font-medium">Scenarios:</span>
            <button
              onClick={() => applyPreset('normal')}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition"
            >
              Normal Load
            </button>
            <button
              onClick={() => applyPreset('high_cpu')}
              className="px-2.5 py-1 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 rounded-lg text-xs font-medium transition"
            >
              CPU Surge
            </button>
            <button
              onClick={() => applyPreset('memory_leak')}
              className="px-2.5 py-1 bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 rounded-lg text-xs font-medium transition"
            >
              Memory Leak
            </button>
            <button
              onClick={() => applyPreset('incident_spike')}
              className="px-2.5 py-1 bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 rounded-lg text-xs font-medium transition"
            >
              Major Incident
            </button>
          </div>
        </div>
      </div>

      {/* Input Grid Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 text-slate-300">
          Input Application Telemetry State
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { id: 'cpu_percent', label: 'CPU Percent (%)', min: 0, max: 100, step: 0.5 },
            { id: 'memory_percent', label: 'Memory Percent (%)', min: 0, max: 100, step: 0.5 },
            { id: 'disk_io_mb_s', label: 'Disk I/O (MB/s)', min: 0, max: 150, step: 1 },
            { id: 'latency_ms', label: 'Latency (ms)', min: 50, max: 2000, step: 10 },
            { id: 'http_errors', label: 'HTTP Errors (/min)', min: 0, max: 500, step: 1 },
            { id: 'http_success', label: 'HTTP Success (/min)', min: 0, max: 10000, step: 50 },
            { id: 'network_mb_s', label: 'Network (MB/s)', min: 0, max: 200, step: 1 },
            { id: 'request_volume', label: 'Request Volume (/min)', min: 0, max: 10000, step: 50 },
          ].map((field) => (
            <div key={field.id} className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/60">
              <div className="flex items-center justify-between text-xs text-slate-300 font-medium mb-1.5">
                <label htmlFor={field.id}>{field.label}</label>
                <span className="font-bold text-blue-400">{metrics[field.id]}</span>
              </div>
              <input
                type="range"
                id={field.id}
                min={field.min}
                max={field.max}
                step={field.step}
                value={metrics[field.id]}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <input
                type="number"
                value={metrics[field.id]}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className="mt-2 w-full px-2 py-1 bg-slate-900 border border-slate-700 rounded text-xs text-white"
              />
            </div>
          ))}
        </div>

        {/* Action Row */}
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-medium">Forecast Horizon:</span>
            <select
              value={horizon}
              onChange={(e) => setHorizon(parseInt(e.target.value))}
              className="bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-xs font-semibold"
            >
              <option value={15}>15 Minutes</option>
              <option value={30}>30 Minutes</option>
              <option value={60}>60 Minutes</option>
              <option value={120}>120 Minutes</option>
            </select>
          </div>

          <button
            onClick={runPrediction}
            disabled={loading}
            className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 transition disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
            Calculate Time-to-Threshold
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-800 text-rose-300 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          {/* Earliest Threshold Highlight */}
          {result.earliest_threshold ? (
            <div className="p-5 bg-amber-950/40 border border-amber-800/60 rounded-2xl flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0" />
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Earliest Predicted Crossing: {result.earliest_threshold.metric.replace(/_/g, ' ').toUpperCase()}
                  </h3>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Threshold of {result.earliest_threshold.threshold} is projected to be reached in approx{' '}
                    <strong className="text-amber-400 font-bold">{result.earliest_threshold.minutes_until_threshold} minutes</strong>.
                  </p>
                </div>
              </div>
              <StatusBadge status={result.earliest_threshold.risk_level} />
            </div>
          ) : (
            <div className="p-5 bg-emerald-950/40 border border-emerald-800/60 rounded-2xl flex items-center gap-3">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              <p className="text-sm text-emerald-300 font-semibold">
                No configured thresholds are projected to be breached within the {horizon}-minute window.
              </p>
            </div>
          )}

          {/* Summary Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white">Time-to-Threshold Prediction Breakdown</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/60 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="py-3 px-4">Metric</th>
                    <th className="py-3 px-4 text-right">Current Value</th>
                    <th className="py-3 px-4 text-right">Threshold Limit</th>
                    <th className="py-3 px-4 text-right">Time-to-Threshold</th>
                    <th className="py-3 px-4 text-center">Operational Status</th>
                    <th className="py-3 px-4">Recommendation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {Object.entries(result.threshold_predictions || {}).map(([metricKey, pred]) => (
                    <tr key={metricKey} className="hover:bg-slate-800/30 transition">
                      <td className="py-3.5 px-4 font-bold text-white">
                        {metricKey.replace(/_/g, ' ')}
                      </td>
                      <td className="py-3.5 px-4 text-right font-medium">
                        {pred.current_value}
                      </td>
                      <td className="py-3.5 px-4 text-right font-semibold text-slate-300">
                        {pred.operator} {pred.threshold_value}
                      </td>
                      <td className="py-3.5 px-4 text-right font-extrabold text-sm">
                        {pred.time_to_threshold_minutes !== null ? (
                          <span className={pred.time_to_threshold_minutes <= 15 ? 'text-rose-400' : 'text-amber-400'}>
                            ~{pred.time_to_threshold_minutes} min
                          </span>
                        ) : (
                          <span className="text-emerald-400 font-normal">Safe (not reached)</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <StatusBadge status={pred.status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 text-xs">
                        {pred.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
