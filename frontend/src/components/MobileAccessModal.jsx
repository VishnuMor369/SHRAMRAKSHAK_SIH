import React, { useState, useEffect } from 'react';
import { X, Smartphone, Wifi, Copy, Check, QrCode } from 'lucide-react';
import { fetchQrCode } from '../services/api';
import { UnifiedModal } from './common';

export default function MobileAccessModal({ isOpen, onClose, lanIp }) {
  const [qrBase64, setQrBase64] = useState(null);
  const [copied, setCopied] = useState(false);

  const supervisorUrl = lanIp 
    ? `http://${lanIp}:5173/supervisor` 
    : `${window.location.origin}/supervisor`;

  useEffect(() => {
    if (isOpen) {
      fetchQrCode(supervisorUrl)
        .then((data) => {
          if (data?.qr_base64) {
            setQrBase64(data.qr_base64);
          }
        })
        .catch((e) => console.warn('QR fetch error:', e));
    }
  }, [isOpen, supervisorUrl]);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(supervisorUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <UnifiedModal
      isOpen={isOpen}
      onClose={onClose}
      maxWidthClass="max-w-md"
    >
      {/* Modal Header */}
        <div className="bg-slate-900 text-white px-5 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Smartphone className="w-5 h-5 text-amber-400" />
            <h3 className="font-black text-sm tracking-wide">CONNECT MOBILE SUPERVISOR</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {/* QR Code Container */}
          <div className="flex flex-col items-center justify-center p-4 bg-slate-50 rounded-lg border border-slate-200">
            {qrBase64 ? (
              <img
                src={`data:image/png;base64,${qrBase64}`}
                alt="Scan to open supervisor mobile page"
                className="w-48 h-48 rounded shadow-sm border border-slate-300"
              />
            ) : (
              <div className="w-48 h-48 bg-slate-200 animate-pulse rounded flex items-center justify-center text-slate-400">
                <QrCode className="w-12 h-12" />
              </div>
            )}
            <p className="text-xs font-semibold text-slate-600 mt-2.5 flex items-center space-x-1.5">
              <span>Scan with phone camera app</span>
            </p>
          </div>

          {/* Direct URL Box */}
          <div className="mt-4">
            <label className="text-[11px] font-bold uppercase text-slate-500 tracking-wider block mb-1">
              Direct Mobile URL
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                readOnly
                value={supervisorUrl}
                className="w-full text-xs font-mono font-bold bg-slate-100 border border-slate-300 rounded px-3 py-2 text-slate-800 select-all"
              />
              <button
                onClick={handleCopy}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-medium flex items-center space-x-1 transition-colors whitespace-nowrap"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Quick Instructions */}
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 space-y-1.5">
            <div className="font-bold flex items-center space-x-1.5">
              <Wifi className="w-4 h-4 text-amber-600" />
              <span>How to open on phone:</span>
            </div>
            <ol className="list-decimal list-inside space-y-1 text-slate-700 pl-1">
              <li>Connect your smartphone to the same Wi-Fi network (or laptop mobile hotspot).</li>
              <li>Scan the QR code above or type the URL into your phone's browser.</li>
              <li>No app download required — runs instantly in mobile web browser.</li>
            </ol>
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            className="mt-5 w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-colors"
          >
            Done / Close
          </button>
        </div>
    </UnifiedModal>
  );
}
