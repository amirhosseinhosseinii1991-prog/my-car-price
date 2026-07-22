import re
import threading
import os
from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_text(text):
    if not text: return ""
    return re.sub(r"\s+", " ", text).strip()

def scrape_iranjib_internal(results):
    try:
        url = "https://www.iranjib.ir/showgroup/45/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                for row in table.find_all("tr")[1:]:
                    cols = [clean_text(td.get_text()) for td in row.find_all("td")]
                    if len(cols) >= 3:
                        results.append({
                            "car_name": cols[0],
                            "market_price": cols[1],
                            "factory_price": cols[2] if cols[2] else "---",
                            "source": "ایران‌جیب (داخلی)",
                            "date": "بروزرسانی شده"
                        })
    except Exception as e: print("Iranjib Error:", e)

def scrape_hamrah(results):
    try:
        url = "https://www.hamrah-mechanic.com/carprice/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            page_text = clean_text(soup.get_text(" "))
            patterns = re.findall(r"([A-Za-zآ-ی0-9\s\-]+)\s+([\d,]+)\s*تومان", page_text)
            for name, price in patterns:
                if len(name) > 3:
                    results.append({
                        "car_name": clean_text(name),
                        "market_price": f"{price} تومان",
                        "factory_price": "---",
                        "source": "همراه مکانیک",
                        "date": "لحظه‌ای"
                    })
    except Exception as e: print("Hamrah Error:", e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/prices")
def api_prices():
    query = request.args.get("query", "").strip().lower()
    results = []
    t1 = threading.Thread(target=scrape_iranjib_internal, args=(results,))
    t2 = threading.Thread(target=scrape_hamrah, args=(results,))
    t1.start(); t2.start()
    t1.join(); t2.join()
    
    if query:
        results = [x for x in results if query in x["car_name"].lower()]
    return jsonify(results)

if __name__ == "__main__":
    # این بخش حیاتی برای Render است
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
