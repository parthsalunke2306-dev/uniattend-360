import React, { useState } from 'react';
import { 
  ShieldCheck, 
  UserCheck, 
  GraduationCap, 
  School, 
  SlidersHorizontal, 
  KeyRound, 
  Fingerprint, 
  LogOut, 
  Sparkles,
  ChevronDown
} from 'lucide-react';

export type UserRole = 'STUDENT' | 'FACULTY' | 'ADMIN';

export interface UserSession {
  role: UserRole;
  name: string;
  identifier: string;
  department: string;
  avatar: string;
  badge: string;
  isBiometricLinked: boolean;
}

interface NavbarProps {
  currentRole: UserRole;
  userSession: UserSession;
  onRoleChange: (role: UserRole) => void;
  onOpenProfile: () => void;
  onOpenQuickTour?: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentRole,
  userSession,
  onRoleChange,
  onOpenProfile,
  onOpenQuickTour,
  onLogout,
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  return (
    <>
      {/* Top Persistent Header */}
      <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-xl border-b border-border/80 shadow-soft-glow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          
          {/* Brand & Institution Info */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-forest to-sage p-0.5 shadow-sm shrink-0">
              <div className="w-full h-full bg-surface rounded-[14px] flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-forest" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-serif font-bold text-text-primary text-base sm:text-lg leading-tight">
                  Smt. C.H.M. College
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-sage-bg text-sage-text border border-sage/20">
                  UniAttend 360
                </span>
              </div>
              <p className="text-[11px] text-text-secondary font-medium hidden xs:block">
                Department of Data Science • Academic Year 2026
              </p>
            </div>
          </div>

          {/* Center: Simplified 1-Click Role Switcher (Desktop) */}
          <div className="hidden md:flex items-center p-1 bg-elevated rounded-2xl border border-border">
            <button
              onClick={() => onRoleChange('STUDENT')}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                currentRole === 'STUDENT'
                  ? 'bg-surface text-forest shadow-sm border border-border/60'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5" />
              <span>Student Portal</span>
            </button>

            <button
              onClick={() => onRoleChange('FACULTY')}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                currentRole === 'FACULTY'
                  ? 'bg-surface text-forest shadow-sm border border-border/60'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Faculty Kiosk</span>
            </button>

            <button
              onClick={() => onRoleChange('ADMIN')}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                currentRole === 'ADMIN'
                  ? 'bg-surface text-forest shadow-sm border border-border/60'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <School className="w-3.5 h-3.5" />
              <span>Principal Console</span>
            </button>
          </div>

          {/* Right Action Hub: Profile Avatar & Menu */}
          <div className="flex items-center space-x-2.5">
            {/* Quick Tour / Help Button */}
            {onOpenQuickTour && (
              <button
                onClick={onOpenQuickTour}
                className="hidden sm:flex items-center space-x-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-text-secondary bg-elevated hover:bg-surface border border-border transition"
                title="5-Second Quick Tour"
              >
                <Sparkles className="w-3.5 h-3.5 text-ochre" />
                <span>Quick Tour</span>
              </button>
            )}

            {/* Profile Avatar Pill & Dropdown Trigger */}
            <div className="relative">
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center space-x-2 p-1.5 sm:px-3 sm:py-1.5 rounded-2xl bg-elevated hover:bg-surface border border-border transition shadow-sm"
              >
                <div className="w-7 h-7 rounded-xl bg-sage-bg text-forest flex items-center justify-center font-bold text-xs border border-sage/20">
                  {userSession.avatar || '👤'}
                </div>
                <div className="text-left hidden sm:block">
                  <p className="text-xs font-bold text-text-primary leading-tight truncate max-w-[120px]">
                    {userSession.name}
                  </p>
                  <p className="text-[10px] text-text-muted font-mono leading-none truncate">
                    {userSession.identifier}
                  </p>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
              </button>

              {/* Account & Security Dropdown */}
              {isDropdownOpen && (
                <div 
                  className="absolute right-0 mt-2 w-64 rounded-2xl bg-surface border border-border shadow-organic-card p-2 z-50 animate-in fade-in slide-in-from-top-2"
                  onMouseLeave={() => setIsDropdownOpen(false)}
                >
                  <div className="p-2.5 border-b border-border/60 mb-1">
                    <p className="text-xs font-bold text-text-primary">{userSession.name}</p>
                    <p className="text-[11px] text-text-secondary font-mono">{userSession.identifier}</p>
                    <div className="mt-2 flex items-center space-x-1.5">
                      <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                      <span className="text-[10px] font-mono text-text-muted">
                        {userSession.isBiometricLinked ? 'Biometrics Bound' : 'Device Unlinked'}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setIsDropdownOpen(false);
                      onOpenProfile();
                    }}
                    className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium text-text-primary hover:bg-elevated rounded-xl transition text-left"
                  >
                    <Fingerprint className="w-4 h-4 text-forest" />
                    <span>Profile & Biometrics</span>
                  </button>

                  <button
                    onClick={() => {
                      setIsDropdownOpen(false);
                      onOpenProfile();
                    }}
                    className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium text-text-primary hover:bg-elevated rounded-xl transition text-left"
                  >
                    <KeyRound className="w-4 h-4 text-ochre" />
                    <span>Emergency Device Reset</span>
                  </button>

                  <div className="my-1 border-t border-border/60"></div>

                  <button
                    onClick={() => {
                      setIsDropdownOpen(false);
                      onLogout();
                    }}
                    className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium text-clay hover:bg-clay-bg/30 rounded-xl transition text-left"
                  >
                    <LogOut className="w-4 h-4 text-clay" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>

        </div>
      </header>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface/95 backdrop-blur-xl border-t border-border shadow-lg px-4 py-2 flex items-center justify-around">
        <button
          onClick={() => onRoleChange('STUDENT')}
          className={`flex flex-col items-center space-y-1 py-1 px-3 rounded-xl transition ${
            currentRole === 'STUDENT' ? 'text-forest font-bold' : 'text-text-muted'
          }`}
        >
          <GraduationCap className="w-5 h-5" />
          <span className="text-[10px]">Student</span>
        </button>

        <button
          onClick={() => onRoleChange('FACULTY')}
          className={`flex flex-col items-center space-y-1 py-1 px-3 rounded-xl transition ${
            currentRole === 'FACULTY' ? 'text-forest font-bold' : 'text-text-muted'
          }`}
        >
          <UserCheck className="w-5 h-5" />
          <span className="text-[10px]">Faculty</span>
        </button>

        <button
          onClick={() => onRoleChange('ADMIN')}
          className={`flex flex-col items-center space-y-1 py-1 px-3 rounded-xl transition ${
            currentRole === 'ADMIN' ? 'text-forest font-bold' : 'text-text-muted'
          }`}
        >
          <School className="w-5 h-5" />
          <span className="text-[10px]">Principal</span>
        </button>

        <button
          onClick={onOpenProfile}
          className="flex flex-col items-center space-y-1 py-1 px-3 rounded-xl text-text-muted"
        >
          <Fingerprint className="w-5 h-5" />
          <span className="text-[10px]">Security</span>
        </button>
      </nav>
    </>
  );
};
export default Navbar;
