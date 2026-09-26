import { useState, useEffect, useRef } from 'react';
import { playAlertChime, playSuccessChime, playEscalationChime } from './sound';

// Base API URL configuration
const API_BASE = '';

export async function fetchStatus() {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchQrCode(customUrl = null) {
  const query = customUrl ? `?url=${encodeURIComponent(customUrl)}` : '';
  const res = await fetch(`${API_BASE}/api/qr${query}`);
  if (!res.ok) throw new Error('Failed to fetch QR code');
  return res.json();
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/api/alerts`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
}

export async function fetchAlertById(alertId) {
  const res = await fetch(`${API_BASE}/api/alerts/${alertId}`);
  if (!res.ok) throw new Error('Failed to fetch alert details');
  return res.json();
}

export async function fetchAlertHistory() {
  const res = await fetch(`${API_BASE}/api/alerts/history`);
  if (!res.ok) throw new Error('Failed to fetch alert history');
  return res.json();
}

export async function respondToAlert(supervisorId = 'SUP-01', notes = '', alertId = null) {
  const endpoint = alertId ? `${API_BASE}/api/alerts/${alertId}/respond` : `${API_BASE}/api/alert/respond`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supervisor_id: supervisorId, notes, alert_id: alertId }),
  });
  if (!res.ok) throw new Error('Failed to respond to alert');
  return res.json();
}

export async function resolveAlert(supervisorId = 'SUP-01', notes = '', alertId = null) {
  const endpoint = alertId ? `${API_BASE}/api/alerts/${alertId}/resolve` : `${API_BASE}/api/alert/resolve`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supervisor_id: supervisorId, notes, alert_id: alertId }),
  });
  if (!res.ok) throw new Error('Failed to resolve alert');
  return res.json();
}

export async function markActionTaken(supervisorId = 'SUP-01', notes = '', actionTaken = '', alertId = null) {
  const endpoint = alertId ? `${API_BASE}/api/alerts/${alertId}/action` : `${API_BASE}/api/alert/action`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supervisor_id: supervisorId, notes, action_taken: actionTaken, alert_id: alertId }),
  });
  if (!res.ok) throw new Error('Failed to mark action taken');
  return res.json();
}

export async function verifyAlert(supervisorId = 'SUP-01', decision = 'VERIFIED', verificationMethod = 'CCTV_VERIFIED', notes = '', alertId = null) {
  const endpoint = alertId ? `${API_BASE}/api/alerts/${alertId}/verify` : `${API_BASE}/api/alert/verify`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supervisor_id: supervisorId, decision, verification_method: verificationMethod, notes, alert_id: alertId }),
  });
  if (!res.ok) throw new Error('Failed to record alert verification');
  return res.json();
}

export async function addHSEObservation(alertId, data) {
  const res = await fetch(`${API_BASE}/api/alerts/${alertId}/hse-observation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit HSE observation');
  }
  return res.json();
}

export async function createHSEObservation(data) {
  const endpoint = data.linked_alert_id 
    ? `${API_BASE}/api/alerts/${data.linked_alert_id}/hse-observation` 
    : `${API_BASE}/api/alerts/hse-observation`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit HSE observation');
  }
  return res.json();
}

export async function resetDemo() {
  const res = await fetch(`${API_BASE}/api/demo/reset`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to reset demo');
  return res.json();
}

export async function simulateNoHelmet() {
  const res = await fetch(`${API_BASE}/api/demo/simulate-no-helmet`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to simulate no-helmet');
  return res.json();
}

export async function simulateSafe() {
  const res = await fetch(`${API_BASE}/api/demo/simulate-safe`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to simulate safe');
  return res.json();
}

export async function simulateZoneEntry() {
  const res = await fetch(`${API_BASE}/api/demo/simulate-zone-entry`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to simulate zone entry');
  return res.json();
}

export async function simulateMultiViolation() {
  const res = await fetch(`${API_BASE}/api/demo/simulate-multi-violation`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to simulate multi-violation');
  return res.json();
}

export async function fetchZone() {
  const res = await fetch(`${API_BASE}/api/zones`);
  if (!res.ok) throw new Error('Failed to fetch zones');
  return res.json();
}

export async function saveZone(zoneData) {
  const res = await fetch(`${API_BASE}/api/zones`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(zoneData),
  });
  if (!res.ok) throw new Error('Failed to save zone');
  return res.json();
}

export async function deleteZone(zoneId = 'ZONE-001') {
  const encId = encodeURIComponent(zoneId || 'ZONE-001');
  let res = await fetch(`${API_BASE}/api/zones/${encId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    res = await fetch(`${API_BASE}/api/zones/${encId}/delete`, {
      method: 'POST',
    });
  }
  if (!res.ok) throw new Error('Failed to delete zone');
  return res.json();
}

export async function toggleZone(zoneId = 'ZONE-001') {
  const encId = encodeURIComponent(zoneId || 'ZONE-001');
  let res = await fetch(`${API_BASE}/api/zones/${encId}/toggle`, {
    method: 'PATCH',
  });
  if (!res.ok) {
    res = await fetch(`${API_BASE}/api/zones/${encId}/toggle`, {
      method: 'POST',
    });
  }
  if (!res.ok) throw new Error('Failed to toggle zone');
  return res.json();
}

export async function restoreDefaultZone() {
  const res = await fetch(`${API_BASE}/api/zones/restore-default`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to restore default zone');
  return res.json();
}

// ==========================================
// SAFETY PASSPORT API CLIENTS
// ==========================================

export async function fetchPassports() {
  const res = await fetch(`${API_BASE}/api/passports`);
  if (!res.ok) throw new Error('Failed to fetch safety passports');
  return res.json();
}

export async function fetchActivePassport() {
  const res = await fetch(`${API_BASE}/api/passports/active`);
  if (!res.ok) throw new Error('Failed to fetch active passport');
  return res.json();
}

export async function createPassport(data) {
  const res = await fetch(`${API_BASE}/api/passports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create passport' }));
    throw new Error(err.detail || 'Failed to create passport');
  }
  return res.json();
}

export async function verifyPassportControl(passportId, controlId, verified = true, verifiedBy = 'Demo Supervisor', notes = '', role = 'supervisor') {
  const res = await fetch(`${API_BASE}/api/passports/${passportId}/verify-control`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-User-Role': role,
    },
    body: JSON.stringify({ control_id: controlId, verified, verified_by: verifiedBy, notes, user_role: role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to verify control' }));
    throw new Error(err.detail || 'Failed to verify control');
  }
  return res.json();
}

export async function approvePassport(passportId, approvedBy = 'HSE Manager', notes = '', role = 'hse') {
  const res = await fetch(`${API_BASE}/api/passports/${passportId}/approve`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-User-Role': role,
    },
    body: JSON.stringify({ approved_by: approvedBy, notes, user_role: role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to approve passport' }));
    throw new Error(err.detail || 'Failed to approve passport');
  }
  return res.json();
}

export async function activatePassport(passportId, role = 'hse') {
  const res = await fetch(`${API_BASE}/api/passports/${passportId}/activate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': role,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to activate passport' }));
    throw new Error(err.detail || 'Failed to activate passport');
  }
  return res.json();
}

export async function verifyBarrierRestored(passportId, supervisorId = 'Demo Supervisor', notes = '', role = 'supervisor') {
  const res = await fetch(`${API_BASE}/api/passports/${passportId}/verify-restoration`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-User-Role': role,
    },
    body: JSON.stringify({ supervisor_id: supervisorId, notes, user_role: role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to verify restoration' }));
    throw new Error(err.detail || 'Failed to verify restoration');
  }
  return res.json();
}

export async function closePassport(passportId) {
  const res = await fetch(`${API_BASE}/api/passports/${passportId}/close`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to close passport' }));
    throw new Error(err.detail || 'Failed to close passport');
  }
  return res.json();
}

// ==========================================
// AI + NLP SAFETY ANALYSIS API CLIENTS (SIH PS 26165)
// ==========================================

export async function fetchGeneratedReports() {
  const res = await fetch(`${API_BASE}/api/reports/generated`);
  if (!res.ok) throw new Error('Failed to fetch generated safety reports');
  return res.json();
}

export async function fetchReportById(reportId) {
  const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
  if (!res.ok) throw new Error('Failed to fetch safety report details');
  return res.json();
}

export async function analyzeReport(reportId) {
  const res = await fetch(`${API_BASE}/api/reports/${reportId}/analyze`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to analyze safety report');
  return res.json();
}

export async function fetchAnalysisSummary() {
  const res = await fetch(`${API_BASE}/api/reports/analysis/summary`);
  if (!res.ok) throw new Error('Failed to fetch safety analysis summary');
  return res.json();
}

export async function fetchRecurringPatterns() {
  const res = await fetch(`${API_BASE}/api/reports/analysis/patterns`);
  if (!res.ok) throw new Error('Failed to fetch recurring patterns');
  return res.json();
}


export function getExportPdfUrl() {
  return `${API_BASE}/api/reports/export-pdf`;
}

export async function downloadExportPdf() {
  const res = await fetch(`${API_BASE}/api/reports/export-pdf`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to download HSE report' }));
    throw new Error(errorData.detail || 'Failed to download HSE report');
  }
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition');
  let filename = 'SHRAMRAKSHAK_HSE_Intelligence_Report.pdf';
  if (disposition && disposition.includes('filename=')) {
    filename = disposition.split('filename=')[1].replace(/"/g, '').replace(/;/g, '').trim();
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}


export function getSingleReportPdfUrl(reportId) {
  return `${API_BASE}/api/reports/${reportId}/export-pdf`;
}

export async function submitHSEReview(reportId, reviewPayload) {
  const res = await fetch(`${API_BASE}/api/reports/${reportId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reviewPayload)
  });
  if (!res.ok) throw new Error('Failed to submit HSE review');
  return res.json();
}

export async function fetchValidationSummary() {
  const res = await fetch(`${API_BASE}/api/reports/validation/summary`);
  if (!res.ok) throw new Error('Failed to fetch validation summary');
  return res.json();
}

export async function analyzeRawText(text, context = {}) {
  const res = await fetch(`${API_BASE}/api/reports/analyze-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, context })
  });
  if (!res.ok) throw new Error('Failed to analyze raw incident text');
  return res.json();
}

// ==========================================
// REAL DATASET SIF ANALYTICS API CLIENTS (SIH PS 26165)
// ==========================================

export async function uploadDatasetCsv(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/api/dataset/upload`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to upload CSV file' }));
    throw new Error(err.detail || 'Failed to upload CSV file');
  }
  return res.json();
}

export async function startDatasetProcessing(maxRows = 2000) {
  const res = await fetch(`${API_BASE}/api/dataset/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max_rows: maxRows })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start dataset SIF analysis' }));
    throw new Error(err.detail || 'Failed to start dataset SIF analysis');
  }
  return res.json();
}

export async function fetchDatasetStatus() {
  const res = await fetch(`${API_BASE}/api/dataset/status`);
  if (!res.ok) throw new Error('Failed to fetch dataset status');
  return res.json();
}

export async function fetchDatasetSummary() {
  const res = await fetch(`${API_BASE}/api/dataset/summary`);
  if (!res.ok) throw new Error('Failed to fetch dataset HSE summary report');
  return res.json();
}

export async function fetchDatasetReports(params = {}) {
  const query = new URLSearchParams();
  if (params.status_filter) query.append('status_filter', params.status_filter);
  if (params.source_filter) query.append('source_filter', params.source_filter);
  if (params.lsr_filter) query.append('lsr_filter', params.lsr_filter);
  if (params.precursor_filter) query.append('precursor_filter', params.precursor_filter);
  if (params.site_filter) query.append('site_filter', params.site_filter);
  if (params.activity_filter) query.append('activity_filter', params.activity_filter);
  if (params.search) query.append('search', params.search);
  if (params.page) query.append('page', params.page);
  if (params.page_size) query.append('page_size', params.page_size);

  const res = await fetch(`${API_BASE}/api/dataset/reports?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch dataset reports');
  return res.json();
}

export async function fetchDatasetReportById(reportId) {
  const res = await fetch(`${API_BASE}/api/dataset/report/${reportId}`);
  if (!res.ok) throw new Error('Failed to fetch dataset report detail');
  return res.json();
}

export async function loadSampleDataset(maxRows = 1500) {
  const res = await fetch(`${API_BASE}/api/dataset/sample?max_rows=${maxRows}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to load sample preset dataset' }));
    throw new Error(err.detail || 'Failed to load sample preset dataset');
  }
  return res.json();
}

/**
 * Custom React Hook for Real-time Synchronization
 * Uses WebSocket with automatic reconnection and fallback polling
 */
export function useRealtimeState() {
  const [status, setStatus] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const prevAlertStatusRef = useRef(null);

  useEffect(() => {
    let ws = null;
    let pollInterval = null;
    let reconnectTimeout = null;
    let isUnmounted = false;

    // Helper to process state updates and trigger audio alerts
    const handleStateUpdate = (newStatus) => {
      if (!newStatus) return;
      const currentAlertStatus = newStatus.active_alert?.status || 'IDLE';
      const prevAlertStatus = prevAlertStatusRef.current;

      // Check transitions for audio effects
      if (prevAlertStatus !== currentAlertStatus) {
        if (currentAlertStatus === 'WAITING_FOR_RESPONSE') {
          playAlertChime();
        } else if (currentAlertStatus === 'RESOLVED') {
          playSuccessChime();
        } else if (currentAlertStatus === 'ESCALATED') {
          playEscalationChime();
        }
        prevAlertStatusRef.current = currentAlertStatus;
      }

      setStatus(newStatus);
    };

    // Initial REST fetch to populate data immediately
    fetchStatus()
      .then((data) => {
        if (!isUnmounted) {
          handleStateUpdate(data);
        }
      })
      .catch((err) => console.warn('Initial status fetch failed:', err));

    // Connect WebSocket
    const connectWs = () => {
      if (isUnmounted) return;
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // If loaded via dev server (port 5173), proxy route is /ws
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!isUnmounted) setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.system_status) {
              handleStateUpdate(data);
            }
          } catch (e) {
            // non-json ping/pong
          }
        };

        ws.onclose = () => {
          if (!isUnmounted) {
            setIsConnected(false);
            reconnectTimeout = setTimeout(connectWs, 2000);
          }
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (err) {
        reconnectTimeout = setTimeout(connectWs, 2000);
      }
    };

    connectWs();

    // Fallback polling every 1.5s in case WebSocket is blocked by network/firewall
    pollInterval = setInterval(() => {
      fetchStatus()
        .then((data) => {
          if (!isUnmounted) handleStateUpdate(data);
        })
        .catch(() => {});
    }, 1500);

    return () => {
      isUnmounted = true;
      if (ws) ws.close();
      if (pollInterval) clearInterval(pollInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  return { status, isConnected };
}

export async function sendCameraFrame(frameBase64, cameraId = 'C-01', frameSeq = 0) {
  const res = await fetch(`${API_BASE}/api/cv/frame`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame: frameBase64, camera_id: cameraId, frame_seq: frameSeq })
  });
  if (!res.ok) throw new Error('Failed to process camera frame');
  return res.json();
}

export async function resetCvSession() {
  const res = await fetch(`${API_BASE}/api/cv/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to reset CV session');
  return res.json();
}

export async function fetchCvDebug() {
  const res = await fetch(`${API_BASE}/api/cv/debug`);
  if (!res.ok) throw new Error('Failed to fetch CV debug info');
  return res.json();
}

// ============================================================
// ENTERPRISE SIH 2026: SAFETY MEMORY, VERIFICATION & CORROBORATION
// ============================================================

export async function verifyCctvCondition(alertId, simulateRebreach = false, supervisorId = 'SUP-01') {
  const res = await fetch(`${API_BASE}/api/alert/cctv-verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      alert_id: alertId,
      simulate_rebreach: simulateRebreach,
      supervisor_id: supervisorId
    })
  });
  if (!res.ok) throw new Error('Failed to run CCTV verification');
  return res.json();
}

export async function fetchSafetyMemorySummary() {
  const res = await fetch(`${API_BASE}/api/safety-memory/summary`);
  if (!res.ok) throw new Error('Failed to fetch Safety Memory summary');
  return res.json();
}

export async function fetchSafetyMemoryPatterns() {
  const res = await fetch(`${API_BASE}/api/safety-memory/patterns`);
  if (!res.ok) throw new Error('Failed to fetch Safety Memory recurring patterns');
  return res.json();
}

export async function fetchPatternDetails(patternId) {
  const res = await fetch(`${API_BASE}/api/safety-memory/patterns/${patternId}`);
  if (!res.ok) throw new Error(`Failed to fetch details for pattern ${patternId}`);
  return res.json();
}

export async function assignPatternAction(patternId, actionData) {
  const res = await fetch(`${API_BASE}/api/safety-memory/patterns/${patternId}/assign-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(actionData)
  });
  if (!res.ok) throw new Error(`Failed to assign corrective action for pattern ${patternId}`);
  return res.json();
}

export async function closeSafetyPattern(patternId, closureData = {}) {
  const res = await fetch(`${API_BASE}/api/safety-memory/patterns/${patternId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(closureData)
  });
  if (!res.ok) throw new Error(`Failed to close safety pattern ${patternId}`);
  return res.json();
}

export async function validateSafetyMemoryPattern(patternId, decision = 'CONFIRM', reviewer = 'HSE-Lead-01', notes = '') {
  const res = await fetch(`${API_BASE}/api/safety-memory/validate-pattern`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pattern_id: patternId,
      decision,
      reviewer,
      notes
    })
  });
  if (!res.ok) throw new Error('Failed to validate safety memory pattern');
  return res.json();
}

export async function checkWorkPackage(packageData) {
  const res = await fetch(`${API_BASE}/api/safety-memory/check-work-package`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(packageData)
  });
  if (!res.ok) throw new Error('Failed to check work package safety requirements');
  return res.json();
}

export async function fetchCorroborationScenarios() {
  const res = await fetch(`${API_BASE}/api/corroboration/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch corroboration scenarios');
  return res.json();
}

export async function evaluateCorroboration(payload) {
  const res = await fetch(`${API_BASE}/api/corroboration/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to evaluate corroboration');
  return res.json();
}

export async function executeDemoPhase(phaseNum, payload = {}) {
  const res = await fetch(`${API_BASE}/api/demo/phase/${phaseNum}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to execute demo phase ${phaseNum}`);
  return res.json();
}

export async function resetEnterpriseDemo() {
  const res = await fetch(`${API_BASE}/api/demo/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to reset enterprise demo');
  return res.json();
}

// ============================================================
// UNIFIED SAFETY EVENT & DATASET IMPORT API
// ============================================================

export async function submitHumanReport(payload) {
  const res = await fetch(`${API_BASE}/api/events/human`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit human safety report');
  }
  return res.json();
}

export async function fetchUnifiedEvents(params = {}) {
  const query = new URLSearchParams();
  if (params.source) query.set('source', params.source);
  if (params.sif_potential) query.set('sif_potential', params.sif_potential);
  if (params.limit) query.set('limit', params.limit);
  if (params.offset) query.set('offset', params.offset);
  const qStr = query.toString();
  const url = `${API_BASE}/api/events${qStr ? '?' + qStr : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch unified safety events');
  return res.json();
}

export async function fetchUnifiedEventById(eventId) {
  const res = await fetch(`${API_BASE}/api/events/${eventId}`);
  if (!res.ok) throw new Error('Failed to fetch safety event details');
  return res.json();
}

export async function fetchUnifiedEventSummary() {
  const res = await fetch(`${API_BASE}/api/events/stats/summary`);
  if (!res.ok) throw new Error('Failed to fetch unified event summary');
  return res.json();
}

export async function updateEventAction(eventId, supervisorId = 'SUP-01', notes = '') {
  const res = await fetch(`${API_BASE}/api/events/${eventId}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supervisor_id: supervisorId, notes })
  });
  if (!res.ok) throw new Error('Failed to update event action');
  return res.json();
}

export async function verifyEventCondition(eventId, simulateRebreach = false, supervisorId = 'SUP-01', notes = '') {
  const res = await fetch(`${API_BASE}/api/events/${eventId}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      simulate_rebreach: simulateRebreach,
      supervisor_id: supervisorId,
      notes
    })
  });
  if (!res.ok) throw new Error('Failed to verify event condition');
  return res.json();
}

export async function uploadDatasetFile(formData) {
  const res = await fetch(`${API_BASE}/api/dataset/import-file`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload dataset file');
  }
  return res.json();
}

export async function executeDatasetImport(maxRows = 1000) {
  const res = await fetch(`${API_BASE}/api/dataset/import-execute?max_rows=${maxRows}`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to execute dataset import');
  }
  return res.json();
}

export async function fetchDatasetImportStatus() {
  const res = await fetch(`${API_BASE}/api/dataset/import-status`);
  if (!res.ok) throw new Error('Failed to fetch dataset import status');
  return res.json();
}


