import React, { useState } from 'react';
import { 
  School, 
  Users, 
  FileSpreadsheet, 
  FileText, 
  ShieldCheck, 
  Search, 
  UserPlus, 
  Trash2, 
  RefreshCw, 
  Download, 
  UploadCloud, 
  CheckCircle2, 
  AlertTriangle,
  Radio,
  Clock
} from 'lucide-react';
import { useToast } from './Toast';

export interface InstitutionalStudent {
  rollNo: string;
  name: string;
  department: string;
  semester: number;
  attendancePct: number;
  deviceStatus: 'BOUND' | 'UNBOUND';
  status: 'ACTIVE' | 'FLAGGED';
}

const INITIAL_STUDENT_DIRECTORY: InstitutionalStudent[] = [
  { rollNo: 'CHMC-DS-2024-001', name: 'Alex Chen', department: 'Data Science', semester: 3, attendancePct: 94, deviceStatus: 'BOUND', status: 'ACTIVE' },
  { rollNo: 'CHMC-DS-2024-002', name: 'Aarav Sharma', department: 'Data Science', semester: 3, attendancePct: 88, deviceStatus: 'BOUND', status: 'ACTIVE' },
  { rollNo: 'CHMC-DS-2024-003', name: 'Priya Patel', department: 'Data Science', semester: 3, attendancePct: 92, deviceStatus: 'BOUND', status: 'ACTIVE' },
  { rollNo: 'CHMC-DS-2024-004', name: 'Rohan Gupta', department: 'Data Science', semester: 3, attendancePct: 62, deviceStatus: 'BOUND', status: 'FLAGGED' },
  { rollNo: 'CHMC-DS-2024-005', name: 'Ananya Verma', department: 'Data Science', semester: 3, attendancePct: 96, deviceStatus: 'BOUND', status: 'ACTIVE' },
];

export const AdminPortal: React.FC = () => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'LIVE' | 'STUDENTS' | 'REPORTS' | 'AUDIT'>('STUDENTS');
  const [searchTerm, setSearchTerm] = useState('');
  const [students, setStudents] = useState<InstitutionalStudent[]>(INITIAL_STUDENT_DIRECTORY);
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [newRollNo, setNewRollNo] = useState('');
  const [newName, setNewName] = useState('');
  const [newDept, setNewDept] = useState('Data Science');

  const filteredStudents = students.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.rollNo.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleEnrollSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRollNo.trim() || !newName.trim()) {
      toast.error('Missing Fields', 'Roll No and Name are required.');
      return;
    }

    const newStudent: InstitutionalStudent = {
      rollNo: newRollNo.trim().toUpperCase(),
      name: newName.trim(),
      department: newDept,
      semester: 3,
      attendancePct: 100,
      deviceStatus: 'UNBOUND',
      status: 'ACTIVE',
    };

    setStudents([newStudent, ...students]);
    setIsEnrollModalOpen(false);
    setNewRollNo('');
    setNewName('');
    toast.success('Student Enrolled', `${newStudent.name} (${newStudent.rollNo}) provisioned.`);
  };

  const handleExpelStudent = (rollNo: string, name: string) => {
    const conf = window.confirm(`⚠️ PERMANENT EXPULSION CONFIRMATION\n\nAre you sure you want to expel and delete student ${name} (${rollNo})?\n\nThis will purge all credentials, passkeys, and enrollment records.`);
    if (conf) {
      setStudents(students.filter((s) => s.rollNo !== rollNo));
      toast.info('Student Expelled', `${name} records expunged from institutional database.`);
    }
  };

  const handleResetDevice = (rollNo: string, name: string) => {
    setStudents(
      students.map((s) => (s.rollNo === rollNo ? { ...s, deviceStatus: 'UNBOUND' } : s))
    );
    toast.success('Device Unbound', `${name} can link a new handset.`);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      
      {/* 1. MANAGEMENT HEADER & TAB CONTROLLER */}
      <div className="p-6 rounded-3xl bg-surface border border-border shadow-organic-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl sm:text-2xl font-serif font-bold text-text-primary">
              Principal & Academic Administration
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-sage-bg text-forest border border-sage/20">
              Super-Admin Tier
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Smt. C.H.M. College • Central Institutional Governance & Cross-Department Ledger
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center p-1 bg-elevated rounded-2xl border border-border overflow-x-auto">
          <button
            onClick={() => setActiveTab('LIVE')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === 'LIVE'
                ? 'bg-surface text-forest shadow-sm border border-border/60'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Live Classes</span>
          </button>

          <button
            onClick={() => setActiveTab('STUDENTS')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === 'STUDENTS'
                ? 'bg-surface text-forest shadow-sm border border-border/60'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Student Directory</span>
          </button>

          <button
            onClick={() => setActiveTab('REPORTS')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === 'REPORTS'
                ? 'bg-surface text-forest shadow-sm border border-border/60'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Reports & Exports</span>
          </button>

          <button
            onClick={() => setActiveTab('AUDIT')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === 'AUDIT'
                ? 'bg-surface text-forest shadow-sm border border-border/60'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Audit Ledger</span>
          </button>
        </div>
      </div>

      {/* 2. TAB 1: TODAY'S LIVE CLASSES */}
      {activeTab === 'LIVE' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
            <div className="flex items-center justify-between border-b border-border/70 pb-3">
              <div>
                <p className="text-xs font-bold text-text-primary">Data Mining (Theory) • Room E-104</p>
                <p className="text-[11px] text-text-secondary">Miss Razia Khan • S.Y. B.Sc. Data Science</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-sage-bg text-forest border border-sage/30 animate-pulse">
                ACTIVE
              </span>
            </div>
            <div className="flex justify-between text-xs font-mono text-text-secondary">
              <span>Attendance: 4 / 5 (80%)</span>
              <span>Geofence: Locked (±3m)</span>
            </div>
          </div>

          <div className="p-6 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
            <div className="flex items-center justify-between border-b border-border/70 pb-3">
              <div>
                <p className="text-xs font-bold text-text-primary">Big Data Architecture • Room M-113</p>
                <p className="text-[11px] text-text-secondary">Prof. Amit Sharma • S.Y. B.Sc. Data Science</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-elevated text-text-muted border border-border">
                SCHEDULED (11:15 AM)
              </span>
            </div>
            <div className="flex justify-between text-xs font-mono text-text-secondary">
              <span>Enrolled: 5 Students</span>
              <span>Classroom: M-113</span>
            </div>
          </div>
        </div>
      )}

      {/* 3. TAB 2: STUDENT DIRECTORY & DIRECT ENROLLMENT */}
      {activeTab === 'STUDENTS' && (
        <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card space-y-6">
          
          {/* Action Bar: Search & Enroll Button */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:max-w-md">
              <Search className="w-4 h-4 text-text-muted absolute left-3.5 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by student name or roll number..."
                className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-elevated border border-border text-xs font-medium text-text-primary focus:outline-none focus:ring-2 focus:ring-forest"
              />
            </div>

            <button
              onClick={() => setIsEnrollModalOpen(true)}
              className="w-full sm:w-auto px-4 py-2.5 rounded-2xl bg-forest hover:bg-forest-hover text-white text-xs font-bold shadow-md transition flex items-center justify-center space-x-1.5"
            >
              <UserPlus className="w-4 h-4" />
              <span>Direct Enroll Student</span>
            </button>
          </div>

          {/* Student Roster Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border/80 text-text-muted font-mono text-[11px]">
                  <th className="pb-3 font-semibold">Student Name & Roll No</th>
                  <th className="pb-3 font-semibold">Department</th>
                  <th className="pb-3 font-semibold">Attendance</th>
                  <th className="pb-3 font-semibold">Device Lock</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredStudents.map((s) => (
                  <tr key={s.rollNo} className="hover:bg-elevated/50 transition">
                    <td className="py-3">
                      <p className="font-bold text-text-primary">{s.name}</p>
                      <p className="font-mono text-[11px] text-text-secondary">{s.rollNo}</p>
                    </td>
                    <td className="py-3 text-text-secondary">{s.department} (Sem {s.semester})</td>
                    <td className="py-3">
                      <span className={`font-mono font-bold px-2 py-0.5 rounded-md ${
                        s.attendancePct >= 75 ? 'bg-sage-bg text-forest' : 'bg-clay-bg text-clay'
                      }`}>
                        {s.attendancePct}%
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded-md font-mono text-[10px] font-semibold ${
                        s.deviceStatus === 'BOUND' ? 'bg-sage-bg text-forest' : 'bg-ochre-bg text-ochre'
                      }`}>
                        {s.deviceStatus}
                      </span>
                    </td>
                    <td className="py-3 text-right space-x-2">
                      <button
                        onClick={() => handleResetDevice(s.rollNo, s.name)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-elevated hover:bg-surface border border-border text-text-secondary transition"
                        title="Reset Biometric Lock"
                      >
                        Reset Lock
                      </button>
                      <button
                        onClick={() => handleExpelStudent(s.rollNo, s.name)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-clay-bg hover:bg-clay-bg/80 text-clay border border-clay/30 transition"
                        title="Expel Student"
                      >
                        Expel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      )}

      {/* 4. TAB 3: REPORTS & EXPORTS */}
      {activeTab === 'REPORTS' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
            <div className="w-10 h-10 rounded-2xl bg-sage-bg text-forest flex items-center justify-center border border-sage/30">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-serif font-bold text-text-primary">
                Institutional Master Attendance Report
              </h3>
              <p className="text-xs text-text-secondary mt-1">
                Download verified semester Excel ledger with per-lecture breakdown, biometric hashes, and geofence timestamps.
              </p>
            </div>
            <button
              onClick={() => toast.success('Excel Report Exported', 'Master attendance spreadsheet saved.')}
              className="w-full py-3 rounded-2xl bg-forest hover:bg-forest-hover text-white text-xs font-bold shadow-md transition flex items-center justify-center space-x-2"
            >
              <Download className="w-4 h-4" />
              <span>Download Master Excel (.xlsx)</span>
            </button>
          </div>

          <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
            <div className="w-10 h-10 rounded-2xl bg-clay-bg text-clay flex items-center justify-center border border-clay/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-serif font-bold text-text-primary">
                Defaulter Warning Notices (PDF)
              </h3>
              <p className="text-xs text-text-secondary mt-1">
                Generate official college warning letters with digital signature for students with attendance below 75%.
              </p>
            </div>
            <button
              onClick={() => toast.success('PDF Letters Generated', 'Warning notices exported for defaulters.')}
              className="w-full py-3 rounded-2xl bg-elevated hover:bg-surface border border-border text-text-primary text-xs font-bold shadow-sm transition flex items-center justify-center space-x-2"
            >
              <Download className="w-4 h-4 text-clay" />
              <span>Export Defaulter Notices (.pdf)</span>
            </button>
          </div>
        </div>
      )}

      {/* 5. TAB 4: IMMUTABLE AUDIT LOGS */}
      {activeTab === 'AUDIT' && (
        <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-organic-card space-y-4">
          <div className="border-b border-border/70 pb-3">
            <h3 className="text-base font-serif font-bold text-text-primary">
              Institutional Security Audit Ledger
            </h3>
            <p className="text-xs text-text-secondary">
              Immutable log of all super-admin provisions, device resets, and blocked proxy attempts.
            </p>
          </div>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="p-3 rounded-xl bg-elevated border border-border flex items-center justify-between">
              <div>
                <span className="font-bold text-clay">[PROXY_INTERCEPTED]</span>
                <span className="text-text-primary ml-2">Priya Patel (003) — 1.85 km away from Room E-104</span>
              </div>
              <span className="text-[10px] text-text-muted">09:04:12</span>
            </div>

            <div className="p-3 rounded-xl bg-elevated border border-border flex items-center justify-between">
              <div>
                <span className="font-bold text-forest">[PASSKEY_REGISTERED]</span>
                <span className="text-text-primary ml-2">Alex Chen (001) — FIDO2 Hardware Passkey Linked</span>
              </div>
              <span className="text-[10px] text-text-muted">08:58:20</span>
            </div>

            <div className="p-3 rounded-xl bg-elevated border border-border flex items-center justify-between">
              <div>
                <span className="font-bold text-ochre">[LECTURE_STARTED]</span>
                <span className="text-text-primary ml-2">Data Mining #14 — Miss Razia Khan (Room E-104)</span>
              </div>
              <span className="text-[10px] text-text-muted">09:00:00</span>
            </div>
          </div>
        </div>
      )}

      {/* DIRECT ENROLLMENT MODAL */}
      {isEnrollModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface rounded-3xl border border-border shadow-organic-card max-w-md w-full p-6 space-y-5 animate-in fade-in">
            <div>
              <h3 className="text-lg font-serif font-bold text-text-primary">
                Direct Expedited Student Enrollment
              </h3>
              <p className="text-xs text-text-secondary">
                Principal Super-Admin Authority • Immediate Roster Ingestion
              </p>
            </div>

            <form onSubmit={handleEnrollSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-text-secondary block mb-1">Student Roll Number</label>
                <input
                  type="text"
                  value={newRollNo}
                  onChange={(e) => setNewRollNo(e.target.value)}
                  placeholder="e.g. CHMC-DS-2024-006"
                  className="w-full px-3 py-2 rounded-xl text-xs bg-elevated border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-forest font-mono uppercase"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-text-secondary block mb-1">Full Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Ramesh Singh"
                  className="w-full px-3 py-2 rounded-xl text-xs bg-elevated border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-forest"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-text-secondary block mb-1">Department</label>
                <select
                  value={newDept}
                  onChange={(e) => setNewDept(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl text-xs bg-elevated border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-forest"
                >
                  <option value="Data Science">Department of Data Science (DS)</option>
                  <option value="Computer Science">Department of Computer Science (CS)</option>
                  <option value="Information Technology">Department of Information Technology (IT)</option>
                  <option value="Artificial Intelligence">Department of AI & Data Science (AI-DS)</option>
                </select>
              </div>

              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEnrollModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-elevated hover:bg-surface border border-border text-text-secondary transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 rounded-xl text-xs font-bold bg-forest hover:bg-forest-hover text-white shadow-md transition"
                >
                  Enroll Student
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
export default AdminPortal;
