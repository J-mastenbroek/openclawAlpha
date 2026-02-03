#!/usr/bin/env python3
"""
Polyberg News Scraper - Fetch from multiple reliable sources
"""

import json
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

class NewsScraperPolyberg:
    def __init__(self):
        self.articles = []
        self.seen_titles = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
    
    def deduplicate(self, title):
        """Avoid duplicate articles"""
        normalized = title.lower().strip()
        if normalized in self.seen_titles:
            return False
        self.seen_titles.add(normalized)
        return True
    
    def fetch_cointelegraph(self):
        """Fetch from CoinTelegraph RSS"""
        try:
            response = self.session.get(
                'https://cointelegraph.com/feed',
                timeout=10
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item', limit=10)
                for item in items:
                    try:
                        title = item.find('title').text if item.find('title') else ''
                        link = item.find('link').text if item.find('link') else ''
                        pubDate = item.find('pubDate').text if item.find('pubDate') else ''
                        
                        if title and self.deduplicate(title):
                            self.articles.append({
                                'title': title,
                                'source': 'CoinTelegraph',
                                'url': link,
                                'time': pubDate,
                                'category': 'crypto'
                            })
                    except:
                        pass
                print(f"[News] CoinTelegraph: {len([a for a in self.articles if a['source'] == 'CoinTelegraph'])} articles")
        except Exception as e:
            print(f"[News] CoinTelegraph error: {e}")
    
    def fetch_theverge(self):
        """Fetch from The Verge"""
        try:
            response = self.session.get(
                'https://www.theverge.com/rss/index.xml',
                timeout=10
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item', limit=5)
                for item in items:
                    try:
                        title = item.find('title').text if item.find('title') else ''
                        link = item.find('link').text if item.find('link') else ''
                        pubDate = item.find('pubDate').text if item.find('pubDate') else ''
                        
                        if title and self.deduplicate(title):
                            self.articles.append({
                                'title': title,
                                'source': 'The Verge',
                                'url': link,
                                'time': pubDate,
                                'category': 'tech'
                            })
                    except:
                        pass
                print(f"[News] The Verge: {len([a for a in self.articles if a['source'] == 'The Verge'])} articles")
        except Exception as e:
            print(f"[News] The Verge error: {e}")
    
    def fetch_techcrunch(self):
        """Fetch from TechCrunch RSS"""
        try:
            response = self.session.get(
                'https://techcrunch.com/feed/',
                timeout=10
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item', limit=5)
                for item in items:
                    try:
                        title = item.find('title').text if item.find('title') else ''
                        link = item.find('link').text if item.find('link') else ''
                        pubDate = item.find('pubDate').text if item.find('pubDate') else ''
                        
                        if title and self.deduplicate(title):
                            self.articles.append({
                                'title': title,
                                'source': 'TechCrunch',
                                'url': link,
                                'time': pubDate,
                                'category': 'tech'
                            })
                    except:
                        pass
                print(f"[News] TechCrunch: {len([a for a in self.articles if a['source'] == 'TechCrunch'])} articles")
        except Exception as e:
            print(f"[News] TechCrunch error: {e}")
    
    def fetch_espn(self):
        """Fetch from ESPN RSS"""
        try:
            response = self.session.get(
                'https://feeds.espn.com/feeds/site/espntech.xml',
                timeout=10
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item', limit=5)
                for item in items:
                    try:
                        title = item.find('title').text if item.find('title') else ''
                        link = item.find('link').text if item.find('link') else ''
                        pubDate = item.find('pubDate').text if item.find('pubDate') else ''
                        
                        if title and self.deduplicate(title):
                            self.articles.append({
                                'title': title,
                                'source': 'ESPN',
                                'url': link,
                                'time': pubDate,
                                'category': 'sports'
                            })
                    except:
                        pass
                print(f"[News] ESPN: {len([a for a in self.articles if a['source'] == 'ESPN'])} articles")
        except Exception as e:
            print(f"[News] ESPN error: {e}")
    
    def fetch_cryptofees(self):
        """Fetch from Crypto Fees Twitter/News"""
        try:
            # Try CryptoSlate as alternative
            response = self.session.get(
                'https://cryptoslate.com/feed/',
                timeout=10
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item', limit=5)
                for item in items:
                    try:
                        title = item.find('title').text if item.find('title') else ''
                        link = item.find('link').text if item.find('link') else ''
                        pubDate = item.find('pubDate').text if item.find('pubDate') else ''
                        
                        if title and self.deduplicate(title):
                            self.articles.append({
                                'title': title,
                                'source': 'CryptoSlate',
                                'url': link,
                                'time': pubDate,
                                'category': 'crypto'
                            })
                    except:
                        pass
                print(f"[News] CryptoSlate: {len([a for a in self.articles if a['source'] == 'CryptoSlate'])} articles")
        except Exception as e:
            print(f"[News] CryptoSlate error: {e}")
    
    def run(self):
        """Fetch all news"""
        print("[News] Fetching from multiple sources...")
        self.fetch_cointelegraph()
        time.sleep(1)
        self.fetch_techcrunch()
        time.sleep(1)
        self.fetch_theverge()
        time.sleep(1)
        self.fetch_espn()
        time.sleep(1)
        self.fetch_cryptofees()
        
        # Sort by most recent
        self.articles = sorted(self.articles, key=lambda x: x.get('time', ''), reverse=True)[:30]
        
        return self.articles
    
    def save(self, path):
        """Save to JSON"""
        data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'articles': self.articles,
            'count': len(self.articles)
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(self.articles)} news articles to {path}")


if __name__ == "__main__":
    scraper = NewsScraperPolyberg()
    scraper.run()
    scraper.save('data/news.json')
