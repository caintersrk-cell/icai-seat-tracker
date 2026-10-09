# 🌐 100% Free Cloud Website Hosting Guide

Host your **ICAI Tamil Nadu Live Web Dashboard** online **24/7 for $0 (100% free)**.
You will get a public website link (e.g. `https://icai-seat-tracker.onrender.com`) that you can open from your phone or PC anytime.
It runs **completely in the cloud** even if your laptop is **shut down, asleep, or disconnected from the internet**.

**Zero emails are sent — only the live website is updated automatically every 1 minute.**

---

## 🚀 3-Minute Free Deployment Steps on Render.com

Render is a modern cloud hosting platform with a **100% Free Tier** ($0, no credit card required).

### Step 1: Create a Free GitHub Repository
1. Open [https://github.com](https://github.com) (sign in or create a free account).
2. Click the **`+`** icon at top-right → **New repository**.
3. Name it: `icai-seat-tracker`.
4. Choose **Public** or **Private** (both are supported).
5. Click **Create repository**.

---

### Step 2: Upload Your Website Files
1. On your new repository page, click **"uploading an existing file"**.
2. Upload the files from this folder (`C:\Users\srira\.gemini\antigravity\scratch\icai_scraper_poc`):
   - `app.py`
   - `templates/index.html`
   - `icai_poc_scraper.py`
   - `icai_tamilnadu_batches.csv`
   - `requirements.txt`
   - `Procfile`
3. Click **Commit changes**.

---

### Step 3: Launch Free Web Service on Render
1. Go to [https://render.com](https://render.com).
2. Click **Get Started for Free** and choose **GitHub** to sign in with your GitHub account.
3. On your Render dashboard, click **New +** (top-right) → **Web Service**.
4. Select your `icai-seat-tracker` repository and click **Connect**.
5. Configure these 3 fields (Render usually auto-detects them):
   - **Name**: `icai-seat-tracker`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
   - **Instance Type**: Select **Free ($0/month)**.
6. Click **Deploy Web Service** (at the bottom).

---

### 🎉 You're Done!
In about 1 minute, Render will build your site and give you a permanent live URL:
👉 **`https://icai-seat-tracker.onrender.com`**

- **Open on your Mobile Phone**: Bookmark the link on your phone browser for instant access anywhere.
- **24/7 Cloud Background Monitoring**: The server automatically queries ICAI every 1 minute in the cloud to update seat availability.
- **On-Demand Live Scanning**: You can click **"Scan Coimbatore Only"** or **"Scan All TN Cities"** right from your phone browser to get live data in ~3 seconds.
- **No Laptop Needed**: Your laptop can be completely powered off.
- **No Emails**: Strictly updates the website.
