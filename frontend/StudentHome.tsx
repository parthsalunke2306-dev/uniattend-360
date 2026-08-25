import React, { useState } from 'react';
import { 
  QrCode, 
  KeyRound, 
  MapPin, 
  Smartphone, 
  CheckCircle2, 
  Sparkles, 
  BookOpen, 
  TrendingUp, 
  Sliders, 
  ShieldCheck, 
  AlertTriangle,
  Camera,
  RefreshCw,
  Clock
} from 'lucide-react';
import { useToast } from './Toast';

export interface SubjectAttendance {
  code: string;
  name: string;
  held: number;
  attended: number;
  faculty: string;
  room: string;
}

const INITIAL_SUBJECTS: SubjectAttendance[] = [
  { code: 'DS201-DM', name: 'Data Mining (Theory)', held: 24, attended: 22, faculty: 'Miss Razia Khan', room: 'E-104' },
  { code: 'DS202-BD', name: 'Big Data Architecture', held: 22, attended: 20, faculty: 'Prof. Amit Sharma', room: 'M-113' },
  { code: 'DS203-ML', name: 'Machine Learning Lab', held: 18, attended: 17, faculty: 'Dr. Priya Desai', room: 'Lab 4' },
  { code: 'DS204-CC', name: 'Cloud Computing & DevOps', held: 16, attended: 15, faculty: 'Prof. Suresh Nair', room: 'E-102' },
  { code: 'DS205-AI', name: 'Applied AI & NLP', held: 14, attended: 14, faculty: 'Dr. Manju Lalwani Pathak', room: 'Auditorium' },
];

export const StudentHome: React.FC = () => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'QR' | 'PIN'>('QR');
  const [pinCode, setPinCode] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [isMarkedPresent, setIsMarkedPresent] = useState(false);
  const [simulatedExtraClasses, setSimulatedExtraClasses] = useState(5);
  const [selectedLectureVenue, setSelectedLectureVenue] = useState('DS201-DM: Data Mining (Theory) — E-104');

  // Attendance Aggregates
  const totalHeld = INITIAL_SUBJECTS.reduce((acc, s) => acc + s.held, 0); // 94
  const totalAttended = INITIAL_SUBJECTS.reduce((acc, s) => acc + s.attended, 0); // 88
  const overallPercentage = Math.round((totalAttended / totalHeld) * 100); // 94%

  // Simulated Future Percentage
  const simHeld = totalHeld + simulatedExtraClasses;
  const simAttended = totalAttended + simulatedExtraClasses;
  const simPercentage = ((simAttended / simHeld) * 100).toFixed(1);

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pinCode.trim().length !== 6) {
      toast.error('Invalid PIN', 'Enter a 6-digit classroom PIN.');
      return;
    }
    // Simulate Instant In-Class Verification
    setIsMarkedPresent(true);
    toast.success('Attendance Marked', 'You are verified in Room E-104.');
  };

  const handleStartScanner = () => {
    setIsScanning(true);
    // Simulate QR reading & instant biometric verification after 1.8s
    setTimeout(() => {
      setIsScanning(false);
      setIsMarkedPresent(true);
      toast.success('Attendance Marked', 'Live QR code scanned & verified.');
    }, 1800);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      
      {/* 1. HERO ATTENDANCE STATUS CARD */}
      <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          
          {/* Left: Overall Ring Metric */}
          <div className="flex items-center space-x-5">
            <div className="relative w-24 h-24 flex items-center justify-center shrink-0">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-border"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-forest transition-all duration-1000 ease-out"
                  strokeDasharray={`${overallPercentage}, 100`}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <div className="absolute text-center">
                <span className="text-xl font-bold font-serif text-text-primary leading-none">
                  {overallPercentage}%
                </span>
                <p className="text-[9px] font-mono text-text-secondary uppercase">Overall</p>
              </div>
            </div>

            <div>
              <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sage-bg text-sage-text border border-sage/20 mb-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-forest" />
                <span>Eligible for Final Exams</span>
              </div>
              <h2 className="text-lg font-serif font-bold text-text-primary">
                Good Standing (Safe above 75% Cutoff)
              </h2>
              <p className="text-xs text-text-secondary">
                {totalAttended} attended out of {totalHeld} total lectures held this semester.
              </p>
            </div>
          </div>

          {/* Right: Quick Ledger Stat Badges */}
          <div className="flex items-center space-x-3 w-full sm:w-auto justify-around sm:justify-end border-t sm:border-t-0 pt-4 sm:pt-0 border-border">
            <div className="text-center px-3 py-2 rounded-2xl bg-elevated border border-border min-w-[75px]">
              <p className="text-[10px] text-text-muted font-mono uppercase">Held</p>
              <p className="text-base font-bold text-text-primary">{totalHeld}</p>
            </div>
            <div className="text-center px-3 py-2 rounded-2xl bg-sage-bg border border-sage/20 min-w-[75px]">
              <p className="text-[10px] text-sage-text font-mono uppercase">Present</p>
              <p className="text-base font-bold text-forest">{totalAttended}</p>
            </div>
            <div className="text-center px-3 py-2 rounded-2xl bg-elevated border border-border min-w-[75px]">
              <p className="text-[10px] text-text-muted font-mono uppercase">Missed</p>
              <p className="text-base font-bold text-clay">{totalHeld - totalAttended}</p>
            </div>
          </div>

        </div>
      </div>

      {/* 2. THE "CHECK IN" ACTION HUB (Rule of 1 Primary Action) */}
      <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card space-y-6">
        
        {/* Header & Classroom Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/70 pb-4">
          <div>
            <h3 className="text-base font-serif font-bold text-text-primary flex items-center space-x-2">
              <span>Mark Today's Attendance</span>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </h3>
            <p className="text-xs text-text-secondary">
              Select your current lecture venue and verify in under 3 seconds.
            </p>
          </div>

          {/* Venue Dropdown */}
          <div className="sm:max-w-xs w-full">
            <select
              value={selectedLectureVenue}
              onChange={(e) => setSelectedLectureVenue(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-xs font-medium bg-elevated border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-forest"
            >
              <option value="DS201-DM: Data Mining (Theory) — E-104">
                [Lec #14] DS201-DM: Data Mining — Room E-104 (ACTIVE)
              </option>
              <option value="DS202-BD: Big Data Architecture — M-113">
                [Lec #11] DS202-BD: Big Data — Room M-113
              </option>
            </select>
          </div>
        </div>

        {/* Success Confirmation State */}
        {isMarkedPresent ? (
          <div className="p-6 rounded-2xl bg-sage-bg border border-sage/30 text-center space-y-3 animate-in fade-in">
            <div className="w-12 h-12 rounded-full bg-forest text-white mx-auto flex items-center justify-center shadow-md">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-base font-serif font-bold text-forest">
                Attendance Recorded Successfully!
              </h4>
              <p className="text-xs text-text-secondary mt-0.5">
                Verified in Room E-104 • Data Mining (Theory) • Timestamp: Just now
              </p>
            </div>
            <button
              onClick={() => setIsMarkedPresent(false)}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-surface text-text-primary border border-border hover:bg-elevated transition shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5 text-text-muted" />
              <span>Mark Another Subject</span>
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            
            {/* Segmented Method Tabs */}
            <div className="flex items-center p-1 bg-elevated rounded-2xl border border-border max-w-sm mx-auto">
              <button
                onClick={() => setActiveTab('QR')}
                className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-xl text-xs font-bold transition ${
                  activeTab === 'QR'
                    ? 'bg-surface text-forest shadow-sm border border-border/60'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <QrCode className="w-4 h-4" />
                <span>Scan Projector QR</span>
              </button>
              <button
                onClick={() => setActiveTab('PIN')}
                className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-xl text-xs font-bold transition ${
                  activeTab === 'PIN'
                    ? 'bg-surface text-forest shadow-sm border border-border/60'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <KeyRound className="w-4 h-4" />
                <span>Enter 6-Digit PIN</span>
              </button>
            </div>

            {/* TAB 1: QR CODE CAMERA SCANNER */}
            {activeTab === 'QR' && (
              <div className="max-w-sm mx-auto space-y-4 text-center">
                <div className="relative aspect-square w-full rounded-2xl bg-canvas-muted border-2 border-dashed border-border flex flex-col items-center justify-center p-6 overflow-hidden">
                  {isScanning ? (
                    <div className="space-y-3">
                      <div className="w-12 h-12 rounded-full bg-forest text-white mx-auto flex items-center justify-center animate-spin">
                        <Camera className="w-6 h-6" />
                      </div>
                      <p className="text-xs font-medium text-text-primary">Scanning classroom screen...</p>
                      <p className="text-[10px] text-text-muted">Align rotating QR inside viewfinder</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="w-14 h-14 rounded-2xl bg-surface text-forest mx-auto flex items-center justify-center border border-border shadow-sm">
                        <QrCode className="w-7 h-7" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-text-primary">Camera Ready</p>
                        <p className="text-[11px] text-text-secondary mt-0.5">
                          Point at the instructor's live 8-second QR code.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Corner reticle guides */}
                  <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-forest rounded-tl"></div>
                  <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-forest rounded-tr"></div>
                  <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-forest rounded-bl"></div>
                  <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-forest rounded-br"></div>
                </div>

                {/* Giant Primary Action Button */}
                <button
                  onClick={handleStartScanner}
                  disabled={isScanning}
                  className="w-full py-3.5 rounded-2xl bg-forest hover:bg-forest-hover text-white font-bold text-sm shadow-md transition flex items-center justify-center space-x-2"
                >
                  <Camera className="w-4 h-4" />
                  <span>{isScanning ? 'Verifying QR...' : 'Open Camera & Scan'}</span>
                </button>
              </div>
            )}

            {/* TAB 2: 6-DIGIT TOTP PIN INPUT */}
            {activeTab === 'PIN' && (
              <form onSubmit={handlePinSubmit} className="max-w-sm mx-auto space-y-4 text-center">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-text-secondary block">
                    Enter the 6-digit code displayed on the classroom screen:
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={pinCode}
                    onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="• • • • • •"
                    className="w-full py-3.5 px-4 text-center tracking-[0.5em] font-mono text-2xl font-extrabold rounded-2xl bg-elevated border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-forest"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-3.5 rounded-2xl bg-forest hover:bg-forest-hover text-white font-bold text-sm shadow-md transition flex items-center justify-center space-x-2"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Verify PIN & Check In</span>
                </button>
              </form>
            )}

            {/* Security Guarantee Badges (Plain-English) */}
            <div className="flex flex-wrap items-center justify-center gap-4 pt-2 text-[11px] text-text-secondary">
              <span className="flex items-center space-x-1">
                <MapPin className="w-3.5 h-3.5 text-forest" />
                <span>In-Classroom Location Check (Within 10m)</span>
              </span>
              <span className="flex items-center space-x-1">
                <Smartphone className="w-3.5 h-3.5 text-forest" />
                <span>Verified Handset Biometrics</span>
              </span>
            </div>

          </div>
        )}

      </div>

      {/* 3. SUBJECT LEDGER & "WHAT-IF" ATTENDANCE PROJECTOR */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Subject Ledger */}
        <div className="md:col-span-2 p-6 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
          <div className="flex items-center justify-between border-b border-border/70 pb-3">
            <h3 className="text-base font-serif font-bold text-text-primary flex items-center space-x-2">
              <BookOpen className="w-4 h-4 text-forest" />
              <span>Enrolled Subjects</span>
            </h3>
            <span className="text-xs font-mono text-text-muted">5 Courses Active</span>
          </div>

          <div className="space-y-3">
            {INITIAL_SUBJECTS.map((sub) => {
              const pct = Math.round((sub.attended / sub.held) * 100);
              const isLow = pct < 75;

              return (
                <div 
                  key={sub.code}
                  className="p-3.5 rounded-2xl bg-elevated border border-border hover:bg-surface transition space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-bold text-text-primary">{sub.name}</p>
                      <p className="text-[11px] text-text-secondary">
                        {sub.code} • {sub.faculty} • {sub.room}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-lg ${
                        isLow ? 'bg-clay-bg text-clay' : 'bg-sage-bg text-forest'
                      }`}>
                        {pct}%
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-1.5 rounded-full ${isLow ? 'bg-clay' : 'bg-forest'}`}
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>

                  <div className="flex justify-between text-[10px] text-text-muted font-mono">
                    <span>Held: {sub.held}</span>
                    <span>Attended: {sub.attended}</span>
                    <span>Missed: {sub.held - sub.attended}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 1 Col: "What-If" Calculator */}
        <div className="p-6 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
          <div className="border-b border-border/70 pb-3">
            <h3 className="text-base font-serif font-bold text-text-primary flex items-center space-x-1.5">
              <TrendingUp className="w-4 h-4 text-ochre" />
              <span>Attendance Projector</span>
            </h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Simulate your final percentage.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium text-text-secondary mb-1.5">
                <span>Attend Next Classes:</span>
                <span className="font-bold text-forest font-mono">+{simulatedExtraClasses} Classes</span>
              </div>
              <input
                type="range"
                min={0}
                max={20}
                value={simulatedExtraClasses}
                onChange={(e) => setSimulatedExtraClasses(parseInt(e.target.value))}
                className="w-full accent-forest cursor-pointer"
              />
            </div>

            <div className="p-4 rounded-2xl bg-elevated border border-border text-center space-y-1">
              <p className="text-[10px] uppercase font-mono text-text-muted">Projected Score</p>
              <p className="text-2xl font-serif font-bold text-forest">{simPercentage}%</p>
              <p className="text-[11px] text-text-secondary">
                {simAttended} / {simHeld} Total Lectures
              </p>
            </div>

            <div className="p-3 rounded-xl bg-sage-bg/60 border border-sage/20 text-[11px] text-sage-text leading-relaxed">
              💡 Attending <b>+{simulatedExtraClasses} more consecutive lectures</b> keeps you well above the university 75% threshold.
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};
export default StudentHome;
