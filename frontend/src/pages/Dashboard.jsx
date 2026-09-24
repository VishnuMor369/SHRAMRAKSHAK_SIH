import React, { useState } from 'react';
import { Shield, BrainCircuit, QrCode, Zap, ArrowLeft, FileText } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import SummaryCards from '../components/SummaryCards';
import SafetyPassportGlanceCard from '../components/SafetyPassportGlanceCard';
import AlertPanel from '../components/AlertPanel';
import SafetyOverviewCard from '../components/SafetyOverviewCard';
import LiveCameraCard from '../components/LiveCameraCard';
import CCTVPanel from '../components/CCTVPanel';
import ZoneStatusCard from '../components/ZoneStatusCard';
import RecentEventsCard from '../components/RecentEventsCard';
import AlertDetailModal from '../components/AlertDetailModal';
import DemoControls from '../components/DemoControls';
import MobileAccessModal from '../components/MobileAccessModal';
import SafetyPassportView from '../components/SafetyPassportView';
import AISafetyAnalysisView from '../components/AISafetyAnalysisView';
import HSEObservationView from '../components/HSEObservationView';

export default function Dashboard({ stateData }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [isQrOpen, setIsQrOpen] = useState(false);
  const [isDrawingZone, setIsDrawingZone] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState('C-01');

  const status = stateData?.status;
  const activeAlert = status?.active_alert;
  const activeAlerts = status?.active_alerts || (activeAlert ? [activeAlert] : []);
  const hasActivePassport = !!(status?.active_passport && status.active_passport.status === 'ACTIVE');

  const handleSelectAlert = (alert) => {
    setSelectedAlert(alert);
    setIsAlertModalOpen(true);
  };

  const handleCloseAlertModal = () => {
    setIsAlertModalOpen(false);
    setSelectedAlert(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex text-slate-900 font-sans">
      {/* 1. LEFT SIDEBAR */}
      <Sidebar 
        isOpen={isSidebarOpen} 
        onClose={() => setIsSidebarOpen(false)}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        activeAlertsCount={activeAlerts.length}
        hasActivePassport={hasActivePassport}
      />

      {/* 2. MAIN APPLICATION CONTENT */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
        {/* TOP HEADER */}
        <Header 
          status={status} 
          onOpenQr={() => setIsQrOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          onOpenPassport={() => setActiveTab('Safety Passport')}
          onOpenSafetyAnalysis={() => setActiveTab('AI Risk Intelligence')}
        />

        {/* VIEW ROUTING */}
        {activeTab === 'HSE Observation' ? (
          <HSEObservationView
            status={status}
            onClose={() => setActiveTab('Dashboard')}
            onSelectAlert={handleSelectAlert}
            onOpenAlerts={() => setActiveTab('Alerts')}
          />
        ) : activeTab === 'Safety Passport' ? (
          <SafetyPassportView 
            status={status} 
            onClose={() => setActiveTab('Dashboard')} 
          />
        ) : activeTab === 'AI Risk Intelligence' || activeTab === 'AI Safety Analysis' || activeTab === 'AI Reports' ? (
          <AISafetyAnalysisView
            status={status}
            onClose={() => setActiveTab('Dashboard')}
          />
        ) : activeTab === 'Live Monitoring' ? (
          /* DEDICATED FULL LIVE MONITORING VIEW */
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setActiveTab('Dashboard')}
                className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Dashboard</span>
              </button>
              <h1 className="text-sm font-black text-slate-900 uppercase tracking-wider">
                Live Camera Surveillance • Camera C-01 (Laptop Webcam)
              </h1>
            </div>
            <CCTVPanel 
              status={status} 
              isDrawingMode={isDrawingZone} 
              setIsDrawingMode={setIsDrawingZone} 
              selectedCamera={selectedCamera}
              onSelectCamera={setSelectedCamera}
              onSelectAlert={handleSelectAlert}
            />
          </main>
        ) : activeTab === 'Alerts' ? (
          /* DEDICATED ALERTS & AUDIT LOG VIEW */
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setActiveTab('Dashboard')}
                className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Dashboard</span>
              </button>
              <h1 className="text-sm font-black text-slate-900 uppercase tracking-wider">
                Safety Alerts Management & Audit History
              </h1>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              <div className="lg:col-span-7 space-y-4">
                <AlertPanel 
                  alert={activeAlert} 
                  alerts={activeAlerts} 
                  onSelectAlert={handleSelectAlert} 
                />
              </div>
              <div className="lg:col-span-5 space-y-4">
                <RecentEventsCard activeAlerts={activeAlerts} />
              </div>
            </div>
          </main>
        ) : activeTab === 'Locations / Zones' ? (
          /* DEDICATED LOCATIONS & SAFETY ZONES VIEW */
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setActiveTab('Dashboard')}
                className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Dashboard</span>
              </button>
              <h1 className="text-sm font-black text-slate-900 uppercase tracking-wider">
                Safety Exclusion Zones & Boundary Configuration
              </h1>
            </div>
            <ZoneStatusCard 
              status={status} 
              onDefineZone={() => {
                setActiveTab('Live Monitoring');
                setIsDrawingZone(true);
              }} 
            />
            <CCTVPanel 
              status={status} 
              isDrawingMode={isDrawingZone} 
              setIsDrawingMode={setIsDrawingZone} 
              selectedCamera={selectedCamera}
              onSelectCamera={setSelectedCamera}
              onSelectAlert={handleSelectAlert}
            />
          </main>
        ) : (
          /* ======================================================= */
          /* MAIN STREAMLINED DASHBOARD (Clean HSE Command Center)  */
          /* ======================================================= */
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
            {/* 1. TOP KPI CARDS (4 Balanced Indicators) */}
            <SummaryCards status={status} alerts={activeAlerts} />

            {/* 2. COMPACT SAFETY PASSPORT STATUS CARD */}
            <SafetyPassportGlanceCard 
              status={status} 
              onOpenPassport={() => setActiveTab('Safety Passport')} 
              onCreatePassport={() => setActiveTab('Safety Passport')} 
            />

            {/* 3. PRIMARY DASHBOARD 2-COLUMN LAYOUT */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              {/* LEFT / PRIMARY COLUMN (7 cols on desktop): ACTIVE ALERTS + SAFETY OVERVIEW */}
              <div className="lg:col-span-7 space-y-5 w-full">
                {/* ACTIVE ALERTS (Primary Focus) */}
                <AlertPanel 
                  alert={activeAlert} 
                  alerts={activeAlerts} 
                  onSelectAlert={handleSelectAlert}
                  onViewAll={() => setActiveTab('Alerts')}
                />

                {/* SAFETY OVERVIEW (3 Lightweight Insight Cards) */}
                <SafetyOverviewCard 
                  status={status} 
                  alerts={activeAlerts} 
                />
              </div>

              {/* RIGHT COLUMN (5 cols on desktop): LIVE MONITOR PREVIEW + QUICK ACTIONS */}
              <div className="lg:col-span-5 space-y-4 w-full">
                {/* Focused Live Camera Monitor Preview */}
                <LiveCameraCard 
                  status={status} 
                  activeCamera={selectedCamera}
                  onOpenLiveMonitoring={() => setActiveTab('Live Monitoring')} 
                />

                {/* Quick Actions Card */}
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
                  <div className="flex items-center space-x-2">
                    <Zap className="w-4 h-4 text-amber-500" />
                    <h3 className="text-xs font-black tracking-wider text-slate-800 uppercase">
                      Quick Actions
                    </h3>
                  </div>
                  <div className="space-y-2">
                    <button
                      onClick={() => setActiveTab('HSE Observation')}
                      className="w-full flex items-center justify-between p-2.5 rounded-lg bg-blue-50 hover:bg-blue-100 border border-blue-200 text-xs font-bold text-blue-900 transition-colors group"
                    >
                      <div className="flex items-center space-x-2.5">
                        <FileText className="w-4 h-4 text-blue-600" />
                        <span>Record HSE Field Observation</span>
                      </div>
                      <span className="text-blue-400 group-hover:text-blue-700 transition-colors">→</span>
                    </button>

                    <button
                      onClick={() => setActiveTab('Safety Passport')}
                      className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-800 transition-colors group"
                    >
                      <div className="flex items-center space-x-2.5">
                        <Shield className="w-4 h-4 text-slate-600" />
                        <span>Create Safety Passport</span>
                      </div>
                      <span className="text-slate-400 group-hover:text-amber-600 transition-colors">→</span>
                    </button>

                    <button
                      onClick={() => setActiveTab('AI Safety Analysis')}
                      className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-800 transition-colors group"
                    >
                      <div className="flex items-center space-x-2.5">
                        <BrainCircuit className="w-4 h-4 text-purple-600" />
                        <span>AI Safety Analysis (NLP)</span>
                      </div>
                      <span className="text-slate-400 group-hover:text-amber-600 transition-colors">→</span>
                    </button>

                    <button
                      onClick={() => setIsQrOpen(true)}
                      className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-800 transition-colors group"
                    >
                      <div className="flex items-center space-x-2.5">
                        <QrCode className="w-4 h-4 text-emerald-600" />
                        <span>Pair Mobile Supervisor</span>
                      </div>
                      <span className="text-slate-400 group-hover:text-amber-600 transition-colors">→</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* 4. PRESENTATION DEMO & FAILSAFE CONTROLS (At bottom) */}
            <div className="pt-2">
              <DemoControls />
            </div>
          </main>
        )}

        {/* INDUSTRIAL FOOTER */}
        <footer className="bg-white border-t border-slate-200 py-3 mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
            <div>
              <span className="font-bold text-slate-800">SHRAMRAKSHAK</span> — AI-Powered SIF Intelligence for Safer Workplaces
            </div>
            <div className="flex items-center space-x-3 text-[11px]">
              <span>SIH Statement ID 26165</span>
              <span className="text-slate-300">•</span>
              <span className="text-emerald-700 font-semibold">● Vision Node Online</span>
            </div>
          </div>
        </footer>
      </div>

      {/* MODAL 1: Mobile Supervisor Pairing Modal */}
      <MobileAccessModal
        isOpen={isQrOpen}
        onClose={() => setIsQrOpen(false)}
        lanIp={status?.lan_ip}
      />

      {/* MODAL 2: Alert Response & Resolution Workflow Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        isOpen={isAlertModalOpen}
        onClose={handleCloseAlertModal}
        currentAlerts={activeAlerts}
      />
    </div>
  );
}
