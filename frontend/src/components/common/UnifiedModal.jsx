import React from 'react';
import OverlayPortal from './OverlayPortal';
import { useOverlayLock } from './useOverlayLock';

/**
 * UnifiedModal: Enterprise standard centered modal dialog.
 * Renders via React Portal at document root with a separate full-viewport backdrop,
 * body scroll lock, Escape key dismiss, and responsive sizing.
 */
export default function UnifiedModal({
  isOpen,
  onClose,
  children,
  maxWidthClass = 'max-w-2xl',
  className = ''
}) {
  useOverlayLock(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <OverlayPortal>
      {/* 1. SEPARATE FULL-VIEWPORT BACKDROP */}
      <div
        className="fixed inset-0 z-[60] bg-slate-950/50 backdrop-blur-[2px] animate-overlay-fade"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 2. CENTERED DIALOG WRAPPER WITH SCROLL SUPPORT */}
      <div 
        className="fixed inset-0 z-[70] flex items-center justify-center p-3 sm:p-4 md:p-6 overflow-y-auto"
        onClick={onClose}
      >
        <div
          className={`bg-white rounded-2xl shadow-2xl border border-slate-200 w-full overflow-hidden my-auto transition-all animate-modal-scale ${maxWidthClass} ${className}`}
          role="dialog"
          aria-modal="true"
          onClick={(e) => e.stopPropagation()}
        >
          {children}
        </div>
      </div>
    </OverlayPortal>
  );
}
