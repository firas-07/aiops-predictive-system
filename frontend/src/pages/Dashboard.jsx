import React, { useState } from 'react';
import MetricCard from '../components/MetricCard';
import AlertPanel from '../components/AlertPanel';
import StatusBadge from '../components/StatusBadge';
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
import { 
  Activity, 
  Server, 
  Cloud, 
  FileSpreadsheet, 
  Clock, 
  Play, 
  RefreshCw, 
  AlertTriangle,
  Info,
  ShieldCheck
} from 'lucide-react';

export default function Dashboard({ 
  currentApp, 
  predictionData, 
  historicalTelemetry = [],
  loading, 
  onRunPredict,
  onNavigateToForecast
}) {
  const [selectedMetric, setSelectedMetric] = useState('cpu_percent');

  const isAzure = currentApp?.telemetry_source === 'azure';
  const metricsList = predictionData?.metrics || [];
  const overallStatus = predictionData?.overall_status || 'NORMAL';
  const breachingCount = predictionData?.metrics_breaching_count || 0;
  const earliestBreach = predictionData?.earliest_breach;

  // Find metric details for the selected chart
  const currentMetricData = metricsList.find(m => m.metric === selectedMetric) || metricsList[0];
  const activeTrajectory = currentMetricData?.forecast || [];
  const effectiveThreshold = currentMetricData?.effective_threshold;
  const operator = currentMetricData?.operator || '>=';
  const unit = currentMetricData?.unit || '';

  // Stitch historical observations (past 30 minutes) + future 30m forecast
  const chartPoints = [];
  const pastPoints = historicalTelemetry.slice(-30);
  
  pastPoints.forEach((p, idx) => {
    const minOffset = - (pastPoints.length - idx);
    chartPoints.push({
      time: `${minOffset}m`,
      actual: p[selectedMetric] !== undefined ? p[selectedMetric] : null,
      forecast: null,
      lower: null,
      upper: null,
    });
  });

  // Current anchor point
  if (currentMetricData) {
    chartPoints.push({
      time: 'Now',
      actual: currentMetricData.current_value,
      forecast: currentMetricData.current_value,
      lower: currentMetricData.current_value,
      upper: currentMetricData.current_value,
    });
  }

  // Future 30-minute forecast points
  activeTrajectory.forEach((pt) => {
    chartPoints.push({
      time: `+${pt.minutes_ahead}m`,
      actual: null,
      forecast: pt.value,
      lower: pt.estimated_lower,
      upper: pt.estimated_upper,
    });
  });

  return (
    <div className="space-y-6">
      {/* Application & Real-time Telemetry Status Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border ${
            isAzure 
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
              : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
          }`}>
            {isAzure ? <Cloud className="w-6 h-6" /> : <FileSpreadsheet className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-lg font-bold text-white tracking-tight">
                {currentApp?.name || 'ChatGPT Azure Prod'}
              </h1>
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                isAzure
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
              }`}>
                {isAzure ? 'Azure Live Telemetry' : 'Sample Telemetry (Dev)'}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
              <span className="flex items-center gap-1 font-mono">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                Prediction Time: {predictionData?.prediction_time ? new Date(predictionData.prediction_time).toLocaleTimeString() : 'Live'}
              </span>
              <span>•</span>
              <span>Horizon: <strong>30 Minutes</strong></span>
              <span>•</span>
              <span>Model Version: <strong className="text-slate-300">{predictionData?.model_version || '1.0.0'}</strong></span>
            </div>
          </div>
        </div>

        {/* Real-time Predict Trigger */}
        <button
          onClick={onRunPredict}
          disabled={loading}
          className="w-full md:w-auto px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 transition disabled:opacity-50 shrink-0"
        >
          <Play className={`w-4 h-4 fill-white ${loading ? 'animate-pulse' : ''}`} />
          {loading ? 'Fetching & Forecasting...' : 'Run Real-Time Prediction'}
        </button>
      </div>

      {/* Overall Application Risk Status Banner */}
      <div className={`p-5 rounded-2xl border shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
        overallStatus === 'CRITICAL'
          ? 'bg-rose-950/40 border-rose-800/80 shadow-rose-950/20'
          : overallStatus === 'AT_RISK'
          ? 'bg-rose-950/30 border-rose-800/50 shadow-rose-950/20'
          : overallStatus === 'WARNING'
          ? 'bg-amber-950/40 border-amber-800/60 shadow-amber-950/20'
          : 'bg-emerald-950/30 border-emerald-800/40 shadow-emerald-950/20'
      }`}>
        <div className="flex items-start gap-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border ${
            overallStatus === 'CRITICAL' || overallStatus === 'AT_RISK'
              ? 'bg-rose-500/20 border-rose-500/40 text-rose-400'
              : overallStatus === 'WARNING'
              ? 'bg-amber-500/20 border-amber-500/40 text-amber-400'
              : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
          }`}>
            {overallStatus === 'NORMAL' ? <ShieldCheck className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
                OVERALL RISK: {overallStatus}
              </span>
              <h2 className="text-sm font-bold text-white">
                {predictionData?.status_summary || 'System Operating Within Normal Limits'}
              </h2>
            </div>
            {earliestBreach && (
              <p className="text-xs text-slate-300 mt-1">
                Earliest predicted crossing: <strong className="text-amber-400 font-bold">{earliestBreach.metric.replace(/_/g, ' ').toUpperCase()}</strong> in approximately <strong className="text-white">~{earliestBreach.predicted_crossing_minutes} minutes</strong> (Threshold: {earliestBreach.effective_threshold}).
              </p>
            )}
          </div>
        </div>

        {/* Second Stage Failure Risk Model Info */}
        {predictionData?.failure_probability_30m !== null && predictionData?.failure_probability_30m !== undefined && (
          <div className="bg-slate-900/90 px-4 py-2.5 rounded-xl border border-slate-800 text-xs shrink-0">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">2nd-Stage Failure Risk</span>
            <div className="font-bold text-white">
              {(predictionData.failure_probability_30m * 100).toFixed(1)}% prob ({predictionData.failure_risk_level || 'LOW'})
            </div>
          </div>
        )}
      </div>

      {/* Notice on Threshold Breach vs Failure */}
      <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center gap-2 text-xs text-slate-400">
        <Info className="w-4 h-4 text-blue-400 shrink-0" />
        <span>
          <strong>Engineering Notice:</strong> A resource threshold crossing represents capacity saturation or performance degradation; it does <em>not</em> imply a guaranteed application crash.
        </span>
      </div>

      {/* Active Predictions & Threshold Alerts Panel */}
      <AlertPanel
        metrics={metricsList}
        onSelectMetric={(m) => setSelectedMetric(m)}
      />

      {/* 8 Metric Cards Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" />
            Monitored Telemetry Parameters (30-Minute Projections)
          </h3>
          <span className="text-xs text-slate-400">Click any card to view 30m trajectory below</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {metricsList.map((m) => (
            <MetricCard
              key={m.metric}
              metricData={m}
              onClick={() => setSelectedMetric(m.metric)}
            />
          ))}
        </div>
      </div>

      {/* 30-Minute Forecast Trajectory Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">
                30-Minute Forecast Trajectory: {selectedMetric.replace(/_/g, ' ').toUpperCase()}
              </h3>
              <StatusBadge status={currentMetricData?.status || 'NORMAL'} size="sm" />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Historical actual telemetry (-30m to Now) + Recursive LightGBM 30-minute projection (Now to +30m)
            </p>
          </div>

          {/* Metric Selector Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto max-w-full pb-1">
            {metricsList.map((m) => (
              <button
                key={m.metric}
                onClick={() => setSelectedMetric(m.metric)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                  selectedMetric === m.metric
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {m.metric.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Recharts Chart */}
        <div className="h-80 w-full">
          {chartPoints.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartPoints} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
                <defs>
                  <linearGradient id="forecastAreaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />

                {/* Effective Threshold Horizontal Reference Line */}
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

                {/* Historical Observations Line */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="#94a3b8"
                  strokeWidth={2.5}
                  dot={false}
                  name="Historical Actual Telemetry"
                />

                {/* Future 30-Minute Forecast Trajectory */}
                <Line
                  type="monotone"
                  dataKey="forecast"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  dot={false}
                  name="30-Min Future Forecast"
                />

                {/* Estimated Uncertainty Band */}
                <Area
                  type="monotone"
                  dataKey="upper"
                  stroke="none"
                  fill="url(#forecastAreaGrad)"
                  name="Estimated Forecast Range"
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500 text-xs">
              Loading forecast trajectory...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
