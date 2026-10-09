"""
ICAI Multi-City Seat Availability Scraper - Proof of Concept (POC)
Target: https://www.icaionlineregistration.org/launchbatchdetail.aspx
"""

import time
import csv
import logging
from typing import List, Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("icai_scraper")

BASE_URL = "https://www.icaionlineregistration.org/launchbatchdetail.aspx"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.icaionlineregistration.org",
    "Referer": "https://www.icaionlineregistration.org/launchbatchdetail.aspx"
}

class ICAIScraperPOC:
    def __init__(self, request_timeout: int = 15, delay_between_requests: float = 2.0):
        self.timeout = request_timeout
        self.delay = delay_between_requests
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _extract_hidden_fields(self, html: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        fields = {}
        for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
            tag = soup.find("input", id=name)
            if tag and tag.get("value") is not None:
                fields[name] = tag["value"]
            else:
                fields[name] = ""
        return fields

    def get_initial_page(self) -> Tuple[bool, str, Dict[str, str]]:
        """Step 1: Initial GET to obtain session cookies and base hidden state."""
        logger.info("Step 1: Requesting initial page...")
        try:
            resp = self.session.get(BASE_URL, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(f"GET failed with HTTP status {resp.status_code}")
                return False, resp.text, {}
            hidden_fields = self._extract_hidden_fields(resp.text)
            return True, resp.text, hidden_fields
        except Exception as e:
            logger.error(f"Exception during GET: {e}")
            return False, str(e), {}

    def trigger_region_postback(self, region_id: str, hidden_fields: Dict[str, str], course_id: Optional[str] = None) -> Tuple[bool, str, Dict[str, str], Dict[str, str]]:
        """
        Step 2: Trigger ddl_reg AutoPostBack to populate ddlPou.
        Returns (success, html, updated_hidden_fields, available_pous_dict)
        """
        logger.info(f"Step 2: Triggering AutoPostBack for Region ID: {region_id}")
        data = {
            "__EVENTTARGET": "ddl_reg",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "__VIEWSTATE": hidden_fields.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": hidden_fields.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": hidden_fields.get("__EVENTVALIDATION", ""),
            "ddl_reg": region_id,
        }
        if course_id:
            data["ddl_course"] = course_id

        try:
            time.sleep(self.delay)
            resp = self.session.post(BASE_URL, data=data, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(f"Postback for Region {region_id} failed with HTTP status {resp.status_code}")
                return False, resp.text, {}, {}

            soup = BeautifulSoup(resp.text, "html.parser")
            new_hidden_fields = self._extract_hidden_fields(resp.text)

            # Extract available POUs in this region for verification
            pou_options = {}
            pou_select = soup.find("select", id="ddlPou")
            if pou_select:
                for opt in pou_select.find_all("option"):
                    val = opt.get("value", "").strip()
                    text = opt.get_text(strip=True)
                    if val and val != "Select":
                        pou_options[val] = text

            logger.info(f"Region {region_id} loaded successfully with {len(pou_options)} POUs.")
            return True, resp.text, new_hidden_fields, pou_options
        except Exception as e:
            logger.error(f"Exception during Region postback: {e}")
            return False, str(e), {}, {}

    def fetch_batch_list(self, region_id: str, pou_id: str, course_id: str, hidden_fields: Dict[str, str]) -> Tuple[bool, Optional[List[Dict[str, str]]], str]:
        """
        Step 3: Submit btn_getlist='Get List' with selected Region, POU, Course and fresh hidden fields.
        Returns (success, list_of_batch_dicts_or_None, status_or_error_msg)
        """
        logger.info(f"Step 3: Submitting Get List for Region: {region_id}, POU: {pou_id}, Course: {course_id}")
        data = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "__VIEWSTATE": hidden_fields.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": hidden_fields.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": hidden_fields.get("__EVENTVALIDATION", ""),
            "ddl_reg": region_id,
            "ddlPou": pou_id,
            "ddl_course": course_id,
            "btn_getlist": "Get List"
        }

        try:
            time.sleep(self.delay)
            resp = self.session.post(BASE_URL, data=data, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(f"Submit returned HTTP {resp.status_code}")
                return False, None, f"HTTP Error {resp.status_code}"

            soup = BeautifulSoup(resp.text, "html.parser")
            grid = soup.find("table", id="GridView1")

            if not grid:
                logger.warning("GridView1 not found in response.")
                return True, [], "No GridView rendered"

            rows = grid.find_all("tr")
            if not rows:
                return True, [], "Empty table"

            # Check if this is the 'no records found' row
            header_cells = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
            if len(rows) == 1 and any("no records found" in c.lower() for c in header_cells):
                logger.info(f"0 batches found for POU {pou_id}, Course {course_id} ('No records found').")
                return True, [], "Zero records found"

            # Parse table columns
            # Expected headers: Batch No, Available Seats, From Date, To Date, Batch Time, Pou Name, Course, Open For
            results = []
            for tr in rows[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if not cells or len(cells) < 8:
                    continue
                batch_data = {
                    "batch_no": cells[0],
                    "available_seats": cells[1],
                    "from_date": cells[2],
                    "to_date": cells[3],
                    "batch_time": cells[4],
                    "pou_name": cells[5],
                    "course": cells[6],
                    "open_for": cells[7],
                    "queried_pou_id": pou_id,
                    "queried_course_id": course_id
                }
                results.append(batch_data)

            logger.info(f"Successfully parsed {len(results)} batches.")
            return True, results, "Success"
        except Exception as e:
            logger.error(f"Exception during batch submission: {e}")
            return False, None, str(e)


def run_poc_test():
    scraper = ICAIScraperPOC(request_timeout=15, delay_between_requests=2.0)

    # 1. Start fresh session
    ok, html, hidden_fields = scraper.get_initial_page()
    if not ok:
        print("Initial GET failed.")
        return

    # 2. Test Region 4 (Southern)
    region_id = "4"
    course_id = "45"  # MCS Course
    ok, html_reg, reg_hidden, pous = scraper.trigger_region_postback(region_id, hidden_fields, course_id)
    if not ok:
        print("Region postback failed.")
        return

    # 3. Test matrix
    test_matrix = [
        ("138", "CHENNAI", "45", "MCS"),
        ("102", "BENGALURU", "45", "MCS"),
        ("106", "COIMBATORE", "45", "MCS"),
        ("132", "THOOTHUKUDI", "49", "MCS Weekend"),
    ]

    all_results = []
    # Note: after each query, the page re-renders with fresh VIEWSTATE.
    # We should update hidden_fields from each response.
    current_hidden = reg_hidden

    for pou_id, pou_name, c_id, c_name in test_matrix:
        if pou_id not in pous:
            print(f"Skipping POU {pou_name} ({pou_id}): Not present in Region {region_id}")
            continue

        print(f"\n--- Testing {pou_name} ({pou_id}) - Course {c_name} ({c_id}) ---")
        ok, batches, msg = scraper.fetch_batch_list(region_id, pou_id, c_id, current_hidden)
        if not ok:
            print(f"FAILED for {pou_name}: {msg}")
            # Refresh session and region if needed
            continue

        print(f"Result: {msg}. Found {len(batches) if batches is not None else 0} batches.")
        if batches:
            all_results.extend(batches)
            for b in batches:
                print(f"  Batch: {b['batch_no']} | Seats: {b['available_seats']} | Dates: {b['from_date']} to {b['to_date']}")

    # Export to CSV
    csv_file = "icai_poc_results.csv"
    if all_results:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nWrote {len(all_results)} batch records to {csv_file}")
    else:
        print("\nNo batch rows collected to write to CSV.")

if __name__ == "__main__":
    run_poc_test()
