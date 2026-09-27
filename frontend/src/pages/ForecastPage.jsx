import React, { useState, useEffect } from 'react';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Line, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  ReferenceLine,
  Legend
} from 'recharts';
import { api } from '../services/api';
import { LineChart, Clock, ShieldAlert, Sparkles } from 'lucide-react';
import StatusBadge from '../components/StatusBadge';

export default function ForecastPage({ currentApp, historicalTelemetry = [] }) {
  const [metric, setMetric] = useState('cpu_percent');
  const [horizon, setHorizon] = useState(30);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [predictionResult, setPredictionResult] = useState(null);

  const metricsList = [
    { id: 'cpu_percent', label: 'CPU Utilization' },
    { id: 'memory_percent', label: 'Memory Usage' },
    { id: 'disk_io_mb_s', label: 'Disk I/O' },
    { id: 'latency_ms', label: 'Latency' },
    { id: 'http_errors', label: 'HTTP Errors' },
    { id: 'http_success', label: 'HTTP Success' },
    { id: 'network_mb_s', label: 'Network Throughput' },
    { id: 'request_volume', label: 'Request Volume' },
  ];

  const fetchForecast = async () => {
    if (!currentApp?.id) return;
    setLoading(true);
    try {
      // 1. Fetch real-time 30-minute prediction
      const pred = await api.predictRealtime(currentApp.id, horizon);
      setPredictionResult(pred);

      // 2. Fetch recent telemetry history (past 45 minutes)
      const telem = await api.getApplicationTelemetry(currentApp.id, 45);
      const points = telem.points || [];

      // Combine into unified chronological chart points
      const combined = [];

      // Add historical points
      points.forEach((p, idx) => {
        const offset = - (points.length - idx);
        combined.push({
          timeLabel: `${offset}m`,
          historical: p[metric] !== undefined ? p[metric] : null,
          forecast: null,
          lower: null,
          upper: null,
        });
      });

      // Target metric prediction result
      const metricResult = pred.metrics?.find((m) => m.metric === metric);

      // Stitch transition point
      if (metricResult) {
        combined.push({
          timeLabel: 'Now',
          historical: metricResult.current_value,
          forecast: metricResult.current_value,
          lower: metricResult.current_value,
          upper: metricResult.current_value,
        });

        // Add 30-minute forecast points
        (metricResult.forecast || []).forEach((pt) => {
          combined.push({
            timeLabel: `+${pt.minutes_ahead}m`,
            historical: null,
            forecast: pt.value,
            lower: pt.estimated_lower,
            upper: pt.estimated_upper,
          });
        });
      }

      setChartData(combined);
    } catch (err) {
      console.error('Error generating forecast:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast();
  }, [metric, horizon, currentApp?.id]);

  const targetMetricData = predictionResult?.metrics?.find((m) => m.metric === metric);
  const effectiveThreshold = targetMetricData?.effective_threshold;
  const operator = targetMetricData?.operator || '>=';
  const unit = targetMetricData?.unit || '';

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <LineChart className="w-5 h-5 text-blue-400" />
              30-Minute Real-Time Forecast Trajectories
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Visualizes actual historical telemetry (-45m to Now) and 30-minute recursive LightGBM trajectory (Now to +30m) against effective threshold limits.
            </p>
          </div>

          {/* Horizon Selection Buttons */}
          <div className="flex items-center gap-2 bg-slate-800/80 p-1 rounded-xl border border-slate-700">
            <span className="text-xs text-slate-400 px-2 font-medium flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Horizon:
            </span>
            {[15, 30, 60].map((h) => (
              <button
                key={h}
                onClick={() => setHorizon(h)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  horizon === h
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {h} min
              </button>
            ))}
          </div>
        </div>

        {/* Metric Selector Pills */}
        <div className="flex items-center gap-2 mt-5 overflow-x-auto pb-1">
          {metricsList.map((m) => (
            <button
              key={m.id}
              onClick={() => setMetric(m.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition whitespace-nowrap ${
                metric === m.id
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Threshold Status Card for this metric */}
      {targetMetricData && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs text-slate-400 block font-medium">Effective Threshold Limit</span>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>
                  {operator} {effectiveThreshold} {unit} ({targetMetricData.threshold_percentage}% of {targetMetricData.operational_limit} {unit})
                </span>
                <StatusBadge status={targetMetricData.status} size="sm" />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs text-slate-300">
            <div>
              <span className="text-slate-500 block">Current Telemetry</span>
              <strong className="text-white text-sm">{targetMetricData.current_value} {unit}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Predicted Time-to-Threshold</span>
              <strong className="text-amber-400 text-sm">
                {targetMetricData.status === 'CURRENT_BREACH'
                  ? 'CURRENT BREACH'
                  : targetMetricData.predicted_crossing_minutes !== null 
                  ? `~${targetMetricData.predicted_crossing_minutes} minutes` 
                  : 'No breach projected'}
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* Big Interactive Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="h-96 w-full">
          {loading ? (
            <div className="flex items-center justify-center h-full text-slate-400 text-sm">
              Computing recursive 30-minute projections...
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <defs>
                  <linearGradient id="forecastBandGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#818cf8" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#818cf8" stopOpacity={0.05}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="timeLabel" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />

                {effectiveThreshold && (
                  <ReferenceLine
                    y={effectiveThreshold}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    label={{
                      value: `Threshold: ${operator} ${effectiveThreshold} ${unit}`,
                      fill: '#ef4444',
                      fontSize: 11,
                      position: 'top',
                    }}
                  />
                )}

                {/* Historical Observed Telemetry */}
                <Line
                  type="monotone"
                  dataKey="historical"
                  stroke="#94a3b8"
                  strokeWidth={2.5}
                  dot={false}
                  name="Historical Actual Telemetry"
                />

                {/* Uncertainty Confidence Band */}
                <Area
                  type="monotone"
                  dataKey="upper"
                  stroke="none"
                  fill="url(#forecastBandGrad)"
                  name="Estimated Forecast Range"
                />

                {/* Future 30-Minute Predicted Trajectory */}
                <Line
                  type="monotone"
                  dataKey="forecast"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  dot={false}
                  name="LightGBM Future Forecast"
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
