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

export async function sendCameraFrame(frameBase64, cameraId = 'C-01') {
  const res = await fetch(`${API_BASE}/api/cv/frame`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame: frameBase64, camera_id: cameraId })
  });
  if (!res.ok) throw new Error('Failed to process camera frame');
  return res.json();
}

export async function fetchCvDebug() {
  const res = await fetch(`${API_BASE}/api/cv/debug`);
  if (!res.ok) throw new Error('Failed to fetch CV debug info');
  return res.json();
}

