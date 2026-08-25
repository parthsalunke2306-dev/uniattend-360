import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  Maximize2, 
  Minimize2, 
  QrCode, 
  Users, 
  ShieldAlert, 
  PlusCircle, 
  Sparkles, 
  CheckCircle2, 
  MapPin, 
  BookOpen, 
  Clock, 
  AlertTriangle 
} from 'lucide-react';
import { useToast } from './Toast';

export interface LectureSession {
  id: string;
  courseCode: string;
  courseName: string;
  room: string;
  startTime: string;
  endTime: string;
  lectureIndex: number;
  totalAllotted: number;
  topic: string;
  status: 'SCHEDULED' | 'ACTIVE' | 'PAUSED' | 'COMPLETED';
  presentCount: number;
  totalEnrolled: number;
}

const INITIAL_FACULTY_LECTURES: LectureSession[] = [
  {
    id: 'LEC-DS201-20260823-14',
    courseCode: 'DS201-DM',
    courseName: 'Data Mining (Theory)',
    room: 'E-104',
    startTime: '09:00 AM',
    endTime: '10:00 AM',
    lectureIndex: 14,
    totalAllotted: 30,
    topic: 'Frequent Itemset Mining & Apriori Algorithm',
    status: 'ACTIVE',
    presentCount: 4,
    totalEnrolled: 5,
  },
  {
    id: 'LEC-DS202-20260823-11',
    courseCode: 'DS202-BD',
    courseName: 'Big Data Architecture',
    room: 'M-113',
    startTime: '11:15 AM',
    endTime: '12:15 PM',
    lectureIndex: 11,
    totalAllotted: 30,
    topic: 'Hadoop HDFS Replication & MapReduce Scheduling',
    status: 'SCHEDULED',
    presentCount: 0,
    totalEnrolled: 5,
  },
];

export const FacultyKiosk: React.FC = () => {
  const toast = useToast();
  const [lectures, setLectures] = useState<LectureSession[]>(INITIAL_FACULTY_LECTURES);
  const [selectedId, setSelectedId] = useState<string>(INITIAL_FACULTY_LECTURES[0].id);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(8);
  const [currentPin, setCurrentPin] = useState<string>('849201');
  const [flaggedProxiesCount, setFlaggedProxiesCount] = useState<number>(1);

  const activeLecture = lectures.find((l) => l.id === selectedId) || lectures[0];

  // 8-second rotating TOTP & QR Epoch Loop
  useEffect(() => {
    if (activeLecture.status !== 'ACTIVE') return;

    const interval = setInterval(() => {
      const now = Date.now();
      const msIntoSlot = now % 8000;
      const remaining = Math.max(1, Math.ceil((8000 - msIntoSlot) / 1000));
      setSecondsRemaining(remaining);

      // Rotate PIN on slot boundary
      if (remaining === 8) {
        const randomPin = Math.floor(100000 + Math.random() * 900000).toString();
        setCurrentPin(randomPin);
      }
    }, 250);

    return () => clearInterval(interval);
  }, [activeLecture.status]);

  const updateLectureStatus = (newStatus: 'SCHEDULED' | 'ACTIVE' | 'PAUSED' | 'COMPLETED') => {
    setLectures((prev) =>
      prev.map((l) => (l.id === selectedId ? { ...l, status: newStatus } : l))
    );

    if (newStatus === 'ACTIVE') {
      toast.success('Attendance Live', 'Broadcasting dynamic QR & PIN.');
    } else if (newStatus === 'PAUSED') {
      toast.warning('Attendance Paused', 'Check-ins temporarily frozen.');
    } else if (newStatus === 'COMPLETED') {
      toast.info('Attendance Committed', `Lecture #${activeLecture.lectureIndex} finalized.`);
    }
  };

  const syllabusPercent = Math.round(
    (activeLecture.lectureIndex / activeLecture.totalAllotted) * 100
  );

  return (
    <div className={`max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 ${isFullscreen ? 'fixed inset-0 z-50 bg-canvas p-6 max-w-none overflow-y-auto' : ''}`}>
      
      {/* 1. TOP CLASSROOM CONTROLLER BAR (Step 1: Lecture Picker) */}
      <div className="p-6 rounded-3xl bg-surface border border-border shadow-organic-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Left: Scheduled Class Selector */}
        <div className="space-y-1">
          <span className="text-[11px] font-mono font-semibold text-text-muted uppercase">
            Step 1 • Select Lecture Session
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="px-3.5 py-2 rounded-xl text-xs font-bold bg-elevated border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-forest"
            >
              {lectures.map((lec) => (
                <option key={lec.id} value={lec.id}>
                  [Lec #{lec.lectureIndex}] {lec.courseName} — Room {lec.room} ({lec.status})
                </option>
              ))}
            </select>

            <span className="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-sage-bg text-forest font-semibold border border-sage/20">
              📖 {syllabusPercent}% Syllabus ({activeLecture.lectureIndex} of {activeLecture.totalAllotted})
            </span>
          </div>
        </div>

        {/* Right: Quick Action Controls & Fullscreen toggle */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-elevated hover:bg-surface border border-border text-text-secondary transition shadow-sm"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            <span>{isFullscreen ? 'Exit Projector' : 'Projector Mode'}</span>
          </button>
        </div>

      </div>

      {/* 2. THE PRESENTATION STAGE (Step 2 & 3: Clean Projector View) */}
      <div className="p-6 sm:p-10 rounded-3xl bg-surface border border-border shadow-organic-card space-y-8">
        
        {/* Stage Header Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/70 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl sm:text-2xl font-serif font-bold text-text-primary">
                {activeLecture.courseName}
              </h2>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                activeLecture.status === 'ACTIVE'
                  ? 'bg-sage-bg text-forest border border-sage/30 animate-pulse'
                  : activeLecture.status === 'PAUSED'
                  ? 'bg-ochre-bg text-ochre border border-ochre/30'
                  : 'bg-elevated text-text-muted border border-border'
              }`}>
                {activeLecture.status}
              </span>
            </div>
            <p className="text-xs text-text-secondary mt-1">
              Room {activeLecture.room} • {activeLecture.startTime} - {activeLecture.endTime} • Topic: {activeLecture.topic}
            </p>
          </div>

          {/* Location Anchor Indicator */}
          <div className="flex items-center space-x-2 text-xs font-mono text-text-secondary bg-elevated px-3 py-1.5 rounded-xl border border-border self-start">
            <MapPin className="w-3.5 h-3.5 text-forest" />
            <span>Classroom Perimeter: ±3.0m Verified</span>
          </div>
        </div>

        {/* Center: Split Screen Projector Stage */}
        {activeLecture.status === 'SCHEDULED' ? (
          <div className="py-16 text-center space-y-5 max-w-md mx-auto">
            <div className="w-16 h-16 rounded-3xl bg-sage-bg text-forest mx-auto flex items-center justify-center border border-sage/30 shadow-md">
              <Play className="w-8 h-8 fill-current ml-1" />
            </div>
            <div>
              <h3 className="text-lg font-serif font-bold text-text-primary">
                Ready to Start Lecture Attendance
              </h3>
              <p className="text-xs text-text-secondary mt-1">
                Click below to project the rotating 8-second QR code and 6-digit backup PIN onto the classroom display.
              </p>
            </div>
            <button
              onClick={() => updateLectureStatus('ACTIVE')}
              className="w-full py-4 rounded-2xl bg-forest hover:bg-forest-hover text-white font-bold text-sm shadow-md transition flex items-center justify-center space-x-2"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Start Attendance Session</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            
            {/* Left: Giant Rotating QR Code */}
            <div className="flex flex-col items-center justify-center p-6 rounded-3xl bg-canvas border border-border space-y-4">
              <div className="relative p-4 rounded-2xl bg-white border border-border shadow-sm">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=CHMC-DS-Token-${currentPin}`}
                  alt="Dynamic Rotating Attendance QR"
                  className="w-48 h-48 sm:w-56 sm:h-56 object-contain"
                />
                
                {/* 8-second countdown ring badge */}
                <div className="absolute -top-3 -right-3 flex items-center space-x-1 px-2.5 py-1 rounded-full bg-forest text-white font-mono text-xs font-bold shadow-md border-2 border-surface">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{secondsRemaining}s</span>
                </div>
              </div>
              <p className="text-xs font-medium text-text-secondary text-center">
                Refreshes automatically every 8 seconds to prevent camera replay attacks.
              </p>
            </div>

            {/* Right: Giant 6-Digit Backup PIN (Visible from back row) */}
            <div className="flex flex-col items-center justify-center p-6 rounded-3xl bg-elevated border border-border space-y-4 text-center">
              <span className="text-xs font-mono font-semibold text-text-muted uppercase">
                Fallback Classroom PIN
              </span>
              <div className="py-4 px-6 rounded-2xl bg-surface border border-border shadow-sm">
                <span className="text-4xl sm:text-5xl font-mono font-extrabold tracking-[0.25em] text-forest">
                  {currentPin}
                </span>
              </div>
              <p className="text-xs text-text-secondary max-w-xs">
                Students unable to scan the screen can type this 6-digit PIN into their mobile portal.
              </p>

              {/* Attendance Progress Count */}
              <div className="w-full pt-4 border-t border-border flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4 text-forest" />
                  <span className="text-xs font-bold text-text-primary">
                    {activeLecture.presentCount} of {activeLecture.totalEnrolled} Students Present
                  </span>
                </div>
                {flaggedProxiesCount > 0 && (
                  <span className="flex items-center space-x-1 text-[11px] font-semibold text-clay bg-clay-bg px-2.5 py-1 rounded-full border border-clay/30">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>{flaggedProxiesCount} Remote Proxy Intercepted</span>
                  </span>
                )}
              </div>
            </div>

          </div>
        )}

        {/* Bottom Bar Controls (Pause / End Session) */}
        {activeLecture.status !== 'SCHEDULED' && (
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-border">
            <div className="flex items-center space-x-3">
              {activeLecture.status === 'ACTIVE' ? (
                <button
                  onClick={() => updateLectureStatus('PAUSED')}
                  className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-ochre-bg hover:bg-ochre-bg/80 text-ochre border border-ochre/30 transition shadow-sm"
                >
                  <Pause className="w-4 h-4" />
                  <span>Pause Check-Ins</span>
                </button>
              ) : (
                <button
                  onClick={() => updateLectureStatus('ACTIVE')}
                  className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-sage-bg hover:bg-sage-bg/80 text-forest border border-sage/30 transition shadow-sm"
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>Resume Check-Ins</span>
                </button>
              )}

              <button
                onClick={() => updateLectureStatus('COMPLETED')}
                className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-clay-bg hover:bg-clay-bg/80 text-clay border border-clay/30 transition shadow-sm"
              >
                <Square className="w-4 h-4 fill-current" />
                <span>End & Commit Session</span>
              </button>
            </div>

            <p className="text-[11px] font-mono text-text-muted">
              Session ID: <span className="font-bold text-text-secondary">{activeLecture.id}</span>
            </p>
          </div>
        )}

      </div>

    </div>
  );
};
export default FacultyKiosk;
