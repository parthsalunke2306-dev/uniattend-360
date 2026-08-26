import React, { useState, useEffect } from 'react';
import { ToastProvider, useToast } from './Toast';
import { Navbar, UserRole, UserSession } from './Navbar';
import { StudentHome } from './StudentHome';
import { FacultyKiosk } from './FacultyKiosk';
import { AdminPortal } from './AdminPortal';
import { StudentProfileEdit } from './StudentProfileEdit';
import { AppLockGate, AppLockUser, UnlockMethod } from './AppLockGate';
import { Sparkles, CheckCircle2, QrCode, Play, ShieldCheck, X } from 'lucide-react';

const INITIAL_SESSIONS: Record<UserRole, UserSession> = {
  STUDENT: {
    role: 'STUDENT',
    name: 'Alex Chen',
    identifier: 'CHMC-DS-2024-001',
    department: 'Data Science',
    avatar: '🎓',
    badge: 'STUDENT',
    isBiometricLinked: true,
  },
  FACULTY: {
    role: 'FACULTY',
    name: 'Miss Razia Khan',
    identifier: 'FAC-DS-01',
    department: 'Data Science',
    avatar: '👩‍🏫',
    badge: 'FACULTY',
    isBiometricLinked: true,
  },
  ADMIN: {
    role: 'ADMIN',
    name: 'Dr. Manju Lalwani Pathak',
    identifier: 'ADMIN-CHMC-001',
    department: 'Principal Super-Admin',
    avatar: '🏛️',
    badge: 'PRINCIPAL',
    isBiometricLinked: true,
  },
};

const MainContent: React.FC = () => {
  const [currentRole, setCurrentRole] = useState<UserRole>('STUDENT');
  const [fallbackProxyAlerts, setFallbackProxyAlerts] = useState<string[]>([]);
  
  // Automatic Browser-Close Session Biometric Lock:
  // Evaluates sessionStorage on initial app launch. If browser/tab was closed, sessionStorage is empty, triggering biometric gate.
  const [isAppLocked, setIsAppLocked] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    return sessionStorage.getItem('uniattend_session_unlocked') !== 'true';
  });

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isQuickTourOpen, setIsQuickTourOpen] = useState(false);
  const toast = useToast();

  const userSession = INITIAL_SESSIONS[currentRole];

  const handleUnlock = (method: UnlockMethod) => {
    setIsAppLocked(false);
    sessionStorage.setItem('uniattend_session_unlocked', 'true');

    if (method === 'FALLBACK_2FA') {
      const alertMsg = `⚠️ Fallback Access Flag: ${userSession.name} (${userSession.identifier}) logged in via Email 2FA (Bypassed Hardware Biometrics).`;
      setFallbackProxyAlerts((prev) => [alertMsg, ...prev]);
      toast.warning('Faculty Alert Dispatched', 'Real-time proxy flag sent to lecturing staff.');
    }
  };

  const handleRoleChange = (role: UserRole) => {
    setCurrentRole(role);
    toast.info('Switched View', `Active Portal: ${role}`);
  };

  const handleLogout = () => {
    sessionStorage.removeItem('uniattend_session_unlocked');
    setIsAppLocked(true);
    toast.info('Signed Out', 'Session expired. Biometric unlock required to re-enter.');
  };

  const appLockUserData: AppLockUser = {
    name: userSession.name,
    identifier: userSession.identifier,
    role: userSession.role,
    avatar: userSession.avatar,
    department: userSession.department,
  };

  return (
    <div className="min-h-screen bg-canvas text-text-primary flex flex-col font-sans pb-20 md:pb-8">
      {/* 1. MANDATORY BROWSER-SESSION BIOMETRIC LOCK GATE */}
      <AppLockGate
        isLocked={isAppLocked}
        user={appLockUserData}
        onUnlock={handleUnlock}
        onSwitchAccount={() => {
          setIsAppLocked(false);
          setIsProfileOpen(true);
        }}
      />

      {/* 2. TOP PERSISTENT NAVBAR & MOBILE DOCK */}
      <Navbar
        currentRole={currentRole}
        userSession={userSession}
        onRoleChange={handleRoleChange}
        onOpenProfile={() => setIsProfileOpen(true)}
        onOpenQuickTour={() => setIsQuickTourOpen(true)}
        onLogout={handleLogout}
      />

      {/* 3. DYNAMIC ROLE-BASED PORTAL */}
      <main className="flex-1">
        {currentRole === 'STUDENT' && <StudentHome />}
        {currentRole === 'FACULTY' && (
          <FacultyKiosk 
            fallbackAlerts={fallbackProxyAlerts} 
            onClearFallbackAlerts={() => setFallbackProxyAlerts([])} 
          />
        )}
        {currentRole === 'ADMIN' && <AdminPortal />}
      </main>

      {/* 4. STUDENT PROFILE & BIOMETRIC LINKING MODAL */}
      {isProfileOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface rounded-3xl border border-border shadow-organic-card max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 relative animate-in fade-in">
            <button
              onClick={() => setIsProfileOpen(false)}
              className="absolute top-5 right-5 p-2 text-text-muted hover:text-text-primary transition"
            >
              <X className="w-5 h-5" />
            </button>
            <StudentProfileEdit
              initialProfile={{
                id: userSession.identifier,
                name: userSession.name,
                rollNo: userSession.identifier,
                department: userSession.department,
                semester: 3,
                batchYear: 2024,
                email: 'alex.chen@chmc.edu',
                phone: '+91 98765 43210',
                bio: 'Passionate data science student interested in NLP & predictive analytics.',
                avatar: userSession.avatar,
                emergencyCode: 'CHMC-REC-9942',
              }}
              onSave={() => setIsProfileOpen(false)}
              onClose={() => setIsProfileOpen(false)}
            />
          </div>
        </div>
      )}

      {/* 5. 5-SECOND QUICK START GUIDE MODAL */}
      {isQuickTourOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface rounded-3xl border border-border shadow-organic-card max-w-md w-full p-6 sm:p-8 space-y-6 animate-in fade-in">
            <div className="flex items-center justify-between border-b border-border/70 pb-3">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 rounded-xl bg-sage-bg text-forest">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h3 className="text-base font-serif font-bold text-text-primary">
                  5-Second Quick Start Guide
                </h3>
              </div>
              <button
                onClick={() => setIsQuickTourOpen(false)}
                className="p-1 text-text-muted hover:text-text-primary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="flex items-start space-x-3 p-3 rounded-2xl bg-elevated border border-border">
                <div className="p-2 rounded-xl bg-sage-bg text-forest font-bold shrink-0">
                  <QrCode className="w-4 h-4" />
                </div>
                <div>
                  <p className="font-bold text-text-primary">For Students: 1-Tap Check In</p>
                  <p className="text-text-secondary mt-0.5">
                    Open camera $\rightarrow$ point at classroom screen $\rightarrow$ instant biometric check-in.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-3 rounded-2xl bg-elevated border border-border">
                <div className="p-2 rounded-xl bg-sage-bg text-forest font-bold shrink-0">
                  <Play className="w-4 h-4" />
                </div>
                <div>
                  <p className="font-bold text-text-primary">For Faculty: 3-Click Kiosk</p>
                  <p className="text-text-secondary mt-0.5">
                    Select lecture $\rightarrow$ click Start Session $\rightarrow$ display rotating QR code.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-3 rounded-2xl bg-elevated border border-border">
                <div className="p-2 rounded-xl bg-sage-bg text-forest font-bold shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <p className="font-bold text-text-primary">Anti-Proxy Protection</p>
                  <p className="text-text-secondary mt-0.5">
                    1 phone per student lock + live classroom location perimeter prevents WhatsApp proxy fraud.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={() => setIsQuickTourOpen(false)}
              className="w-full py-3 rounded-2xl bg-forest hover:bg-forest-hover text-white text-xs font-bold shadow-md transition"
            >
              Got It, Let's Go! →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <MainContent />
    </ToastProvider>
  );
};

export default App;
