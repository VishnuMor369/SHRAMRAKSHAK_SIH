import React from 'react';
import { Video, ShieldCheck, Wifi, Eye, CheckCircle2 } from 'lucide-react';

export default function CameraFeedsCard({ status, activeCamera = 'C-01', onSelectCamera }) {
  const cameraActive = status?.camera_active ?? true;

  const cameras = [
    {
      id: 'C-01',
      name: 'CAMERA C-01',
      location: 'Demo Work Zone (Laptop Webcam)',
      resolution: '640×480',
      badge: 'PHYSICAL WEBCAM',
      active: cameraActive,
      streamUrl: '/video_feed?camera=C-01'
    }
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Video className="w-4 h-4 text-slate-700" />
          <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">
            Site Surveillance Node
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
            1 / 1 Feed Active (C-01)
          </span>
        </div>
      </div>

      {/* Primary Camera C-01 */}
      <div className="grid grid-cols-1 gap-3">
        {cameras.map((cam) => {
          const isSelected = (activeCamera === cam.id);
          return (
            <div
              key={cam.id}
              onClick={() => onSelectCamera && onSelectCamera(cam.id)}
              className={`border rounded-lg p-2.5 transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'border-amber-500 bg-amber-50/40 ring-2 ring-amber-400/30 shadow-sm'
                  : 'border-slate-200 bg-slate-50/50 hover:bg-slate-100/80 hover:border-slate-300'
              }`}
            >
              {/* Snapshot Thumbnail */}
              <div className="w-full h-24 bg-slate-950 rounded border border-slate-300 overflow-hidden relative shrink-0 flex items-center justify-center mb-2">
                {cam.active ? (
                  <img
                    src={cam.streamUrl}
                    alt={`${cam.name} Thumbnail`}
                    className="w-full h-full object-cover select-none pointer-events-none"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                ) : (
                  <span className="text-[9px] text-slate-500 font-mono">OFFLINE</span>
                )}
                
                {/* Live Dot */}
                <div className="absolute top-1.5 left-1.5 flex items-center space-x-1 bg-black/70 backdrop-blur-xs px-1.5 py-0.5 rounded">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 block animate-pulse"></span>
                  <span className="text-[9px] font-mono font-bold text-emerald-400">LIVE</span>
                </div>

                {/* Selected Indicator */}
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 bg-amber-500 text-slate-950 px-1.5 py-0.5 rounded text-[9px] font-black tracking-wide flex items-center space-x-0.5">
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    <span>PRIMARY</span>
                  </div>
                )}
              </div>

              {/* Camera Info */}
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-slate-900">
                    {cam.name}
                  </span>
                  <span className="text-[9px] font-bold text-slate-600 bg-slate-200/80 px-1 py-0.5 rounded">
                    {cam.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 truncate font-medium mt-0.5" title={cam.location}>
                  {cam.location}
                </p>
                <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-slate-200/70 text-[10px] text-slate-400 font-mono">
                  <span>{cam.resolution}</span>
                  <span className="text-emerald-700 font-bold bg-emerald-100/70 px-1 rounded">AI Armed</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
