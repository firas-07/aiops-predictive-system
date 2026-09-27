import React, { useState } from 'react';
import { X, Cloud, FileSpreadsheet, Shield, KeyRound, Server } from 'lucide-react';

export default function AppConfigModal({ isOpen, onClose, onSave, initialData }) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    id: initialData?.id || `app-${Date.now().toString().slice(-4)}`,
    name: initialData?.name || '',
    telemetry_source: initialData?.telemetry_source || 'csv',
    azure_config: {
      tenant_id: initialData?.azure_config?.tenant_id || '',
      client_id: initialData?.azure_config?.client_id || '',
      client_secret: '',
      subscription_id: initialData?.azure_config?.subscription_id || '',
      resource_group: initialData?.azure_config?.resource_group || '',
      resource_name: initialData?.azure_config?.resource_name || '',
      telemetry_service: initialData?.azure_config?.telemetry_service || 'azure_monitor',
    },
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Application name is required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save application');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">
                {initialData ? 'Edit Application Settings' : 'Configure New Application'}
              </h2>
              <p className="text-xs text-slate-400">Configure telemetry connection and Azure credentials</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-xl text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* Basic Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Application Identifier (ID)</label>
              <input
                type="text"
                disabled={!!initialData}
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-blue-500 disabled:opacity-60"
                placeholder="e.g. chatgpt-azure-prod"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Application Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-blue-500"
                placeholder="e.g. ChatGPT Production Cluster"
                required
              />
            </div>
          </div>

          {/* Telemetry Source Switch */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">Telemetry Source Mode</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition ${
                  formData.telemetry_source === 'csv'
                    ? 'bg-blue-600/10 border-blue-500 text-white'
                    : 'bg-slate-800/50 border-slate-700/60 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <input
                  type="radio"
                  name="telemetry_source"
                  value="csv"
                  checked={formData.telemetry_source === 'csv'}
                  onChange={() => setFormData({ ...formData, telemetry_source: 'csv' })}
                  className="mt-0.5 text-blue-600 focus:ring-0"
                />
                <div>
                  <div className="flex items-center gap-1.5 font-bold text-xs">
                    <FileSpreadsheet className="w-4 h-4 text-blue-400" />
                    Sample Dataset (Dev)
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Offline development mode using synthetic telemetry CSV without requiring Azure credentials.
                  </p>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition ${
                  formData.telemetry_source === 'azure'
                    ? 'bg-blue-600/10 border-blue-500 text-white'
                    : 'bg-slate-800/50 border-slate-700/60 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <input
                  type="radio"
                  name="telemetry_source"
                  value="azure"
                  checked={formData.telemetry_source === 'azure'}
                  onChange={() => setFormData({ ...formData, telemetry_source: 'azure' })}
                  className="mt-0.5 text-blue-600 focus:ring-0"
                />
                <div>
                  <div className="flex items-center gap-1.5 font-bold text-xs">
                    <Cloud className="w-4 h-4 text-emerald-400" />
                    Azure Telemetry (Production)
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Real-time connection via Azure Monitor, Application Insights, or Log Analytics.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Azure Credentials (Only required if Azure source selected) */}
          {formData.telemetry_source === 'azure' && (
            <div className="p-4 bg-slate-800/40 border border-slate-800 rounded-xl space-y-4">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <Shield className="w-4 h-4" />
                Azure Active Directory & Resource Configuration
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">Azure Tenant ID</label>
                  <input
                    type="text"
                    value={formData.azure_config.tenant_id}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        azure_config: { ...formData.azure_config, tenant_id: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">Azure Client ID</label>
                  <input
                    type="text"
                    value={formData.azure_config.client_id}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        azure_config: { ...formData.azure_config, client_id: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                    <KeyRound className="w-3 h-3 text-amber-400" />
                    Azure Client Secret
                  </label>
                  <input
                    type="password"
                    value={formData.azure_config.client_secret}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        azure_config: { ...formData.azure_config, client_secret: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                    placeholder={initialData ? '•••••••• (leave blank to keep existing)' : 'Enter client secret'}
                  />
                  <span className="text-[10px] text-slate-500 block mt-0.5">
                    Encrypted on backend, never leaked to frontend.
                  </span>
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">Subscription ID</label>
                  <input
                    type="text"
                    value={formData.azure_config.subscription_id}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        azure_config: { ...formData.azure_config, subscription_id: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                    placeholder="Subscription GUID"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">Resource Group</label>
                  <input
                    type="text"
                    value={formData.azure_config.resource_group}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        azure_config: { ...formData.azure_config, resource_group: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                    placeholder="e.g. rg-production-eastus"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">Resource / App Name</label>
                  <input
                    type="text"
                    value={formData.azure_config.resource_name}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        azure_config: { ...formData.azure_config, resource_name: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                    placeholder="e.g. chatgpt-web-prod"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 transition disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
