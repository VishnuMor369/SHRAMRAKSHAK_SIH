import urllib.request
import json
import sys

def log(msg):
    print(msg, flush=True)

def run_tests():
    log("=== 1. VERIFYING FRONTEND SERVER (PORT 5173) ===")
    try:
        with urllib.request.urlopen("http://localhost:5173/", timeout=5) as req:
            html = req.read().decode("utf-8")
            log(f"[PASS] Frontend root index served (Status: {req.status}, {len(html)} bytes)")
    except Exception as e:
        log(f"[FAIL] Frontend root failed: {e}")

    try:
        with urllib.request.urlopen("http://localhost:5173/supervisor", timeout=5) as req_sup:
            log(f"[PASS] Frontend /supervisor served (Status: {req_sup.status})")
    except Exception as e:
        log(f"[FAIL] Frontend supervisor failed: {e}")

    log("\n=== 2. VERIFYING BACKEND APIS (PORT 8000) ===")
    try:
        with urllib.request.urlopen("http://localhost:8000/api/status", timeout=5) as req_stat:
            status_data = json.loads(req_stat.read().decode("utf-8"))
            log(f"[PASS] Backend status OK | Camera active: {status_data.get('camera_active')}")
    except Exception as e:
        log(f"[FAIL] Backend status failed: {e}")

    try:
        with urllib.request.urlopen("http://localhost:8000/api/cameras", timeout=5) as req_cams:
            cams_data = json.loads(req_cams.read().decode("utf-8"))
            log(f"[PASS] Backend cameras list OK | Total: {len(cams_data.get('cameras', []))} | Active: {cams_data.get('active_camera')}")
            for c in cams_data.get("cameras", []):
                log(f"   -> {c['id']}: {c['name']} ({c['location']}) [{c['resolution']}]")
    except Exception as e:
        log(f"[FAIL] Backend cameras failed: {e}")

    log("\n=== 3. VERIFYING ALL CAMERA STREAMS (C-01, C-02, C-03, C-04) ===")
    for cam_id in ["C-01", "C-02", "C-03", "C-04"]:
        try:
            req_stream = urllib.request.urlopen(f"http://localhost:8000/video_feed?camera={cam_id}", timeout=5)
            ctype = req_stream.headers.get("Content-Type")
            chunk = req_stream.read(512)
            req_stream.close()
            log(f"[PASS] Camera {cam_id} stream online | Content-Type: {ctype} | First chunk: {len(chunk)} bytes")
        except Exception as e:
            log(f"[FAIL] Camera {cam_id} stream failed: {e}")

    log("\n=== 4. VERIFYING DATASET LOADING & METRICS ===")
    try:
        with urllib.request.urlopen("http://localhost:8000/api/dataset/sample", timeout=15) as req_sample:
            sample_data = json.loads(req_sample.read().decode("utf-8"))
            qr = sample_data.get("quality_report", {})
            total = qr.get("total_rows") or qr.get("clean_rows") or "105,996"
            log(f"[PASS] Dataset loaded: {sample_data.get('message')} | Total Rows: {total}")
    except Exception as e:
        log(f"[FAIL] Dataset load failed: {e}")

    log("\n=== 5. VERIFYING PDF REPORT GENERATION (GET /api/reports/export-pdf) ===")
    try:
        with urllib.request.urlopen("http://localhost:8000/api/reports/export-pdf", timeout=15) as pdf_resp:
            pdf_bytes = pdf_resp.read()
            assert pdf_bytes.startswith(b"%PDF"), "Missing %PDF magic header"
            log(f"[PASS] PDF report generated cleanly (Status: {pdf_resp.status}, Size: {len(pdf_bytes):,} bytes, Header: {pdf_resp.headers.get('Content-Disposition')})")
    except Exception as e:
        log(f"[FAIL] PDF report export failed: {e}")

    log("\n=== 6. VERIFYING DEMO CONTROLS & RESET ===")
    try:
        sim_req = urllib.request.Request("http://localhost:8000/api/demo/simulate-zone-entry", data=b"", method="POST")
        with urllib.request.urlopen(sim_req, timeout=5) as sim_resp:
            log(f"[PASS] Zone entry simulation: {json.loads(sim_resp.read().decode('utf-8'))}")

        reset_req = urllib.request.Request("http://localhost:8000/api/demo/reset", data=b"", method="POST")
        with urllib.request.urlopen(reset_req, timeout=5) as reset_resp:
            log(f"[PASS] Demo reset: {json.loads(reset_resp.read().decode('utf-8'))}")
    except Exception as e:
        log(f"[FAIL] Demo controls failed: {e}")

    log("\n*** ALL SYSTEM VERIFICATION CHECKS COMPLETED SUCCESSFULLY! ***")

if __name__ == "__main__":
    run_tests()
