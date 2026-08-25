import React, { useState } from 'react';
import { 
  User, 
  ShieldCheck, 
  Fingerprint, 
  Phone, 
  Mail, 
  CheckCircle2, 
  RefreshCw, 
  Lock, 
  Sparkles,
  Smartphone,
  Cpu
} from 'lucide-react';

interface StudentProfile {
  rollNo: string;
  fullName: string;
  department: string;
  semester: string;
  division: string;
  batchYear: number;
  phone: string;
  alternateEmail: string;
  bio: string;
  avatarIcon: string;
  customAvatarUrl?: string;
  deviceLock: {
    isBound: boolean;
    deviceName: string;
    credentialId: string;
    enclaveLevel: string;
    lastVerified: string;
  };
}

export const StudentProfileEdit: React.FC = () => {
  const [profile, setProfile] = useState<StudentProfile>({
    rollNo: 'CHMC-DS-2024-007',
    fullName: 'Kavita Nair',
    department: 'Data Science & Artificial Intelligence',
    semester: 'Semester III',
    division: 'Div A (Batch 2024)',
    batchYear: 2024,
    phone: '9876543210',
    alternateEmail: 'kavita.personal@gmail.com',
    bio: 'S.Y. Data Science student passionate about machine learning and cryptographic security systems.',
    avatarIcon: '🚀',
    deviceLock: {
      isBound: true,
      deviceName: 'Apple iPhone 15 Pro (Secure Enclave)',
      credentialId: 'cred_fido2_8f29e01a',
      enclaveLevel: 'FIDO2 Platform L2 Enclave',
      lastVerified: 'Aug 25, 2026 • 11:35 AM'
    }
  });

  const [isLinking, setIsLinking] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const handleBiometricReLink = async () => {
    setIsLinking(true);
    try {
      // Hardware-level WebAuthn trigger simulation
      setTimeout(() => {
        setProfile(prev => ({
          ...prev,
          deviceLock: {
            ...prev.deviceLock,
            isBound: true,
            lastVerified: 'Just now'
          }
        }));
        setIsLinking(false);
      }, 900);
    } catch (err) {
      setIsLinking(false);
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-text-primary p-4 sm:p-8 flex items-center justify-center font-sans antialiased">
      {/* Ambient Lighting Backdrop Glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[350px] bg-accent-blue/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 right-10 w-[450px] h-[300px] bg-accent-mint/5 rounded-full blur-3xl" />
      </div>

      {/* Main Profile Modal Card (Luminous Frosted Charcoal) */}
      <div className="relative w-full max-w-xl bg-surface/90 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-soft-glow overflow-hidden p-6 sm:p-8 space-y-6">
        
        {/* Header Section */}
        <div className="flex items-start justify-between border-b border-border-subtle pb-5">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-elevated border border-white/10 flex items-center justify-center text-3xl shadow-inner">
                {profile.avatarIcon}
              </div>
              <span className="absolute -bottom-1 -right-1 w-5 h-5 bg-accent-mint rounded-full border-2 border-surface flex items-center justify-center">
                <CheckCircle2 className="w-3 h-3 text-surface stroke-[3]" />
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold tracking-tight text-text-primary">
                  {profile.fullName}
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-accent-blue/15 text-accent-blue-light border border-accent-blue/30">
                  VERIFIED
                </span>
              </div>
              <p className="text-xs text-text-muted font-mono mt-0.5">{profile.rollNo}</p>
              <p className="text-xs text-text-secondary mt-0.5">{profile.department}</p>
            </div>
          </div>
        </div>

        {/* 1. Verified Institutional Records (Warm Milled Slate) */}
        <div className="bg-elevated/70 border border-slate-700/50 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-text-muted" />
              Institutional Records
            </span>
            <span className="text-[10px] font-mono text-text-muted">Locked by Registrar</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs font-mono">
            <div className="bg-surface/80 p-2.5 rounded-xl border border-white/5">
              <span className="text-[10px] text-text-muted block">Program</span>
              <span className="text-text-primary font-semibold">B.Sc. Data Science</span>
            </div>
            <div className="bg-surface/80 p-2.5 rounded-xl border border-white/5">
              <span className="text-[10px] text-text-muted block">Semester / Div</span>
              <span className="text-text-primary font-semibold">{profile.semester} • Div A</span>
            </div>
            <div className="bg-surface/80 p-2.5 rounded-xl border border-white/5 col-span-2 sm:col-span-1">
              <span className="text-[10px] text-text-muted block">Admissions Year</span>
              <span className="text-text-primary font-semibold">{profile.batchYear} - 2027</span>
            </div>
          </div>
        </div>

        {/* 2. Device Biometric & Passkey Anchor (Soothing Mint Glow & High Security) */}
        <div className="bg-elevated/70 border border-slate-700/50 rounded-2xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-lg bg-accent-mint/15 text-accent-mint border border-accent-mint/30">
                <Fingerprint className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">
                  Biometric Passkey Anchor
                </h3>
                <p className="text-[11px] text-text-muted">Single-Device Cryptographic Attendance Anchor</p>
              </div>
            </div>

            {/* Soft Mint Status Pill */}
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-mono font-bold bg-accent-mint/15 text-accent-mint border border-accent-mint/30 shadow-mint-glow">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-mint animate-pulse" />
              BOUND & VERIFIED
            </span>
          </div>

          {/* Bound Hardware Metadata Card */}
          <div className="bg-surface/80 rounded-xl p-3.5 border border-white/5 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2 text-text-secondary">
                <Smartphone className="w-3.5 h-3.5 text-accent-blue" />
                <span className="font-semibold text-text-primary">{profile.deviceLock.deviceName}</span>
              </div>
              <span className="text-[10px] font-mono text-text-muted">{profile.deviceLock.lastVerified}</span>
            </div>
            
            <div className="flex items-center justify-between text-[11px] font-mono text-text-muted pt-1 border-t border-white/5">
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-text-muted" />
                {profile.deviceLock.enclaveLevel}
              </span>
              <span className="text-accent-mint font-semibold">{profile.deviceLock.credentialId}</span>
            </div>
          </div>

          {/* Biometric Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleBiometricReLink}
              disabled={isLinking}
              className="flex-1 py-2 px-3 rounded-xl bg-accent-blue/15 hover:bg-accent-blue/25 text-accent-blue-light text-xs font-semibold font-mono border border-accent-blue/30 transition flex items-center justify-center gap-1.5 shadow-blue-glow"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLinking ? 'animate-spin' : ''}`} />
              <span>{isLinking ? 'Verifying Sensor...' : 'Re-Link Device'}</span>
            </button>
            <button
              type="button"
              className="py-2 px-4 rounded-xl bg-elevated hover:bg-slate-600/50 text-text-secondary text-xs font-mono border border-border-hairline transition"
            >
              Test Biometric Auth
            </button>
          </div>
        </div>

        {/* 3. Editable Student Contact Info */}
        <div className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-text-muted block">
            Personal Contact & Bio
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] text-text-muted block mb-1">WhatsApp / Phone</label>
              <div className="relative">
                <Phone className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  className="w-full bg-elevated border border-slate-700/60 rounded-xl py-2 pl-9 pr-3 text-xs text-text-primary font-mono focus:outline-none focus:border-accent-blue transition"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] text-text-muted block mb-1">Alternate Email</label>
              <div className="relative">
                <Mail className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={profile.alternateEmail}
                  onChange={(e) => setProfile({ ...profile, alternateEmail: e.target.value })}
                  className="w-full bg-elevated border border-slate-700/60 rounded-xl py-2 pl-9 pr-3 text-xs text-text-primary font-mono focus:outline-none focus:border-accent-blue transition"
                />
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-[11px] text-text-muted">Bio / Academic Interest</label>
              <span className="text-[10px] font-mono text-text-muted">{profile.bio.length} / 150</span>
            </div>
            <textarea
              maxLength={150}
              rows={2}
              value={profile.bio}
              onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
              className="w-full bg-elevated border border-slate-700/60 rounded-xl p-2.5 text-xs text-text-primary resize-none focus:outline-none focus:border-accent-blue transition"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-2 flex items-center justify-end space-x-3 border-t border-border-subtle">
          <button
            type="button"
            className="px-4 py-2 rounded-xl text-xs font-semibold text-text-muted hover:text-text-primary transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              setIsSaved(true);
              setTimeout(() => setIsSaved(false), 2000);
            }}
            className="px-5 py-2 rounded-xl bg-accent-blue hover:bg-accent-blue-light text-white text-xs font-semibold shadow-blue-glow transition flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isSaved ? 'Saved Successfully!' : 'Save Changes'}</span>
          </button>
        </div>

      </div>
    </div>
  );
};

export default StudentProfileEdit;
