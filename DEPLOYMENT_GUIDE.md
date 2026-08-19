# 🌐 UniAttend 360 — Production Deployment & Real-World Testing Guide

This guide provides step-by-step instructions for deploying **UniAttend 360** into production with **real institutional data**, configuring a cloud database, onboarding new students/faculty, and running live classroom tests.

---

## 1. Architecture Overview

| Component | Technology | Recommended Host | Free Tier Available? |
| :--- | :--- | :--- | :--- |
| **Frontend Web App** | HTML5, Tailwind CSS, Lucide, WebAuthn | **Vercel** (`uniattend-360.vercel.app`) | ✅ 100% Free |
| **REST API Server** | FastAPI, Python 3.12/3.14, Uvicorn | **Render / Railway / Fly.io** | ✅ Free Tier |
| **Production Database** | PostgreSQL 16 | **Neon.tech / Supabase / Render** | ✅ Free Tier |
| **Security Layer** | Argon2id, RFC 6238 TOTP, W3C WebAuthn | Native Python & Web APIs | ✅ Free |

---

## 2. Cloud Database Setup (Free PostgreSQL)

### Option A: Neon.tech (Recommended - Serverless Postgres)
1. Go to [https://neon.tech](https://neon.tech) and create a free account.
2. Click **Create Project**, name it `uniattend-production`, select AWS region (e.g. `ap-south-1` Mumbai or `eu-central-1`).
3. Copy your connection string:
   ```env
   UNIATTEND_DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.ap-south-1.aws.neon.tech/neondb?sslmode=require
   ```

### Option B: Supabase (Alternative)
1. Create a project at [https://supabase.com](https://supabase.com).
2. Under **Project Settings > Database**, copy the **URI Connection String**.

---

## 3. Deploying the FastAPI REST Backend (Render.com)

1. Fork or push your repository to GitHub: `https://github.com/parthsalunke2306-dev/uniattend-360`.
2. Go to [https://render.com](https://render.com) and click **New > Web Service**.
3. Connect your GitHub repository.
4. Fill in the build & start settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.server:app --host 0.0.0.0 --port $PORT`
5. In the **Environment Variables** section, add:
   ```env
   UNIATTEND_DATABASE_URL=postgresql://... (your Neon/Supabase connection string)
   JWT_SECRET_KEY=UniAttend-Production-Enterprise-Key-2026-SuperSecret!
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   WEBAUTHN_RP_ID=uniattend-360.vercel.app
   WEBAUTHN_RP_NAME="UniAttend 360"
   WEBAUTHN_ORIGIN=https://uniattend-360.vercel.app
   ```
6. Click **Deploy**. Render will provide a live API URL like `https://uniattend-backend.onrender.com`.

---

## 4. How to Handle New Users (Whose Data Is Not in the System)

UniAttend 360 provides **3 flexible ways** to handle new people testing the application:

### Method 1: Self-Registration (Mobile Self-Sign Up)
- When new students or teachers open the link [https://uniattend-360.vercel.app](https://uniattend-360.vercel.app), they click **"Create Account"**.
- They enter:
  - **Full Name** (e.g., *Ramesh Singh*)
  - **Email** (any valid email: `@gmail.com`, `@yahoo.com`, or college domain)
  - **Roll Number / PRN** (e.g., *CHMC-DS-2024-006*)
  - **Password** (Argon2id encrypted)
- The system automatically creates their database dimension record, initializes their course attendance cards, and logs them in immediately.

### Method 2: Bulk CSV Class Roster Upload (For Coordinators)
- The Course Coordinator (Mrs. Shiji Johnson) opens the **Coordinator Dashboard**.
- Clicks **"📥 Bulk Class Roster Upload (.CSV)"**.
- Uploads a simple CSV file with columns:
  ```csv
  roll_no,full_name,email,gender
  CHMC-DS-2024-006,Ramesh Singh,ramesh.singh@gmail.com,M
  CHMC-DS-2024-007,Kavita Nair,kavita.nair@gmail.com,F
  CHMC-DS-2024-008,Siddharth Joshi,siddharth.joshi@yahoo.com,M
  ```
- All students are instantly registered with their default password `CHMC@2026!` and assigned to all subjects.

### Method 3: Instant 1-Click Guest Testing
- Testers can use the built-in 1-Click Persona profiles to test student, teacher, coordinator, or principal views in 1 second.

---

## 5. Live Classroom Testing Checklist (Step-by-Step)

When testing live in a classroom with teachers and students:

1. **Teacher Laptop / Projector**:
   - Open [https://uniattend-360.vercel.app](https://uniattend-360.vercel.app).
   - Log in as **Miss Razia Khan** (`razia.khan@chmc.edu`) or **Mr. Anshul Chimnani** (`anshul.chimnani@chmc.edu`).
   - Project the **Projector Kiosk** screen displaying the **Micro-Rotating Dynamic QR Code** and **Rolling 4-Digit Security PIN** (refreshes every 8 seconds).
   - Default geofence radius is **10.0 meters**; teachers can adjust the slider (5m–50m) to fit room size.

2. **Student Mobile Phones**:
   - Students open [https://uniattend-360.vercel.app](https://uniattend-360.vercel.app) on their mobile browsers.
   - If they have an existing account, log in with their Roll Number.
   - If new, click **Create Account** to register in 15 seconds.
   - Click **"SUBMIT LIVE CHECK-IN"**.

3. **Anti-Proxy Interception Verification**:
   - **Legitimate In-Class Scan**: GPS distance $\le 10\text{m} \implies$ **🟢 VERIFIED PRESENT**.
   - **Remote WhatsApp Photo / Proxy Attempt**: Location $> 10\text{m}$ (e.g. at home) $\implies$ **🚨 PROXY BLOCKED**.
   - **Device Sharing Attempt**: Same physical phone used for 2 different students $\implies$ **🚨 HARDWARE BINDING BLOCKED**.

---

## 6. Production Security & Data Isolation

1. **Zero Secret Leakage**: All API logs, error traces, and audit logs redact passwords, secrets, and raw biometric tokens automatically.
2. **Asymmetric Passkeys**: Biometrics stay securely on user hardware via W3C WebAuthn.
3. **Automated Defaulter Audits**: Nightly background ETL pipelines automatically aggregate attendance into gold summary marts and flag students below the 75% university threshold.
