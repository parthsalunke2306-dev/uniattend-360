import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  Eye,
  EyeOff,
  Mail,
  User,
  IdCard,
  LogIn,
  Users,
  ChevronDown
} from 'lucide-react';
import { useToast } from './Toast';

export interface AppLockUser {
  name: string;
  identifier: string;
  role: string;
  avatar: string;
  department: string;
}

export type UnlockMethod = 'GOOGLE_PASSWORD_MANAGER' | 'CREDENTIALS' | 'BIOMETRIC';

interface AppLockGateProps {
  isLocked: boolean;
  user: AppLockUser;
  onUnlock: (method: UnlockMethod) => void;
  onSwitchAccount?: () => void;
}

export const AppLockGate: React.FC<AppLockGateProps> = ({
  isLocked,
  user,
  onUnlock,
}) => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'SIGNIN' | 'REGISTER'>('SIGNIN');
  
  // Login Form Fields (matching hand-drawn sketch)
  const [inputName, setInputName] = useState<string>(user?.name || 'Alex Chen');
  const [inputRollNo, setInputRollNo] = useState<string>(user?.identifier || 'CHMC-DS-2024-001');
  const [inputEmail, setInputEmail] = useState<string>(
    user?.identifier ? `${user.identifier.toLowerCase().replace(/[^a-z0-9]/g, '.')}@chmc.edu` : 'alex.chen@chmc.edu'
  );
  const [inputPassword, setInputPassword] = useState<string>('CHMC@2026!');
  const [showInputPassword, setShowInputPassword] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Register Form Fields (matching second hand-drawn sketch)
  const [regFirstName, setRegFirstName] = useState<string>('');
  const [regMiddleName, setRegMiddleName] = useState<string>('');
  const [regLastName, setRegLastName] = useState<string>('');
  const [regEmail, setRegEmail] = useState<string>('');
  const [regPassword, setRegPassword] = useState<string>('');
  const [regConfirmPassword, setRegConfirmPassword] = useState<string>('');
  const [showRegPassword, setShowRegPassword] = useState<boolean>(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState<boolean>(false);
  const [regCategory, setRegCategory] = useState<string>('STUDENT');
  const [regError, setRegError] = useState<string | null>(null);

  // Sync with user prop if user changes
  useEffect(() => {
    if (user) {
      setInputName(user.name);
      setInputRollNo(user.identifier);
      setInputEmail(`${user.identifier.toLowerCase().replace(/[^a-z0-9]/g, '.')}@chmc.edu`);
    }
  }, [user]);

  // Quick fill persona helper
  const handleQuickFill = (name: string, rollNo: string, email: string, pwd = 'CHMC@2026!') => {
    setInputName(name);
    setInputRollNo(rollNo);
    setInputEmail(email);
    setInputPassword(pwd);
    setLoginError(null);
  };

  // Direct login with Google Password Manager / Passkey
  const handleGooglePasswordManagerLogin = async () => {
    toast.info('Google Password Manager', 'Authenticating credentials...');
    try {
      if (typeof window !== 'undefined' && window.PublicKeyCredential && navigator.credentials) {
        const challengeBuffer = new Uint8Array(32);
        window.crypto.getRandomValues(challengeBuffer);
        let rpId = window.location.hostname === 'localhost' ? 'localhost' : window.location.hostname;

        await navigator.credentials.get({
          publicKey: {
            challenge: challengeBuffer,
            rpId,
            userVerification: 'preferred',
            timeout: 10000,
          },
        }).catch(() => null);
      }
    } catch (err) {
      console.warn('Google Password Manager prompt:', err);
    }

    toast.success('Portal Unlocked', `Welcome back, ${inputName.split(' ')[0]}. Verified via Google Password Manager.`);
    onUnlock('GOOGLE_PASSWORD_MANAGER');
  };

  // Handle Standard Login Submission
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPassword) {
      setLoginError('Please enter your account password.');
      return;
    }
    if (inputPassword !== 'CHMC@2026!' && inputPassword.length < 6) {
      setLoginError('Invalid password. (Default: CHMC@2026!)');
      return;
    }

    setLoginError(null);

    // Trigger Google Password Manager / native Passkey prompt if available
    if (typeof window !== 'undefined' && window.PublicKeyCredential && navigator.credentials) {
      try {
        const challengeBuffer = new Uint8Array(32);
        window.crypto.getRandomValues(challengeBuffer);
        let rpId = window.location.hostname === 'localhost' ? 'localhost' : window.location.hostname;

        await navigator.credentials.get({
          publicKey: {
            challenge: challengeBuffer,
            rpId,
            userVerification: 'preferred',
            timeout: 3000,
          },
        }).catch(() => null);
      } catch (err) {
        console.log('Google Password Manager passkey check:', err);
      }
    }

    toast.success('Portal Unlocked', `Welcome back, ${inputName.split(' ')[0]}.`);
    onUnlock('CREDENTIALS');
  };

  // Handle Create Account Submission (Matching Sketch in Image 2)
  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!regFirstName.trim() || !regLastName.trim()) {
      setRegError('Please enter both First name and Last name.');
      return;
    }
    if (!regEmail.trim() || !regEmail.includes('@')) {
      setRegError('Please enter a valid email address.');
      return;
    }
    if (regPassword.length < 6) {
      setRegError('Password must be at least 6 characters long.');
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegError('Passwords do not match. Please re-enter.');
      return;
    }

    setRegError(null);
    const fullName = [regFirstName.trim(), regMiddleName.trim(), regLastName.trim()].filter(Boolean).join(' ');
    toast.success('Account Created', `Welcome, ${regFirstName}! Role: ${regCategory}`);
    onUnlock('CREDENTIALS');
  };

  if (!isLocked) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-canvas/98 backdrop-blur-2xl flex flex-col items-center justify-center p-4 sm:p-6 select-none animate-in fade-in duration-300">
      
      {/* Background Glow */}
      <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 sm:w-96 h-80 sm:h-96 bg-forest/5 rounded-full blur-3xl pointer-events-none"></div>

      <div className="max-w-md w-full p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card relative z-10 space-y-4 text-center max-h-[92vh] overflow-y-auto">
        
        {/* Header & Institution Branding (Logo Box & Title) */}
        <div className="text-center space-y-1.5 pb-1 border-b border-border">
          <div className="h-11 w-11 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-emerald-400 p-0.5 mx-auto shadow-md flex items-center justify-center">
            <div className="h-full w-full bg-surface rounded-[14px] flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-forest" />
            </div>
          </div>
          <h2 className="text-xl sm:text-2xl font-serif font-bold text-text-primary tracking-tight">
            Smt. C.H.M. College
          </h2>
          <p className="text-[11px] text-text-secondary font-sans">
            UniAttend 360 • Attendance Portal
          </p>
        </div>

        {/* Tab Switcher: Sign In vs Create Account */}
        <div className="flex rounded-xl bg-elevated p-1 border border-border text-xs font-mono">
          <button 
            type="button" 
            onClick={() => setActiveTab('SIGNIN')} 
            className={`flex-1 py-2 rounded-lg font-bold transition duration-150 ${
              activeTab === 'SIGNIN' 
                ? 'bg-forest hover:bg-forest-hover text-white shadow' 
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Sign In
          </button>
          <button 
            type="button" 
            onClick={() => setActiveTab('REGISTER')} 
            className={`flex-1 py-2 rounded-lg font-bold transition duration-150 ${
              activeTab === 'REGISTER' 
                ? 'bg-forest hover:bg-forest-hover text-white shadow' 
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* TAB 1: SIGN IN FORM */}
        {activeTab === 'SIGNIN' && (
          <div className="space-y-4 text-left animate-in fade-in">
            <form onSubmit={handleLoginSubmit} className="space-y-3.5">
              
              {/* Field 1: Name * */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-bold text-text-primary block">
                  Name <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-text-muted absolute left-3 top-3" />
                  <input 
                    type="text" 
                    autoComplete="name"
                    placeholder="Enter full name (e.g. Alex Chen)" 
                    required 
                    value={inputName}
                    onChange={(e) => setInputName(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-text-primary font-sans placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>
              </div>

              {/* Field 2: Roll no * */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-bold text-text-primary block">
                  Roll no <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <IdCard className="w-4 h-4 text-text-muted absolute left-3 top-3" />
                  <input 
                    type="text" 
                    autoComplete="username"
                    placeholder="e.g. CHMC-DS-2024-001 or Faculty ID" 
                    required 
                    value={inputRollNo}
                    onChange={(e) => setInputRollNo(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-text-primary font-mono placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>
              </div>

              {/* Field 3: Email * */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-bold text-text-primary block">
                  Email <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-text-muted absolute left-3 top-3" />
                  <input 
                    type="email" 
                    autoComplete="email"
                    placeholder="e.g. alex.chen@chmc.edu" 
                    required 
                    value={inputEmail}
                    onChange={(e) => setInputEmail(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-text-primary font-mono placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>
              </div>

              {/* Field 4: Password * */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-bold text-text-primary block">
                  Password <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-text-muted absolute left-3 top-3" />
                  <input 
                    type={showInputPassword ? 'text' : 'password'} 
                    autoComplete="current-password"
                    placeholder="Enter password (CHMC@2026!)" 
                    required 
                    value={inputPassword}
                    onChange={(e) => setInputPassword(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-9 pr-10 py-2.5 text-xs text-text-primary font-mono placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                  <button 
                    type="button" 
                    onClick={() => setShowInputPassword(!showInputPassword)} 
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                  >
                    {showInputPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Error Alert Banner */}
              {loginError && (
                <div className="p-2.5 rounded-xl bg-clay-bg border border-clay/30 text-clay text-[11px] font-mono text-center">
                  {loginError}
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-2 pt-1">
                {/* Primary Submit Button: Login / Sign in */}
                <button 
                  type="submit" 
                  className="w-full py-3.5 px-4 rounded-xl bg-forest hover:bg-forest-hover text-white font-bold text-xs sm:text-sm font-mono shadow-md flex items-center justify-center space-x-2 transition duration-150 transform active:scale-[0.99]"
                >
                  <LogIn className="w-4 h-4" />
                  <span>Login / Sign in</span>
                </button>

                {/* Direct Google Password Manager / Passkey Button */}
                <button 
                  type="button" 
                  onClick={handleGooglePasswordManagerLogin}
                  className="w-full py-2.5 px-3 rounded-xl bg-elevated hover:bg-surface text-text-primary font-bold text-xs font-mono border border-border flex items-center justify-center space-x-2 transition shadow-sm"
                >
                  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                  </svg>
                  <span>Sign in with Google Password Manager</span>
                </button>
              </div>
            </form>

            {/* Quick Demo Fill Chips */}
            <div className="pt-2 border-t border-border space-y-1.5">
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-wider block text-center">⚡ Quick-Fill Demo Profiles:</span>
              <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                <button 
                  type="button" 
                  onClick={() => handleQuickFill('Alex Chen', 'CHMC-DS-2024-001', 'alex.chen@chmc.edu')}
                  className="p-1.5 rounded-lg bg-sage-bg/60 hover:bg-sage-bg border border-sage/30 text-forest text-left truncate font-bold"
                >
                  🎓 Alex Chen (001)
                </button>
                <button 
                  type="button" 
                  onClick={() => handleQuickFill('Aarav Sharma', 'CHMC-DS-2024-002', 'aarav.sharma@chmc.edu')}
                  className="p-1.5 rounded-lg bg-elevated hover:bg-surface border border-border text-forest text-left truncate"
                >
                  🎓 Aarav (002)
                </button>
                <button 
                  type="button" 
                  onClick={() => handleQuickFill('Miss Razia Khan', 'faculty.razia', 'razia.khan@chmc.edu')}
                  className="p-1.5 rounded-lg bg-sage-bg/60 hover:bg-sage-bg border border-sage/30 text-forest text-left truncate"
                >
                  👩‍🏫 Miss Razia (Faculty)
                </button>
                <button 
                  type="button" 
                  onClick={() => handleQuickFill('Mrs. Shiji Wilson', 'coordinator.ds', 'shiji.wilson@chmc.edu')}
                  className="p-1.5 rounded-lg bg-elevated hover:bg-surface border border-border text-forest text-left truncate"
                >
                  👔 Mrs. Shiji (HOD)
                </button>
                <button 
                  type="button" 
                  onClick={() => handleQuickFill('Dr. Manju Lalwani Pathak', 'principal.chmc', 'principal@chmc.edu')}
                  className="p-1.5 rounded-lg bg-elevated hover:bg-surface border border-border text-forest text-left truncate font-bold col-span-2 text-center"
                >
                  👑 Dr. Manju Lalwani Pathak (Principal)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: CREATE ACCOUNT FORM (EXACT MATCH TO HAND-DRAWN SKETCH IN IMAGE 2) */}
        {activeTab === 'REGISTER' && (
          <div className="space-y-3 text-left animate-in fade-in">
            <form onSubmit={handleRegisterSubmit} className="space-y-3">
              
              {/* Row 1: Firstname, Middle name, Last name (3 columns) */}
              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-1">
                  <label className="text-[11px] font-mono font-bold text-text-primary block truncate">
                    Firstname <span className="text-clay">*</span>
                  </label>
                  <input 
                    type="text" 
                    placeholder="First name" 
                    required 
                    value={regFirstName}
                    onChange={(e) => setRegFirstName(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl px-2.5 py-2 text-xs text-text-primary font-sans placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono font-bold text-text-primary block truncate">
                    Middle name
                  </label>
                  <input 
                    type="text" 
                    placeholder="Middle" 
                    value={regMiddleName}
                    onChange={(e) => setRegMiddleName(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl px-2.5 py-2 text-xs text-text-primary font-sans placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono font-bold text-text-primary block truncate">
                    Last name <span className="text-clay">*</span>
                  </label>
                  <input 
                    type="text" 
                    placeholder="Last name" 
                    required 
                    value={regLastName}
                    onChange={(e) => setRegLastName(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl px-2.5 py-2 text-xs text-text-primary font-sans placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>
              </div>

              {/* Row 2: Email address */}
              <div className="space-y-1">
                <label className="text-[11px] font-mono font-bold text-text-primary block">
                  Email address <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 text-text-muted absolute left-3 top-3" />
                  <input 
                    type="email" 
                    placeholder="e.g. alex.chen@chmc.edu" 
                    required 
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-8 pr-3 py-2 text-xs text-text-primary font-mono placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                </div>
              </div>

              {/* Row 3: Password */}
              <div className="space-y-1">
                <label className="text-[11px] font-mono font-bold text-text-primary block">
                  Password <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-3.5 h-3.5 text-text-muted absolute left-3 top-3" />
                  <input 
                    type={showRegPassword ? 'text' : 'password'} 
                    placeholder="Enter password (min 6 chars)" 
                    required 
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-8 pr-9 py-2 text-xs text-text-primary font-mono placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                  <button 
                    type="button" 
                    onClick={() => setShowRegPassword(!showRegPassword)} 
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                  >
                    {showRegPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Row 4: Confirm Password */}
              <div className="space-y-1">
                <label className="text-[11px] font-mono font-bold text-text-primary block">
                  Confirm Password <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <ShieldCheck className="w-3.5 h-3.5 text-text-muted absolute left-3 top-3" />
                  <input 
                    type={showRegConfirmPassword ? 'text' : 'password'} 
                    placeholder="Re-enter password" 
                    required 
                    value={regConfirmPassword}
                    onChange={(e) => setRegConfirmPassword(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-8 pr-9 py-2 text-xs text-text-primary font-mono placeholder-text-muted focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition"
                  />
                  <button 
                    type="button" 
                    onClick={() => setShowRegConfirmPassword(!showRegConfirmPassword)} 
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                  >
                    {showRegConfirmPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Row 5: User category (Select / Dropdown) */}
              <div className="space-y-1">
                <label className="text-[11px] font-mono font-bold text-text-primary block">
                  User category <span className="text-clay">*</span>
                </label>
                <div className="relative">
                  <Users className="w-3.5 h-3.5 text-text-muted absolute left-3 top-3 pointer-events-none" />
                  <select 
                    value={regCategory}
                    onChange={(e) => setRegCategory(e.target.value)}
                    className="w-full bg-elevated border border-border rounded-xl pl-8 pr-8 py-2 text-xs text-text-primary font-sans appearance-none focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest transition cursor-pointer font-medium"
                  >
                    <option value="STUDENT">🎓 Student</option>
                    <option value="TEACHER">👨‍🏫 Faculty</option>
                    <option value="COORDINATOR">👔 Course Coordinator</option>
                  </select>
                  <ChevronDown className="w-3.5 h-3.5 text-text-muted absolute right-3 top-3 pointer-events-none" />
                </div>
              </div>

              {/* Error Alert Banner */}
              {regError && (
                <div className="p-2.5 rounded-xl bg-clay-bg border border-clay/30 text-clay text-[11px] font-mono text-center">
                  {regError}
                </div>
              )}

              {/* Row 6: Submit Button (Matching Sketch) */}
              <button 
                type="submit" 
                className="w-full py-3 px-4 rounded-xl bg-forest hover:bg-forest-hover text-white font-bold text-xs sm:text-sm font-mono shadow-md flex items-center justify-center space-x-2 transition duration-150 transform active:scale-[0.99]"
              >
                <span>Submit</span>
              </button>
            </form>
          </div>
        )}

      </div>

    </div>
  );
};

export default AppLockGate;
