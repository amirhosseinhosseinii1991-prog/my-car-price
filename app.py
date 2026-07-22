import re
import threading
from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def scrape_iranjib_internal(results):
    try:
        url = "https://www.iranjib.ir/showgroup/45/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return

        soup = BeautifulSoup(r.text, "html.parser")
        page_text = clean_text(soup.get_text(" "))

        # تاریخ
        date_text = "نامشخص"
        m_date = re.search(r"آخرین به روز رسانی[^0-9۰-۹]*([0-9۰-۹/\-]+)", page_text)
        if m_date:
            date_text = m_date.group(1)

        # تلاش برای پیدا کردن ردیف‌های خودرو
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = [clean_text(td.get_text(" ")) for td in row.find_all("td")]
                if len(cols) >= 3:
                    name = cols[0]
                    market = cols[1]
                    factory = cols[2]

                    if name and len(name) > 2 and any(ch.isdigit() for ch in market):
                        results.append({
                            "car_name": name,
                            "market_price": market,
                            "factory_price": factory if factory else "---",
                            "source": "ایران‌جیب (داخلی)",
                            "date": date_text
                        })
    except Exception as e:
        print("iranjib internal error:", e)

def scrape_iranjib_imported(results):
    try:
        url = "https://www.iranjib.ir/showgroup/46/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return

        soup = BeautifulSoup(r.text, "html.parser")
        page_text = clean_text(soup.get_text(" "))

        date_text = "نامشخص"
        m_date = re.search(r"آخرین به روز رسانی[^0-9۰-۹]*([0-9۰-۹/\-]+)", page_text)
        if m_date:
            date_text = m_date.group(1)

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = [clean_text(td.get_text(" ")) for td in row.find_all("td")]
                if len(cols) >= 3:
                    name = cols[0]
                    market = cols[1]
                    factory = cols[2]

                    if name and len(name) > 2 and any(ch.isdigit() for ch in market):
                        results.append({
                            "car_name": name,
                            "market_price": market,
                            "factory_price": factory if factory else "---",
                            "source": "ایران‌جیب (وارداتی)",
                            "date": date_text
                        })
    except Exception as e:
        print("iranjib imported error:", e)

def scrape_hamrah(results):
    try:
        url = "https://www.hamrah-mechanic.com/carprice/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return

        soup = BeautifulSoup(r.text, "html.parser")
        page_text = clean_text(soup.get_text(" "))

        date_text = "نامشخص"
        m_date = re.search(r"به روز رسانی\s*[:：]?\s*([0-9۰-۹/\-]+)", page_text)
        if m_date:
            date_text = m_date.group(1)

        # استخراج تقریبی رکوردها
        patterns = re.findall(r"([A-Za-zآ-ی0-9\s\-\/]+)\s+([\d,]+)\s*تومان", page_text)
        for name, price in patterns:
            name = clean_text(name)
            price = clean_text(price)
            if len(name) > 3:
                results.append({
                    "car_name": name,
                    "market_price": f"{price} تومان",
                    "factory_price": "---",
                    "source": "همراه مکانیک",
                    "date": date_text
                })
    except Exception as e:
        print("hamrah error:", e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/prices")
def api_prices():
    query = request.args.get("query", "").strip().lower()
    results = []

    threads = [
        threading.Thread(target=scrape_iranjib_internal, args=(results,)),
        threading.Thread(target=scrape_iranjib_imported, args=(results,)),
        threading.Thread(target=scrape_hamrah, args=(results,))
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # حذف تکراری‌ها
    unique = []
    seen = set()
    for item in results:
        key = (item["car_name"], item["market_price"], item["factory_price"], item["source"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    if query:
        unique = [x for x in unique if query in x["car_name"].lower()]

    return jsonify(unique)

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    Fix Render app startup
