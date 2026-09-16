# 🛡️ SHRAMRAKSHAK: AI-Powered SIF Intelligence for Safer Workplaces

> **Internal College Round MVP / Live Demonstration**  
> *Smart India Hackathon (SIH)*

SHRAMRAKSHAK is an AI-powered industrial safety observation and intervention system. It detects visible workplace safety violations (such as failure to wear a mandatory hard hat/PPE) via CCTV/webcam, automatically dispatches critical alerts with a strict 20-second supervisor response SLA, and provides mobile-responsive field intervention tracking.

---

## 🏗️ System Architecture

```
[ Laptop Webcam ] ──> [ OpenCV + YOLO Engine ]
                             │ (Debounce 1.5s)
                             ▼
                    [ FastAPI State Machine ] 
                    (0.0.0.0:8000 + WebSockets)
                      │                  │
         Real-time    │                  │  LAN Network
          Sync        ▼                  ▼  (Wi-Fi / Hotspot)
     [ Laptop HSE Dashboard ]     [ Mobile Supervisor Page ]
      (http://localhost:5173)      (http://<LAN-IP>:5173/supervisor)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.11)
- **Node.js v18+** and `npm`
- Laptop with webcam (or fallback simulation mode)
- Smartphone connected to the **same Wi-Fi** (or laptop mobile hotspot)

---

### Step 1: Install Dependencies

#### Backend:
Open PowerShell or Command Prompt in the project root:
```powershell
pip install fastapi "uvicorn[standard]" websockets opencv-python ultralytics qrcode pillow pydantic
```

#### Frontend:
Open a terminal in the `frontend` folder:
```powershell
cd frontend
npm.cmd install
```

---

### Step 2: Run the Application

#### Terminal 1 — Start the Backend:
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*The backend will automatically detect your active Wi-Fi LAN IP and print it to the console.*

#### Terminal 2 — Start the Frontend:
```powershell
cd frontend
npm.cmd run dev
```
*The Vite frontend will bind to `0.0.0.0:5173`, making it accessible across your local network.*

---

### Step 3: Access the Dashboards

1. **Laptop HSE Dashboard**:  
   Open your browser to:  
   👉 **`http://localhost:5173`**

2. **Mobile Supervisor Page**:  
   - Click the **"Mobile Supervisor: [LAN-IP]"** button in the dashboard header to view the **QR Code**.
   - Scan the QR code using your smartphone camera app (or open `http://<YOUR-LAPTOP-IP>:5173/supervisor`).

---

## 🎬 Live Presentation Script (Demo Flow)

Follow this exact sequence during your college hackathon evaluation:

### Primary Flow: Live Detection & Resolution
1. **Show Dashboard**: Open `http://localhost:5173` on laptop. Point out the header (*SHRAMRAKSHAK*, *SYSTEM ONLINE*).
2. **Show Live Feed**: Point to Camera C-01 live feed. Person is detected in the zone.
3. **Trigger Violation**: Sit or stand in front of webcam **without a helmet**.
4. **AI Debounce & Alert**: Within ~1.5s, the system detects `NO HELMET`, turns status to **CRITICAL RED**, and generates Alert `ALT-...`.
5. **Stage 1 (20s Response Timer)**: The 20-second response countdown begins immediately.
6. **Open Mobile Page**: Show the alert appearing in real-time on the phone at `/supervisor`.
7. **Supervisor Acknowledges**: Tap **`[ I'M RESPONDING ]`** on the phone before the 20s timer reaches zero.
8. **Stage 2 (Action Timer)**: Timer switches to 60-second action window on both laptop and phone.
9. **Don Helmet**: Put on a hard hat/helmet (or yellow/bright cap).
10. **Supervisor Resolves**: Tap **`[ FIXED / RESOLVED ]`** on phone.
11. **Verification**: Dashboard turns **GREEN** (`SAFE — Helmet Detected`), confirming human-in-the-loop closure.

---

### Secondary Flow: Automatic Escalation Test
1. Click **`[ RESET DEMO ]`** on the dashboard.
2. Trigger violation (either via webcam or click **`[ SIMULATE NO HELMET ]`**).
3. Do **NOT** click "I'M RESPONDING" on phone.
4. Let the 20-second countdown expire.
5. Both laptop and phone immediately flash:
   **`🚨 RESPONSE TIME EXCEEDED — Escalated to: HSE Manager / Control Room`**
6. Explain to judges how this automated escalation prevents unattended SIF potentials.

---

## 🛠️ Presentation Failsafe: Demo Mode

If stage lighting or webcam angles make camera detection unreliable during the presentation:
- Scroll to the bottom of the laptop dashboard to find the **Presentation Demo Controls**:
  - **`[ ⚡ SIMULATE NO HELMET ]`**: Manually fires the violation alert and triggers the 10-second timer.
  - **`[ 🛡️ SIMULATE SAFE ]`**: Restores the safe visual indicator.
  - **`[ 🔄 RESET DEMO ]`**: Clears active alert and resets all timers.

---

## 🔍 Troubleshooting & FAQs

### 1. Phone cannot connect to `http://<IP>:5173/supervisor`
- **Ensure same network**: Make sure your phone and laptop are connected to the exact same Wi-Fi router (or connect phone to your laptop's Mobile Hotspot).
- **Windows Firewall**: If Windows asks to allow Node.js or Python through Private Networks, click **Allow**. Alternatively, in Windows PowerShell (Admin):
  ```powershell
  New-NetFirewallRule -DisplayName "SIH Demo Frontend" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
  New-NetFirewallRule -DisplayName "SIH Demo Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
  ```

### 2. Webcam permission or camera in use
- Close any other apps using the camera (Zoom, Teams, Camera app, Chrome tabs).
- If the physical camera cannot be accessed, ShramRakshak automatically displays a high-clarity synthetic CCTV stream so the demo never crashes.

### 3. How to check Laptop LAN IP manually
- In PowerShell, run `ipconfig`. Look for `IPv4 Address` under your active Wi-Fi adapter (typically `192.168.x.x` or `10.x.x.x`).

---

## 📋 Technology Stack
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Web Audio API
- **Backend**: Python 3.11, FastAPI, Uvicorn, WebSockets, Pydantic
- **Computer Vision**: OpenCV (DirectShow), Ultralytics YOLOv8, Color/Head PPE heuristics
- **Protocols**: WebSocket duplex state sync, HTTP REST, MJPEG stream
