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
import { useToast, ToastProvider } from './Toast';
import { useWebAuthn, WebAuthnDeviceState } from './useWebAuthn';

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
  deviceLock: WebAuthnDeviceState;
}

export const StudentProfileEditContent: React.FC = () => {
  const toast = useToast();
  const { registerPasskey, testBiometricAuth, isProcessing } = useWebAuthn();

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
    avatarIcon: '🎓',
    deviceLock: {
      isBound: true,
      deviceName: 'Apple iPhone 15 Pro (Secure Enclave)',
      credentialId: 'cred_fido2_8f29e01a',
      enclaveLevel: 'FIDO2 Platform L2 Enclave',
      lastVerified: 'Aug 25, 2026 • 11:35 AM'
    }
  });

  const [isSaved, setIsSaved] = useState(false);

  const handleBiometricReLink = async () => {
    const updatedState = await registerPasskey(
      profile.rollNo,
      profile.fullName,
      profile.alternateEmail || `${profile.rollNo.toLowerCase()}@chmc.edu`
    );

    if (updatedState) {
      setProfile((prev) => ({
        ...prev,
        deviceLock: updatedState,
      }));
    }
  };

  const handleTestAuth = async () => {
    await testBiometricAuth(profile.deviceLock);
  };

  const handleSaveProfile = () => {
    setIsSaved(true);
    toast.success('Profile Saved', 'Personal information updated.');
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#FBF9F5] text-[#1C241E] p-4 sm:p-8 flex items-center justify-center font-sans antialiased">
      {/* Ambient Lighting Backdrop Glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[350px] bg-[#2F5238]/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 right-10 w-[450px] h-[300px] bg-[#C28222]/5 rounded-full blur-3xl" />
      </div>

      {/* Main Profile Modal Card */}
      <div className="relative w-full max-w-xl bg-white border border-[#E8E3DA] rounded-3xl shadow-[0_4px_24px_-2px_rgba(50,60,50,0.07)] overflow-hidden p-6 sm:p-8 space-y-6">
        
        {/* Header Section */}
        <div className="flex items-start justify-between border-b border-[#E8E3DA] pb-5">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-[#F5F2EB] border border-[#E8E3DA] flex items-center justify-center text-3xl shadow-inner">
                {profile.avatarIcon}
              </div>
              <span className="absolute -bottom-1 -right-1 w-5 h-5 bg-[#4A6B53] rounded-full border-2 border-white flex items-center justify-center">
                <CheckCircle2 className="w-3 h-3 text-white stroke-[3]" />
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold font-serif tracking-tight text-[#1C241E]">
                  {profile.fullName}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-sans font-bold bg-[#EAF2EB] text-[#2D4F38] border border-[#D5E4D8]">
                  VERIFIED
                </span>
              </div>
              <p className="text-xs text-[#5A655C] font-mono mt-0.5">{profile.rollNo}</p>
              <p className="text-xs text-[#869288] mt-0.5">{profile.department}</p>
            </div>
          </div>
        </div>

        {/* 1. Verified Institutional Records */}
        <div className="bg-[#F5F2EB] border border-[#E8E3DA] rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#5A655C] flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-[#5A655C]" />
              Institutional Records
            </span>
            <span className="text-[10px] font-mono text-[#869288]">Locked by Registrar</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
            <div className="bg-white p-2.5 rounded-xl border border-[#E8E3DA]">
              <span className="text-[10px] text-[#869288] block">Program</span>
              <span className="text-[#1C241E] font-semibold">B.Sc. Data Science</span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-[#E8E3DA]">
              <span className="text-[10px] text-[#869288] block">Semester / Div</span>
              <span className="text-[#1C241E] font-semibold">{profile.semester} • Div A</span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-[#E8E3DA] col-span-2 sm:col-span-1">
              <span className="text-[10px] text-[#869288] block">Admissions Year</span>
              <span className="text-[#1C241E] font-semibold">{profile.batchYear} - 2027</span>
            </div>
          </div>
        </div>

        {/* 2. Device Biometric & Passkey Anchor */}
        <div className="bg-[#F5F2EB] border border-[#E8E3DA] rounded-2xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-lg bg-[#EAF2EB] text-[#2F5238] border border-[#D5E4D8]">
                <Fingerprint className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#1C241E]">
                  Biometric Passkey Anchor
                </h3>
                <p className="text-[11px] text-[#5A655C]">Single-Device Cryptographic Attendance Anchor</p>
              </div>
            </div>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-sans font-bold bg-[#4A6B53] text-white shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              BOUND & ACTIVE
            </span>
          </div>

          {/* Bound Hardware Metadata Card */}
          <div className="bg-white rounded-xl p-3.5 border border-[#E8E3DA] space-y-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2 text-[#5A655C]">
                <Smartphone className="w-3.5 h-3.5 text-[#2F5238]" />
                <span className="font-semibold text-[#1C241E]">{profile.deviceLock.deviceName}</span>
              </div>
              <span className="text-[10px] font-mono text-[#869288]">{profile.deviceLock.lastVerified}</span>
            </div>
            
            <div className="flex items-center justify-between text-[11px] font-mono text-[#869288] pt-1 border-t border-[#E8E3DA]">
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-[#869288]" />
                {profile.deviceLock.enclaveLevel}
              </span>
              <span className="text-[#2F5238] font-semibold">{profile.deviceLock.credentialId}</span>
            </div>
          </div>

          {/* Biometric Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleBiometricReLink}
              disabled={isProcessing}
              className="flex-1 py-2 px-3 rounded-xl bg-[#2F5238] hover:bg-[#25422D] text-white text-xs font-semibold font-sans transition flex items-center justify-center gap-1.5 shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
              <span>{isProcessing ? 'Verifying Sensor...' : 'Re-Link Device'}</span>
            </button>
            <button
              type="button"
              onClick={handleTestAuth}
              disabled={isProcessing}
              className="py-2 px-4 rounded-xl bg-white hover:bg-[#F5F2EB] text-[#1C241E] text-xs font-sans font-semibold border border-[#E8E3DA] transition"
            >
              Test Biometric Auth
            </button>
          </div>
        </div>

        {/* 3. Editable Student Contact Info */}
        <div className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-[#5A655C] block">
            Personal Contact & Bio
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] text-[#5A655C] block mb-1">WhatsApp / Phone</label>
              <div className="relative">
                <Phone className="w-3.5 h-3.5 text-[#869288] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  className="w-full bg-white border border-[#E8E3DA] rounded-xl py-2 pl-9 pr-3 text-xs text-[#1C241E] font-mono focus:outline-none focus:border-[#2F5238] focus:ring-1 focus:ring-[#2F5238] transition"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] text-[#5A655C] block mb-1">Alternate Email</label>
              <div className="relative">
                <Mail className="w-3.5 h-3.5 text-[#869288] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={profile.alternateEmail}
                  onChange={(e) => setProfile({ ...profile, alternateEmail: e.target.value })}
                  className="w-full bg-white border border-[#E8E3DA] rounded-xl py-2 pl-9 pr-3 text-xs text-[#1C241E] font-mono focus:outline-none focus:border-[#2F5238] focus:ring-1 focus:ring-[#2F5238] transition"
                />
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-[11px] text-[#5A655C]">Bio / Academic Interest</label>
              <span className="text-[10px] font-mono text-[#869288]">{profile.bio.length} / 150</span>
            </div>
            <textarea
              maxLength={150}
              rows={2}
              value={profile.bio}
              onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
              className="w-full bg-white border border-[#E8E3DA] rounded-xl p-2.5 text-xs text-[#1C241E] resize-none focus:outline-none focus:border-[#2F5238] focus:ring-1 focus:ring-[#2F5238] transition"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-2 flex items-center justify-end space-x-3 border-t border-[#E8E3DA]">
          <button
            type="button"
            className="px-4 py-2 rounded-xl text-xs font-semibold text-[#869288] hover:text-[#1C241E] transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSaveProfile}
            className="px-5 py-2 rounded-xl bg-[#2F5238] hover:bg-[#25422D] text-white text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isSaved ? 'Saved Successfully!' : 'Save Changes'}</span>
          </button>
        </div>

      </div>
    </div>
  );
};

export const StudentProfileEdit: React.FC = () => {
  return (
    <ToastProvider>
      <StudentProfileEditContent />
    </ToastProvider>
  );
};

export default StudentProfileEdit;
