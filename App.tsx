import React, { useState, useEffect } from 'react';
import { ToastProvider, useToast } from './Toast';
import { Navbar, UserRole, UserSession } from './Navbar';
import { StudentHome } from './StudentHome';
import { FacultyKiosk } from './FacultyKiosk';
import { AdminPortal } from './AdminPortal';
import { StudentProfileEdit } from './StudentProfileEdit';
import { AppLockGate, AppLockUser } from './AppLockGate';
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
  const [isAppLocked, setIsAppLocked] = useState<boolean>(true); // App-launch biometric lock
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isQuickTourOpen, setIsQuickTourOpen] = useState(false);
  const toast = useToast();

  const userSession = INITIAL_SESSIONS[currentRole];

  // Auto-Lock Lifecycle: Re-authenticate on background return or inactivity
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Tab went to background
        sessionStorage.setItem('uniattend_background_time', Date.now().toString());
      } else {
        // Tab restored from background: prompt re-authentication if away > 5s
        const bgTime = parseInt(sessionStorage.getItem('uniattend_background_time') || '0', 10);
        if (bgTime && Date.now() - bgTime > 5000) {
          setIsAppLocked(true);
          toast.info('Session Locked', 'Biometric re-verification required.');
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [toast]);

  const handleRoleChange = (role: UserRole) => {
    setCurrentRole(role);
    toast.info('Switched View', `Active Portal: ${role}`);
  };

  const handleLogout = () => {
    setIsAppLocked(true);
    toast.info('Signed Out', 'App locked. Authenticate to enter.');
  };

  const handleManualLock = () => {
    setIsAppLocked(true);
    toast.info('Application Locked', 'Biometric scan required.');
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
      {/* 1. MANDATORY APP-LAUNCH BIOMETRIC LOCK GATE */}
      <AppLockGate
        isLocked={isAppLocked}
        user={appLockUserData}
        onUnlock={() => setIsAppLocked(false)}
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
        onLockApp={handleManualLock}
        onLogout={handleLogout}
      />

      {/* 3. DYNAMIC ROLE-BASED PORTAL */}
      <main className="flex-1">
        {currentRole === 'STUDENT' && <StudentHome />}
        {currentRole === 'FACULTY' && <FacultyKiosk />}
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
