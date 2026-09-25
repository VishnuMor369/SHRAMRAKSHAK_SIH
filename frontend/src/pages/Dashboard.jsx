import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import AlertDetailModal from '../components/AlertDetailModal';
import MobileAccessModal from '../components/MobileAccessModal';

// 8 Enterprise SIH Views
import OverviewView from '../components/views/OverviewView';
import ReportsView from '../components/views/ReportsView';
import SafetyIntelligenceView from '../components/views/SafetyIntelligenceView';
import SafetyMemoryView from '../components/views/SafetyMemoryView';
import LiveSafetyView from '../components/views/LiveSafetyView';
import ActionsVerificationView from '../components/views/ActionsVerificationView';
import ImportDataView from '../components/views/ImportDataView';
import SettingsDemoView from '../components/views/SettingsDemoView';

// Field / Supporting Modals & Views (Secondary)
import SafetyPassportView from '../components/SafetyPassportView';
import HSEObservationView from '../components/HSEObservationView';

export default function Dashboard({ stateData }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('OVERVIEW');
  const [isQrOpen, setIsQrOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);

  const status = stateData?.status;
  const activeAlert = status?.active_alert;
  const activeAlerts = status?.active_alerts || (activeAlert ? [activeAlert] : []);

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
      {/* 1. LEFT SIDEBAR (8 Enterprise Views) */}
      <Sidebar 
        isOpen={isSidebarOpen} 
        onClose={() => setIsSidebarOpen(false)}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        activeAlertsCount={activeAlerts.length}
      />

      {/* 2. MAIN APPLICATION CONTENT */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
        {/* TOP HEADER */}
        <Header 
          status={status} 
          onOpenQr={() => setIsQrOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          onOpenPassport={() => setActiveTab('Safety Passport')}
          onOpenSafetyAnalysis={() => setActiveTab('SAFETY INTELLIGENCE')}
        />

        {/* ENTERPRISE 8-VIEW ROUTING */}
        <main className="flex-1">
          {activeTab === 'OVERVIEW' || activeTab === 'Dashboard' ? (
            <OverviewView 
              status={status}
              onNavigate={(tab) => setActiveTab(tab)}
              onSelectAlert={handleSelectAlert}
            />
          ) : activeTab === 'REPORTS' ? (
            <ReportsView />
          ) : activeTab === 'SAFETY INTELLIGENCE' || activeTab === 'AI Risk Intelligence' || activeTab === 'AI Safety Analysis' ? (
            <SafetyIntelligenceView 
              onNavigate={(tab) => setActiveTab(tab)}
            />
          ) : activeTab === 'SAFETY MEMORY' ? (
            <SafetyMemoryView />
          ) : activeTab === 'LIVE SAFETY' || activeTab === 'Live Monitoring' ? (
            <LiveSafetyView 
              status={status}
              onSelectAlert={handleSelectAlert}
              onNavigate={(tab) => setActiveTab(tab)}
            />
          ) : activeTab === 'ACTIONS' || activeTab === 'ACTIONS / VERIFICATION' || activeTab === 'Alerts' ? (
            <ActionsVerificationView 
              status={status}
              onSelectAlert={handleSelectAlert}
            />
          ) : activeTab === 'IMPORT DATA' ? (
            <ImportDataView 
              onNavigate={(tab) => setActiveTab(tab)}
            />
          ) : activeTab === 'SETTINGS / DEMO' ? (
            <SettingsDemoView 
              onNavigate={(tab) => setActiveTab(tab)}
            />
          ) : activeTab === 'HSE Observation' ? (
            <HSEObservationView
              status={status}
              onClose={() => setActiveTab('OVERVIEW')}
              onSelectAlert={handleSelectAlert}
              onOpenAlerts={() => setActiveTab('ACTIONS')}
            />
          ) : activeTab === 'Safety Passport' ? (
            <SafetyPassportView 
              status={status} 
              onClose={() => setActiveTab('OVERVIEW')} 
            />
          ) : (
            <OverviewView 
              status={status}
              onNavigate={(tab) => setActiveTab(tab)}
              onSelectAlert={handleSelectAlert}
            />
          )}
        </main>

        {/* INDUSTRIAL ENTERPRISE FOOTER */}
        <footer className="bg-white border-t border-slate-200 py-3 mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
            <div>
              <span className="font-bold text-slate-800">SHRAMRAKSHAK</span> — AI/NLP SIF Intelligence System (SIH 2026 Problem SIH26165 • OIL India)
            </div>
            <div className="flex items-center space-x-3 text-[11px]">
              <span>Architecture: UNDERSTAND → REMEMBER → LEARN → PREVENT → VERIFY</span>
              <span className="text-slate-300">•</span>
              <span className="text-emerald-700 font-semibold">● Vision Node Online</span>
            </div>
          </div>
        </footer>
      </div>

      {/* MODAL 1: Mobile Supervisor Pairing QR Modal */}
      <MobileAccessModal
        isOpen={isQrOpen}
        onClose={() => setIsQrOpen(false)}
        lanIp={status?.lan_ip}
      />

      {/* MODAL 2: Alert Response & Verification Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        isOpen={isAlertModalOpen}
        onClose={handleCloseAlertModal}
        currentAlerts={activeAlerts}
      />
    </div>
  );
}
