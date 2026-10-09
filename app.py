"""
ICAI Tamil Nadu Seat Availability Live Dashboard Backend
Framework: Flask
Target: Strictly Tamil Nadu ICAI Branches & Advanced Courses
Features:
- Targeted City & Course Scanning (Scan only Chennai in ~3s, or all TN)
- Fast In-Memory Cache with CSV Persistence
- Real-Time JSON REST API
"""

import os
import csv
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates") if os.path.exists(os.path.join(BASE_DIR, "templates")) else BASE_DIR

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Strictly Tamil Nadu POUs
TN_POUS = {
    "138": "CHENNAI",
    "106": "COIMBATORE",
    "268": "Chengalpattu",
    "252": "ERODE",
    "115": "KUMBAKONAM",
    "116": "MADURAI",
    "124": "SALEM",
    "251": "SIRC",
    "125": "SIVAKASI",
    "127": "TIRUNELVELI",
    "129": "TIRUPUR",
    "132": "Thoothukudi",
    "126": "Tiruchirapalli",
    "134": "VELLORE"
}

TARGET_COURSES = [
    {"id": "45", "name": "Advanced (ICITSS) MCS Course"},
    {"id": "48", "name": "AICITSS - Advanced Information Technology"},
    {"id": "49", "name": "Advanced (ICITSS) MCS Course - Weekend"}
]

DATA_FILE = os.path.join(BASE_DIR, "icai_tamilnadu_batches.csv")

# Global state
data_lock = threading.Lock()
cached_batches: List[Dict[str, Any]] = []
last_scanned_time: str = "Never"
is_scanning: bool = False
currently_scanning_target: str = ""

def load_cached_data():
    global cached_batches, last_scanned_time
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                with data_lock:
                    cached_batches = reader
                    if reader and "scraped_at" in reader[0]:
                        last_scanned_time = reader[0]["scraped_at"]
        except Exception as e:
            print(f"Error loading {DATA_FILE}: {e}")

def run_tamilnadu_scan(target_city_name=None, target_course_name=None):
    global cached_batches, last_scanned_time, is_scanning, currently_scanning_target
    
    # 1. Determine target POUs
    pous_to_scan = {}
    if target_city_name and target_city_name.upper() != "ALL":
        for pid, pname in TN_POUS.items():
            if pname.upper() == target_city_name.upper():
                pous_to_scan[pid] = pname
    if not pous_to_scan:
        pous_to_scan = TN_POUS

    # 2. Determine target courses
    courses_to_scan = []
    if target_course_name and target_course_name.upper() != "ALL":
        for c in TARGET_COURSES:
            if c["name"].upper() == target_course_name.upper() or c["id"] == target_course_name or target_course_name.upper() in c["name"].upper():
                courses_to_scan.append(c)
    if not courses_to_scan:
        courses_to_scan = TARGET_COURSES

    with data_lock:
        if is_scanning:
            return False
        is_scanning = True
        currently_scanning_target = target_city_name if target_city_name and target_city_name != "ALL" else "All Tamil Nadu"

    try:
        scraper = ICAIScraperPOC(request_timeout=15, delay_between_requests=1.2)
        ok, _, hidden = scraper.get_initial_page()
        if not ok:
            return False

        first_course = courses_to_scan[0]["id"] if courses_to_scan else "45"
        ok_reg, _, reg_hidden, _ = scraper.trigger_region_postback("4", hidden, first_course)
        if not ok_reg:
            return False

        fresh_batches = []
        current_hidden = reg_hidden

        for pou_id, pou_name in sorted(pous_to_scan.items(), key=lambda x: x[1]):
            for course in courses_to_scan:
                ok_fetch, batches, _ = scraper.fetch_batch_list("4", pou_id, course["id"], current_hidden)
                if ok_fetch and batches:
                    fresh_batches.extend(batches)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with data_lock:
            if len(pous_to_scan) < len(TN_POUS):
                # Targeted scan: update only the scanned city and courses
                scanned_pous = set(p.upper() for p in pous_to_scan.values())
                scanned_courses = set(c["name"].upper() for c in courses_to_scan)

                retained = [
                    b for b in cached_batches
                    if not (b.get("pou_name", "").upper() in scanned_pous and b.get("course", "").upper() in scanned_courses)
                ]
                cached_batches = retained + fresh_batches
            else:
                # Full scan: replace all
                cached_batches = fresh_batches

            last_scanned_time = timestamp

            # Save full dataset to CSV
            with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "scraped_at", "pou_name", "course", "available_seats", "from_date",
                    "to_date", "batch_time", "batch_no", "open_for", "queried_pou_id", "queried_course_id"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for b in cached_batches:
                    row = dict(b)
                    if "scraped_at" not in row or not row["scraped_at"]:
                        row["scraped_at"] = timestamp
                    writer.writerow(row)

        return True
    finally:
        with data_lock:
            is_scanning = False
            currently_scanning_target = ""

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    candidates = [
        os.path.join(BASE_DIR, "templates", "index.html"),
        os.path.join(BASE_DIR, "index.html"),
        "templates/index.html",
        "index.html",
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    
    # Debug directory if missing
    files_list = []
    for r, d, fs in os.walk(BASE_DIR):
        for f in fs:
            files_list.append(os.path.relpath(os.path.join(r, f), BASE_DIR))
    return f"<h3>index.html not found</h3><p>Server files: {files_list}</p>", 404

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return f"<h1>Server Error</h1><pre style='background:#f1f5f9;padding:15px;border-radius:8px;'>{traceback.format_exc()}</pre>", 500

@app.route("/api/batches")
def get_batches():
    city = request.args.get("city", "").strip().upper()
    course = request.args.get("course", "").strip().upper()
    available_only = request.args.get("available_only", "false").lower() == "true"
    search_query = request.args.get("q", "").strip().lower()

    with data_lock:
        batches = list(cached_batches)
        last_time = last_scanned_time
        scanning = is_scanning
        scanning_target = currently_scanning_target

    filtered = []
    total_open_seats = 0
    cities_with_open_seats = set()

    for b in batches:
        # Calculate stats across all TN batches
        try:
            seats = int(b.get("available_seats", 0))
        except ValueError:
            seats = 0

        if seats > 0:
            total_open_seats += seats
            cities_with_open_seats.add(b.get("pou_name", ""))

        # City filter
        pou_name_clean = b.get("pou_name", "").strip().upper()
        if city and city != "ALL" and pou_name_clean != city:
            continue
        # Course filter
        course_clean = b.get("course", "").strip().upper()
        if course and course != "ALL" and course_clean != course:
            continue
        # Available only filter
        if available_only and seats <= 0:
            continue
        # Text search
        if search_query:
            combined = f"{b.get('pou_name', '')} {b.get('course', '')} {b.get('batch_no', '')} {b.get('from_date', '')}".lower()
            if search_query not in combined:
                continue

        filtered.append(b)

    # Sort: open seats first, then city name
    filtered.sort(key=lambda x: (
        0 if int(x.get("available_seats", 0) if x.get("available_seats", "").isdigit() else 0) > 0 else 1,
        x.get("pou_name", ""),
        x.get("course", "")
    ))

    # Calculate filtered open seats
    filtered_open_seats = sum(int(b.get("available_seats", 0)) for b in filtered if b.get("available_seats", "").isdigit())

    return jsonify({
        "batches": filtered,
        "stats": {
            "total_batches": len(batches),
            "filtered_count": len(filtered),
            "total_available_seats": total_open_seats,
            "filtered_open_seats": filtered_open_seats,
            "cities_with_open_seats": len(cities_with_open_seats),
            "last_scanned": last_time,
            "is_scanning": scanning,
            "scanning_target": scanning_target
        }
    })

@app.route("/api/scan", methods=["POST"])
def trigger_scan():
    data = request.get_json(silent=True) or {}
    city = data.get("city") or request.args.get("city", "")
    course = data.get("course") or request.args.get("course", "")

    global is_scanning
    with data_lock:
        if is_scanning:
            return jsonify({
                "status": "already_scanning",
                "message": f"A scan for {currently_scanning_target or 'Tamil Nadu'} is already running."
            })

    target_desc = city if city and city != "ALL" else "all Tamil Nadu cities"
    t = threading.Thread(target=run_tamilnadu_scan, args=(city, course))
    t.daemon = True
    t.start()

    return jsonify({
        "status": "started",
        "target": target_desc,
        "message": f"Targeted scan for {target_desc} started."
    })

def background_periodic_scanner(interval_seconds=60):
    """Automated 24/7 background worker: refreshes all Tamil Nadu batches every 1 minute."""
    time.sleep(15)  # Initial grace period after startup
    while True:
        try:
            with data_lock:
                already_scanning = is_scanning
            if not already_scanning:
                print("Running automated 24/7 background scan for all Tamil Nadu branches...")
                run_tamilnadu_scan()
        except Exception as e:
            print(f"Error in background scanner: {e}")
        time.sleep(interval_seconds)

def start_background_scanner():
    worker = threading.Thread(target=background_periodic_scanner, daemon=True)
    worker.start()

# Load cached data and start background worker on app initialization
load_cached_data()
start_background_scanner()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting ICAI Tamil Nadu Seat Availability Live Dashboard on http://localhost:{port} ...")
    app.run(host="0.0.0.0", port=port, debug=False)
