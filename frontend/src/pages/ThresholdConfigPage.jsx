import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ShieldAlert, Save, RefreshCw, CheckCircle2, Info } from 'lucide-react';

export default function ThresholdConfigPage({ currentApp, onReloadThresholds }) {
  const [thresholds, setThresholds] = useState(currentApp?.thresholds || {});
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (currentApp?.thresholds) {
      setThresholds(currentApp.thresholds);
    }
  }, [currentApp]);

  const handlePercentageChange = (metric, val) => {
    const num = parseFloat(val) || 0;
    setThresholds((prev) => {
      const cur = prev[metric] || {};
      const limit = cur.operational_limit || 100;
      return {
        ...prev,
        [metric]: {
          ...cur,
          threshold_percentage: num,
          effective_threshold: (limit * num) / 100,
        },
      };
    });
  };

  const handleLimitChange = (metric, val) => {
    const num = parseFloat(val) || 0;
    setThresholds((prev) => {
      const cur = prev[metric] || {};
      const pct = cur.threshold_percentage || 80;
      return {
        ...prev,
        [metric]: {
          ...cur,
          operational_limit: num,
          effective_threshold: (num * pct) / 100,
        },
      };
    });
  };

  const handleOperatorChange = (metric, op) => {
    setThresholds((prev) => ({
      ...prev,
      [metric]: {
        ...prev[metric],
        operator: op,
      },
    }));
  };

  const handleToggle = (metric) => {
    setThresholds((prev) => ({
      ...prev,
      [metric]: {
        ...prev[metric],
        enabled: !prev[metric]?.enabled,
      },
    }));
  };

  const handleSave = async () => {
    if (!currentApp?.id) return;
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      await api.updateApplicationThresholds(currentApp.id, thresholds);
      setSaveSuccess(true);
      if (onReloadThresholds) onReloadThresholds();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setError(err.message || 'Failed to update thresholds');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-blue-400" />
            Threshold Configuration & Normalization
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            All thresholds are entered as <strong>Percentages (%)</strong> and automatically converted into effective native metric units.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 flex items-center gap-2 transition disabled:opacity-50"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Thresholds
        </button>
      </div>

      {/* Explanatory Conversion Banner */}
      <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl flex items-start gap-3 text-xs text-slate-300">
        <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-white block mb-0.5">Threshold Normalization Formula:</strong>
          <span>
            <code className="text-blue-300 bg-slate-800 px-1.5 py-0.5 rounded font-mono">
              Effective Threshold = Operational Limit × (Threshold % / 100)
            </code>
            . For instance, Latency with an operational limit of 500 ms at 80% yields an effective threshold of <strong>400 ms</strong>.
          </span>
        </div>
      </div>

      {saveSuccess && (
        <div className="p-4 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          Threshold configurations saved successfully. Real-time predictions will immediately use these limits.
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-800 text-rose-300 rounded-xl text-xs">
          {error}
        </div>
      )}

      {/* Threshold Rules Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/60 text-slate-400 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Operator</th>
                <th className="py-3 px-4 text-right">Threshold %</th>
                <th className="py-3 px-4 text-right">Operational Limit</th>
                <th className="py-3 px-4 text-right">Effective Threshold</th>
                <th className="py-3 px-4">Unit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200">
              {Object.entries(thresholds).map(([metricKey, conf]) => {
                const effective = ((conf.operational_limit || 100) * (conf.threshold_percentage || 80)) / 100;
                return (
                  <tr key={metricKey} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-bold text-white">
                      {metricKey.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3.5 px-4">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={conf.enabled}
                          onChange={() => handleToggle(metricKey)}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                        <span className="ml-2 text-xs font-medium text-slate-400">
                          {conf.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </label>
                    </td>
                    <td className="py-3.5 px-4">
                      <select
                        value={conf.operator || '>='}
                        onChange={(e) => handleOperatorChange(metricKey, e.target.value)}
                        className="bg-slate-800 border border-slate-700 text-white rounded-lg px-2.5 py-1 text-xs font-semibold"
                      >
                        <option value=">=">&gt;= (Greater or equal)</option>
                        <option value=">">&gt; (Strictly greater)</option>
                        <option value="<=">&lt;= (Less or equal)</option>
                        <option value="<">&lt; (Strictly less)</option>
                      </select>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center gap-1">
                        <input
                          type="number"
                          step="1"
                          min="0"
                          max="200"
                          value={conf.threshold_percentage}
                          onChange={(e) => handlePercentageChange(metricKey, e.target.value)}
                          className="w-20 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white font-bold text-right"
                        />
                        <span className="text-slate-400 font-bold">%</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <input
                        type="number"
                        step="1"
                        min="1"
                        value={conf.operational_limit}
                        onChange={(e) => handleLimitChange(metricKey, e.target.value)}
                        className="w-24 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 text-right font-mono"
                      />
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <strong className="text-amber-400 font-mono text-sm">
                        {conf.operator} {effective.toFixed(1)}
                      </strong>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 font-mono">
                      {conf.unit}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
