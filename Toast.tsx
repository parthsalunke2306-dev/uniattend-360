import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastOptions {
  id?: string;
  title: string;
  subtitle?: string;
  type?: ToastType;
  duration?: number;
}

interface ToastContextValue {
  toast: {
    success: (title: string, subtitle?: string) => void;
    error: (title: string, subtitle?: string) => void;
    warning: (title: string, subtitle?: string) => void;
    info: (title: string, subtitle?: string) => void;
    show: (options: ToastOptions) => void;
  };
}

const ToastContext = createContext<ToastContextValue | null>(null);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastOptions[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    ({ title, subtitle, type = 'info', duration = 2800 }: ToastOptions) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastOptions = { id, title, subtitle, type, duration };

      setToasts((prev) => [...prev.slice(-3), newToast]);

      setTimeout(() => {
        removeToast(id);
      }, duration);
    },
    [removeToast]
  );

  const toast = {
    success: (title: string, subtitle?: string) => show({ title, subtitle, type: 'success' }),
    error: (title: string, subtitle?: string) => show({ title, subtitle, type: 'error' }),
    warning: (title: string, subtitle?: string) => show({ title, subtitle, type: 'warning' }),
    info: (title: string, subtitle?: string) => show({ title, subtitle, type: 'info' }),
    show,
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Floating Organic Toast Stack Container */}
      <div className="fixed top-4 right-4 sm:top-5 sm:right-5 z-[99999] flex flex-col space-y-2 pointer-events-none max-w-sm w-full">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto flex items-center justify-between p-3.5 rounded-2xl bg-white/95 border border-[#E8E3DA] backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.08)] text-xs font-sans transition-all duration-300 transform translate-y-0 opacity-100"
          >
            <div className="flex items-center space-x-3 min-w-0">
              <div className="shrink-0">
                {t.type === 'success' && (
                  <div className="p-1.5 rounded-xl bg-[#EAF2EB] text-[#2F5238] border border-[#D5E4D8]">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                )}
                {t.type === 'error' && (
                  <div className="p-1.5 rounded-xl bg-[#FCE4DA] text-[#8D3F30] border border-[#F5C7B6]">
                    <AlertCircle className="w-4 h-4" />
                  </div>
                )}
                {t.type === 'warning' && (
                  <div className="p-1.5 rounded-xl bg-[#FEF3DD] text-[#C28222] border border-[#F9E2B5]">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                )}
                {t.type === 'info' && (
                  <div className="p-1.5 rounded-xl bg-[#F4F0E8] text-[#5A655C] border border-[#E8E3DA]">
                    <Info className="w-4 h-4" />
                  </div>
                )}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-[#1C241E] text-[12px] truncate">{t.title}</p>
                {t.subtitle && (
                  <p className="text-[10px] text-[#5A655C] font-mono truncate">{t.subtitle}</p>
                )}
              </div>
            </div>
            <button
              onClick={() => t.id && removeToast(t.id)}
              className="p-1 text-[#869288] hover:text-[#1C241E] transition shrink-0 ml-2"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context.toast;
};
