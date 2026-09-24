import React, { useState } from 'react';
import { Video, Maximize2, RefreshCw, Eye } from 'lucide-react';

export default function LiveCameraCard({ status, activeCamera = 'C-01', onOpenLiveMonitoring }) {
  const [streamKey, setStreamKey] = useState(Date.now());
  const [streamError, setStreamError] = useState(false);

  const personCount = status?.person_count ?? (status?.person_detected ? 1 : 0);
  const unhelmetedCount = status?.unhelmeted_count ?? (!status?.helmet_detected && personCount > 0 ? 1 : 0);
  const zoneViolation = status?.zone_violation ?? false;

  const handleRefresh = (e) => {
    e.stopPropagation();
    setStreamError(false);
    setStreamKey(Date.now());
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Video className="w-4 h-4 text-slate-700" />
          <h2 className="text-xs font-black tracking-wider text-slate-800 uppercase">
            Live Monitoring • Camera C-01 (Laptop Webcam)
          </h2>
        </div>

        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>LIVE</span>
          </span>
          <button
            onClick={handleRefresh}
            className="p-1 text-slate-400 hover:text-slate-600 rounded transition-colors"
            title="Refresh stream"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Video Feed Window */}
      <div className="relative rounded-lg overflow-hidden bg-slate-950 aspect-[4/3] max-h-64 mx-auto border border-slate-200 group flex items-center justify-center">
        {!streamError ? (
          <img
            key={`${activeCamera}-${streamKey}`}
            src={`/video_feed?camera=${activeCamera}&t=${streamKey}`}
            alt={`Live CCTV Stream ${activeCamera}`}
            className="w-full h-full object-contain"
            onError={() => setStreamError(true)}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center p-4 text-slate-400 space-y-2">
            <Eye className="w-8 h-8 text-slate-500" />
            <p className="text-xs font-bold text-slate-300">Live AI Feed Connecting</p>
            <button
              onClick={handleRefresh}
              className="text-[11px] font-bold text-amber-400 underline"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Real-time overlay bar at bottom of stream */}
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none">
          <div className="flex items-center space-x-1.5">
            <span className="bg-black/80 backdrop-blur-sm text-white px-2 py-0.5 rounded text-[10px] font-mono font-bold border border-white/10">
              {personCount} {personCount === 1 ? 'Worker' : 'Workers'}
            </span>
            {unhelmetedCount > 0 && (
              <span className="bg-amber-600/90 text-white px-2 py-0.5 rounded text-[10px] font-bold">
                {unhelmetedCount} No Helmet
              </span>
            )}
            {zoneViolation && (
              <span className="bg-red-600/90 text-white px-2 py-0.5 rounded text-[10px] font-bold animate-pulse">
                Zone Breach
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-slate-500 font-medium">
          Edge Model: ONNX PPE + YOLOv8
        </span>
        {onOpenLiveMonitoring && (
          <button
            onClick={onOpenLiveMonitoring}
            className="text-xs font-bold text-slate-900 hover:text-amber-600 flex items-center space-x-1 transition-colors"
          >
            <span>Full Live View</span>
            <span className="text-amber-500">→</span>
          </button>
        )}
      </div>
    </div>
  );
}
