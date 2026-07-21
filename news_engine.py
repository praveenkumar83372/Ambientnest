"""
Real-Time Morning Financial News Scraper
Fetches breaking business, stock market, and macroeconomic headlines for video hooks.
"""

import urllib.parse
import xml.etree.ElementTree as ET
import requests


def fetch_morning_financial_news():
    """Fetches top 5 trending financial news headlines from Google News RSS."""
    print("📰 [News Engine] Fetching morning financial news headlines...")
    query = "central banks inflation stock market billionaires finance"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        response = requests.get(rss_url, timeout=10)
        root = ET.fromstring(response.content)

        headlines = []
        for item in root.findall(".//item")[:5]:
            title = item.find("title").text
            if title:
                # Remove source trailing name (e.g., " - Bloomberg")
                clean_title = title.split(" - ")[0]
                headlines.append(clean_title)

        print(
            f"✅ [News Engine] Retrieved {len(headlines)} breaking headlines."
        )
        return headlines

    except Exception as e:
        print(f"⚠️ [News Engine] Failed to fetch news: {e}. Using baseline.")
        return [
            "Federal Reserve signals liquidity shifts in global markets",
            "Billionaire portfolio allocations shift toward alternative assets",
        ]


if __name__ == "__main__":
    news = fetch_morning_financial_news()
    for idx, h in enumerate(news, 1):
        print(f"{idx}. {h}")