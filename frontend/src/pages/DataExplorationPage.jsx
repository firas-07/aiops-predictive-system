import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Database, Table, CheckCircle2, AlertTriangle, ArrowUpDown, FileSpreadsheet } from 'lucide-react';

export default function DataExplorationPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSummary = async () => {
      setLoading(true);
      try {
        const res = await api.getDataSummary();
        setSummary(res);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, []);

  const stats = summary?.statistics || {};
  const correlations = summary?.correlations || {};
  const metrics = summary?.metrics || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Database className="w-5 h-5 text-blue-400" />
          Telemetry Data Exploration & Quality
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Inspection of 50,000 synthetic 1-minute telemetry records representing ChatGPT on Azure.
        </p>
      </div>

      {loading && (
        <div className="p-8 text-center text-slate-400 text-sm">
          Loading dataset statistics and correlation matrices...
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-xl text-xs">
          {error}
        </div>
      )}

      {summary && (
        <>
          {/* Quality Overview Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 block font-medium">Total Telemetry Rows</span>
              <span className="text-lg font-bold text-white">{summary.total_records.toLocaleString()}</span>
              <span className="text-[10px] text-slate-500 block mt-0.5">1-minute regular interval</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 block font-medium">Missing Values</span>
              <span className="text-lg font-bold text-emerald-400">0 (0.0%)</span>
              <span className="text-[10px] text-emerald-500 block mt-0.5">Continuous time-series</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 block font-medium">Start Timestamp</span>
              <span className="text-xs font-mono font-bold text-white block mt-1">{summary.start_time}</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 block font-medium">End Timestamp</span>
              <span className="text-xs font-mono font-bold text-white block mt-1">{summary.end_time}</span>
            </div>
          </div>

          {/* Descriptive Statistics Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white">Descriptive Statistics & Quantiles</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/60 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="py-3 px-4">Metric</th>
                    <th className="py-3 px-4 text-right">Mean</th>
                    <th className="py-3 px-4 text-right">Std Dev</th>
                    <th className="py-3 px-4 text-right">Min</th>
                    <th className="py-3 px-4 text-right">p25</th>
                    <th className="py-3 px-4 text-right">Median</th>
                    <th className="py-3 px-4 text-right">p75</th>
                    <th className="py-3 px-4 text-right">Max</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {Object.entries(stats).map(([metricKey, st]) => (
                    <tr key={metricKey} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-bold text-white">
                        {metricKey.replace(/_/g, ' ')}
                      </td>
                      <td className="py-3 px-4 text-right font-mono">{st.mean}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-400">{st.std}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-400">{st.min}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-400">{st.p25}</td>
                      <td className="py-3 px-4 text-right font-mono text-blue-400 font-semibold">{st.median}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-400">{st.p75}</td>
                      <td className="py-3 px-4 text-right font-mono text-rose-400 font-semibold">{st.max}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Cross-Metric Correlation Matrix */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white">Correlation Matrix (Pairwise Pearson r)</h3>
            </div>
            <div className="overflow-x-auto p-4">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                    <th className="p-2">Metric</th>
                    {metrics.map((m) => (
                      <th key={m} className="p-2 text-right font-mono text-[10px]">
                        {m.slice(0, 8)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {metrics.map((rowMetric) => (
                    <tr key={rowMetric} className="hover:bg-slate-800/30">
                      <td className="p-2 font-bold text-white whitespace-nowrap">
                        {rowMetric.replace(/_/g, ' ')}
                      </td>
                      {metrics.map((colMetric) => {
                        const val = correlations[rowMetric]?.[colMetric] ?? 0;
                        const isHigh = Math.abs(val) >= 0.85 && rowMetric !== colMetric;
                        return (
                          <td
                            key={colMetric}
                            className={`p-2 text-right ${
                              rowMetric === colMetric 
                                ? 'text-slate-500' 
                                : isHigh 
                                ? 'text-blue-400 font-bold bg-blue-500/10' 
                                : 'text-slate-300'
                            }`}
                          >
                            {val.toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
