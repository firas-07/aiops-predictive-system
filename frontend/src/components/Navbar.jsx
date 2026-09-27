import React from 'react';
import { 
  Activity, 
  LineChart, 
  Sliders, 
  Cpu, 
  Database, 
  ShieldAlert, 
  RefreshCw,
  Plus,
  Cloud,
  FileSpreadsheet,
  Settings
} from 'lucide-react';

export default function Navbar({ 
  activeTab, 
  setActiveTab, 
  applications = [],
  currentApp,
  onSelectApp,
  onOpenAppConfig,
  isReady, 
  onRefresh,
  loading
}) {
  const tabs = [
    { id: 'dashboard', label: 'Live Dashboard', icon: Activity },
    { id: 'forecast', label: '30m Forecasts', icon: LineChart },
    { id: 'thresholds', label: 'Threshold Rules', icon: ShieldAlert },
    { id: 'models', label: 'Models & Training', icon: Cpu },
    { id: 'data', label: 'Data Quality', icon: Database },
  ];

  const isAzure = currentApp?.telemetry_source === 'azure';

  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">
          {/* Brand & App Selector */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base text-white tracking-tight hidden sm:inline">
                  AIOps Predictor
                </span>
                
                {/* Application Switcher Dropdown */}
                <select
                  value={currentApp?.id || ''}
                  onChange={(e) => onSelectApp(e.target.value)}
                  className="bg-slate-800 border border-slate-700 text-white rounded-lg px-2.5 py-1 text-xs font-semibold max-w-[180px] sm:max-w-[220px] truncate"
                >
                  {applications.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name} ({app.telemetry_source.toUpperCase()})
                    </option>
                  ))}
                </select>

                {/* Telemetry Source Badge */}
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded flex items-center gap-1 border ${
                  isAzure 
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' 
                    : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                }`}>
                  {isAzure ? <Cloud className="w-3 h-3" /> : <FileSpreadsheet className="w-3 h-3" />}
                  {isAzure ? 'Azure Live' : 'Sample Dev'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden md:block">Real-Time Azure Telemetry Forecaster</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Action Buttons: Add/Edit App & Refresh */}
          <div className="flex items-center gap-2">
            <button
              onClick={onOpenAppConfig}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
              title="Configure Application or Add Azure Connection"
            >
              <Settings className="w-3.5 h-3.5 text-blue-400" />
              <span className="hidden sm:inline">Settings</span>
            </button>

            <button
              onClick={onRefresh}
              disabled={loading}
              title="Refresh Telemetry & Run Realtime Prediction"
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="lg:hidden border-t border-slate-800 bg-slate-900/95 overflow-x-auto py-2 px-4 flex gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs whitespace-nowrap font-medium transition ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 bg-slate-800/50 hover:bg-slate-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>
    </header>
  );
}
