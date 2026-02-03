#!/usr/bin/env python3
"""
Polyberg News Scraper
Scrapes real news from public sources (no API keys)
- Reuters
- Bloomberg (via RSS)
- ESPN
- CoinTelegraph
"""

import requests
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict
from html.parser import HTMLParser
import time
import re

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

class NewsAggregator:
    """Aggregate news from multiple sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self.news = []
    
    def fetch_cointelegraph_rss(self) -> List[Dict]:
        """Fetch from CoinTelegraph RSS (freely available)"""
        news = []
        try:
            print("[News] Fetching CoinTelegraph RSS...")
            # CoinTelegraph provides RSS feeds
            feed_urls = [
                "https://cointelegraph.com/feed",  # Main feed
                "https://cointelegraph.com/rss/news",  # News only
            ]
            
            for feed_url in feed_urls:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code != 200:
                        continue
                    
                    # Parse RSS using simple regex patterns
                    title_pattern = r'<title[^>]*>([^<]+)</title>'
                    link_pattern = r'<link[^>]*>([^<]+)</link>'
                    pubdate_pattern = r'<pubDate>([^<]+)</pubDate>'
                    desc_pattern = r'<description[^>]*>([^<]+)</description>'
                    
                    titles = re.findall(title_pattern, response.text)
                    links = re.findall(link_pattern, response.text)
                    
                    for i, title in enumerate(titles[1:11]):  # Skip feed title, get top 10
                        if i < len(links):
                            news.append({
                                "title": title.strip(),
                                "source": "CoinTelegraph",
                                "url": links[i].strip(),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "category": "crypto",
                            })
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"CoinTelegraph error: {e}")
        
        return news[:5]
    
    def fetch_cnbc_rss(self) -> List[Dict]:
        """Fetch CNBC business news"""
        news = []
        try:
            print("[News] Fetching CNBC...")
            response = self.session.get(
                "https://feeds.cnbc.com/id/100003114x/rss.html",
                timeout=10
            )
            
            if response.status_code == 200:
                # Parse basic RSS
                title_pattern = r'<title[^>]*>([^<]+)</title>'
                link_pattern = r'<link>([^<]+)</link>'
                
                titles = re.findall(title_pattern, response.text)
                links = re.findall(link_pattern, response.text)
                
                for i, title in enumerate(titles[1:8]):
                    if i < len(links):
                        news.append({
                            "title": title.strip(),
                            "source": "CNBC",
                            "url": links[i].strip(),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "category": "macro",
                        })
        except Exception as e:
            print(f"CNBC error: {e}")
        
        return news[:3]
    
    def fetch_espn_rss(self) -> List[Dict]:
        """Fetch ESPN sports news"""
        news = []
        try:
            print("[News] Fetching ESPN...")
            
            # ESPN RSS feeds
            feeds = [
                "https://www.espn.com/espn/rss/news.xml",
                "https://www.espn.com/nfl/rss.xml",
                "https://www.espn.com/nba/rss.xml",
            ]
            
            for feed_url in feeds:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code != 200:
                        continue
                    
                    title_pattern = r'<title[^>]*>([^<]+)</title>'
                    link_pattern = r'<link>([^<]+)</link>'
                    
                    titles = re.findall(title_pattern, response.text)
                    links = re.findall(link_pattern, response.text)
                    
                    for i, title in enumerate(titles[1:6]):
                        if i < len(links) and len(news) < 8:
                            news.append({
                                "title": title.strip(),
                                "source": "ESPN",
                                "url": links[i].strip(),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "category": "sports",
                            })
                except:
                    continue
        
        except Exception as e:
            print(f"ESPN error: {e}")
        
        return news[:6]
    
    def fetch_economist(self) -> List[Dict]:
        """Fetch The Economist news (has RSS)"""
        news = []
        try:
            print("[News] Fetching The Economist...")
            response = self.session.get(
                "https://www.economist.com/finance-and-economics/rss.xml",
                timeout=10
            )
            
            if response.status_code == 200:
                title_pattern = r'<title[^>]*>([^<]+)</title>'
                link_pattern = r'<link>([^<]+)</link>'
                
                titles = re.findall(title_pattern, response.text)
                links = re.findall(link_pattern, response.text)
                
                for i, title in enumerate(titles[1:5]):
                    if i < len(links):
                        news.append({
                            "title": title.strip(),
                            "source": "The Economist",
                            "url": links[i].strip(),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "category": "macro",
                        })
        except Exception as e:
            print(f"Economist error: {e}")
        
        return news[:3]
    
    def aggregate(self) -> List[Dict]:
        """Fetch from all sources and aggregate"""
        all_news = []
        
        all_news.extend(self.fetch_cointelegraph_rss())
        time.sleep(0.5)
        all_news.extend(self.fetch_cnbc_rss())
        time.sleep(0.5)
        all_news.extend(self.fetch_espn_rss())
        time.sleep(0.5)
        all_news.extend(self.fetch_economist())
        
        # Remove duplicates by title
        seen = set()
        unique_news = []
        for article in all_news:
            title = article["title"].lower()
            if title not in seen:
                seen.add(title)
                unique_news.append(article)
        
        # Sort by timestamp (newest first)
        unique_news = sorted(
            unique_news,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        print(f"✓ Aggregated {len(unique_news)} news articles")
        return unique_news[:20]  # Return top 20
    
    def save_news(self, news: List[Dict]):
        """Save news to file"""
        output_file = DATA_DIR / "news.json"
        
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "articles": news,
            "count": len(news),
        }
        
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Saved {len(news)} news articles to {output_file}")

if __name__ == "__main__":
    aggregator = NewsAggregator()
    news = aggregator.aggregate()
    aggregator.save_news(news)
