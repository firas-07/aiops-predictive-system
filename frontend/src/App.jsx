import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import ForecastPage from './pages/ForecastPage';
import ThresholdConfigPage from './pages/ThresholdConfigPage';
import ModelManagementPage from './pages/ModelManagementPage';
import DataExplorationPage from './pages/DataExplorationPage';
import AppConfigModal from './components/AppConfigModal';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [applications, setApplications] = useState([]);
  const [currentAppId, setCurrentAppId] = useState('');
  const [currentApp, setCurrentApp] = useState(null);
  const [predictionData, setPredictionData] = useState(null);
  const [historicalTelemetry, setHistoricalTelemetry] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  // 1. Load Applications List
  const loadApplications = async () => {
    try {
      const apps = await api.listApplications();
      setApplications(apps);
      if (apps.length > 0) {
        const selected = currentAppId ? apps.find(a => a.id === currentAppId) || apps[0] : apps[0];
        setCurrentAppId(selected.id);
        setCurrentApp(selected);
      }
    } catch (err) {
      console.warn('Failed to load applications:', err);
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  // 2. Fetch Real-time Telemetry & Predictions for Selected Application
  const runPrediction = async (appId) => {
    const targetId = appId || currentAppId;
    if (!targetId) return;

    setLoading(true);
    try {
      // Fetch latest 30-minute real-time prediction
      const pred = await api.predictRealtime(targetId, 30);
      setPredictionData(pred);

      // Fetch recent historical telemetry window for charting
      const telem = await api.getApplicationTelemetry(targetId, 60);
      setHistoricalTelemetry(telem.points || []);
    } catch (err) {
      console.error('Error running real-time prediction:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentAppId) {
      const app = applications.find(a => a.id === currentAppId);
      setCurrentApp(app || null);
      runPrediction(currentAppId);
    }
  }, [currentAppId]);

  // Periodic real-time update every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      if (currentAppId) {
        runPrediction(currentAppId);
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [currentAppId]);

  const handleSelectApp = (appId) => {
    setCurrentAppId(appId);
  };

  const handleSaveAppConfig = async (formData) => {
    if (formData.id === currentApp?.id) {
      await api.updateApplication(formData.id, formData);
    } else {
      await api.createApplication(formData);
    }
    await loadApplications();
    setCurrentAppId(formData.id);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        applications={applications}
        currentApp={currentApp}
        onSelectApp={handleSelectApp}
        onOpenAppConfig={() => setIsConfigModalOpen(true)}
        isReady={!!predictionData}
        onRefresh={() => runPrediction(currentAppId)}
        loading={loading}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <Dashboard
            currentApp={currentApp}
            predictionData={predictionData}
            historicalTelemetry={historicalTelemetry}
            loading={loading}
            onRunPredict={() => runPrediction(currentAppId)}
            onNavigateToForecast={() => setActiveTab('forecast')}
          />
        )}

        {activeTab === 'forecast' && (
          <ForecastPage
            currentApp={currentApp}
            historicalTelemetry={historicalTelemetry}
          />
        )}

        {activeTab === 'thresholds' && (
          <ThresholdConfigPage
            currentApp={currentApp}
            onReloadThresholds={loadApplications}
          />
        )}

        {activeTab === 'models' && <ModelManagementPage />}

        {activeTab === 'data' && <DataExplorationPage />}
      </main>

      {/* App Configuration Modal */}
      <AppConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        onSave={handleSaveAppConfig}
        initialData={currentApp}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <p>AIOps Predictive System • Real-Time Azure Telemetry Forecasting Platform</p>
        <p className="mt-1">
          Decoupled Telemetry Layer with LightGBM 30-Minute Trajectory & Percentage Threshold Normalization.
        </p>
      </footer>
    </div>
  );
}
