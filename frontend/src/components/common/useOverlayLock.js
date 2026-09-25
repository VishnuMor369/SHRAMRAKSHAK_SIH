import { useEffect } from 'react';

let lockCount = 0;
let originalBodyOverflow = '';

/**
 * useOverlayLock:
 * - Locks document.body scroll while isOpen is true using reference counting.
 * - Adds Escape key listener to close overlay.
 */
export function useOverlayLock(isOpen, onClose) {
  useEffect(() => {
    if (!isOpen) return;

    if (lockCount === 0) {
      originalBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    }
    lockCount++;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      lockCount = Math.max(0, lockCount - 1);
      if (lockCount === 0) {
        document.body.style.overflow = originalBodyOverflow;
      }
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);
}
