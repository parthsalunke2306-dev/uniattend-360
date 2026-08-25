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

      setToasts((prev) => [...prev.slice(-3), newToast]); // Keep max 4 toasts

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
      {/* Floating Modern Toast Stack Container */}
      <div className="fixed top-4 right-4 sm:top-5 sm:right-5 z-[9999] flex flex-col space-y-2 pointer-events-none max-w-sm w-full">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto flex items-center justify-between p-3 rounded-2xl bg-surface/95 border border-white/10 backdrop-blur-xl shadow-soft-glow text-xs font-sans transition-all duration-300 transform translate-y-0 opacity-100 animate-in fade-in slide-in-from-top-2"
          >
            <div className="flex items-center space-x-3 min-w-0">
              <div className="shrink-0">
                {t.type === 'success' && (
                  <div className="p-1.5 rounded-xl bg-accent-mint/15 text-accent-mint border border-accent-mint/30">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                )}
                {t.type === 'error' && (
                  <div className="p-1.5 rounded-xl bg-accent-rose/15 text-accent-rose border border-accent-rose/30">
                    <AlertCircle className="w-4 h-4" />
                  </div>
                )}
                {t.type === 'warning' && (
                  <div className="p-1.5 rounded-xl bg-accent-amber/15 text-accent-amber border border-accent-amber/30">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                )}
                {t.type === 'info' && (
                  <div className="p-1.5 rounded-xl bg-accent-blue/15 text-accent-blue-light border border-accent-blue/30">
                    <Info className="w-4 h-4" />
                  </div>
                )}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-text-primary text-[12px] truncate">{t.title}</p>
                {t.subtitle && (
                  <p className="text-[10px] text-text-muted font-mono truncate">{t.subtitle}</p>
                )}
              </div>
            </div>
            <button
              onClick={() => t.id && removeToast(t.id)}
              className="p-1 text-text-muted hover:text-text-primary transition shrink-0 ml-2"
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

export default ToastProvider;
