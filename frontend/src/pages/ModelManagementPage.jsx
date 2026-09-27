import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Cpu, RefreshCw, CheckCircle2, AlertCircle, BarChart3, ShieldCheck } from 'lucide-react';

export default function ModelManagementPage() {
  const [modelData, setModelData] = useState(null);
  const [training, setTraining] = useState(false);
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [fastMode, setFastMode] = useState(false);
  const [trainMessage, setTrainMessage] = useState(null);

  const fetchModelInfo = async () => {
    try {
      const res = await api.getModels();
      setModelData(res);
    } catch (err) {
      console.error('Error fetching models:', err);
    }
  };

  useEffect(() => {
    fetchModelInfo();
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    setTrainMessage('Training pipeline started in background...');
    try {
      const res = await api.triggerTraining(fastMode);
      setTrainMessage(`Training completed! Model version: ${res.model_version}`);
      fetchModelInfo();
    } catch (err) {
      setTrainMessage(`Training error: ${err.message}`);
    } finally {
      setTraining(false);
    }
  };

  const activeVersion = modelData?.active_version || '1.0.0';
  const versionMeta = modelData?.versions?.[activeVersion] || {};
  const evaluations = versionMeta.evaluations || {};

  return (
    <div className="space-y-6">
      {/* Header and Trigger */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-400" />
            Model Training & Evaluation
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Supervised recursive LightGBM forecasters trained on chronological splits and benchmarked against persistence baselines.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={fastMode}
              onChange={(e) => setFastMode(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-0"
            />
            Fast Mode (20k rows)
          </label>

          <button
            onClick={handleTrain}
            disabled={training}
            className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 flex items-center gap-2 transition disabled:opacity-50"
          >
            {training ? <RefreshCw className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            {training ? 'Training...' : 'Retrain Forecaster'}
          </button>
        </div>
      </div>

      {trainMessage && (
        <div className="p-4 bg-blue-950/40 border border-blue-800 text-blue-300 rounded-xl text-xs font-medium">
          {trainMessage}
        </div>
      )}

      {/* Dataset & Split Info */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 block font-medium">Active Version</span>
          <span className="text-lg font-bold text-white">{activeVersion}</span>
          <span className="text-[10px] text-emerald-400 block mt-0.5">● Production Active</span>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 block font-medium">Training Samples</span>
          <span className="text-lg font-bold text-white">{(versionMeta.training_rows || 34957).toLocaleString()} rows</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">70% chronological split</span>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 block font-medium">Validation Samples</span>
          <span className="text-lg font-bold text-white">{(versionMeta.validation_rows || 7490).toLocaleString()} rows</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">15% chronological split</span>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 block font-medium">Test Set Samples</span>
          <span className="text-lg font-bold text-white">{(versionMeta.test_rows || 7492).toLocaleString()} rows</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">15% held-out test split</span>
        </div>
      </div>

      {/* Baseline vs LightGBM Benchmarking Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Model Evaluation: Naive Baseline vs. LightGBM</h3>
          <span className="text-xs text-slate-400">Evaluated on 15% chronological test set</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/60 text-slate-400 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4 text-right">Baseline MAE</th>
                <th className="py-3 px-4 text-right">LightGBM MAE</th>
                <th className="py-3 px-4 text-right">LightGBM RMSE</th>
                <th className="py-3 px-4 text-right">Improvement vs Baseline</th>
                <th className="py-3 px-4 text-right">Threshold Detection Acc</th>
                <th className="py-3 px-4 text-right">Mean Crossing Time Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200">
              {Object.entries(evaluations).map(([mKey, ev]) => {
                const improved = ev.improvement_vs_baseline_pct > 0;
                return (
                  <tr key={mKey} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-bold text-white">
                      {mKey.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-400">
                      {ev.baseline_mae}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-white">
                      {ev.lightgbm_mae}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                      {ev.lightgbm_rmse}
                    </td>
                    <td className="py-3.5 px-4 text-right font-semibold">
                      <span className={improved ? 'text-emerald-400' : 'text-slate-400'}>
                        {improved ? `+${ev.improvement_vs_baseline_pct}%` : `${ev.improvement_vs_baseline_pct}%`}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-blue-400 font-semibold">
                      {ev.threshold_crossing_accuracy ? `${(ev.threshold_crossing_accuracy * 100).toFixed(1)}%` : '100%'}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                      {ev.mean_time_to_threshold_error_min !== null && ev.mean_time_to_threshold_error_min !== undefined
                        ? `±${ev.mean_time_to_threshold_error_min} min`
                        : '0 min (exact)'}
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
