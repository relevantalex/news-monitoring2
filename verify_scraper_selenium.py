import time
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

class NewsVerifierSelenium:
    def __init__(self):
        # Initialize Chrome options
        self.options = uc.ChromeOptions()
        self.options.add_argument('--headless')  # Run in headless mode
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920x1080')
        
        # Add user agent
        self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Initialize driver
        self.driver = None
        
        # Media configuration with Selenium selectors
        self.media_config = {
            "yonhap": {
                "url": "https://www.yna.co.kr/search/index?query={}&ctype=A&from={}&to={}",
                "selectors": ["//div[@class='cts_atclst']//a", "//div[@class='news-tit']"],
                "keywords": ["에너지기술개발계획", "무탄소 에너지", "해상풍력", "LS전선"],
                "wait_for": "//div[@class='cts_atclst']"
            },
            "mtn": {
                "url": "https://news.mtn.co.kr/newscenter/news_search.mtn?keyword={}",
                "selectors": ["//div[@class='news-txt']//a", "//div[@class='news-title']"],
                "keywords": ["해상풍력", "기자재", "입찰"],
                "wait_for": "//div[@class='news-txt']"
            },
            "electimes": {
                "url": "https://www.electimes.com/news/articleList.html?sc_word={}",
                "selectors": ["//div[@class='article-list']//a", "//div[@class='titles']"],
                "keywords": ["해상풍력", "개발사", "지분"],
                "wait_for": "//div[@class='article-list']"
            },
            # Add more media sites...
        }
        
        # Known articles (same as before)
        self.known_articles_dec18 = {
            "국립의대·공항·해상풍력 탈규제… 해 넘기는 전남 현안": {
                "media": "Newsis",
                "category": "Local govt policy"
            },
            # ... (rest of the articles)
        }
        
        self.known_articles_dec12 = {
            "기후위기 문제 심각한데 또 깎인 예산안": {
                "media": "Fortune Korea",
                "category": "Govt policy",
                "journalist": "Nayoon Kim"
            },
            # ... (rest of the articles)
        }

    def initialize_driver(self):
        """Initialize or reinitialize the Chrome driver"""
        if self.driver:
            self.driver.quit()
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.implicitly_wait(10)

    def clean_title(self, title: str) -> str:
        """Clean and normalize title text"""
        title = re.sub(r'\s+', ' ', title).strip().lower()
        title = re.sub(r'[^\w\s가-힣]', '', title)
        return title

    def titles_match(self, title1: str, title2: str) -> bool:
        """Compare titles accounting for minor differences"""
        t1 = self.clean_title(title1)
        t2 = self.clean_title(title2)
        
        if t1 == t2:
            return True
        
        t1_parts = set(t1.split())
        t2_parts = set(t2.split())
        common_words = t1_parts.intersection(t2_parts)
        
        if len(common_words) >= min(len(t1_parts), len(t2_parts)) * 0.6:
            key_terms = ['에너지', '해상풍력', 'CCUS', 'BESS', '데이터센터', 'OpenAI', '기후위기', '신재생']
            for term in key_terms:
                if term.lower() in t1 and term.lower() in t2:
                    return True
        
        return False

    def search_articles(self, date: str, known_articles: Dict) -> List[Dict]:
        """Search for articles using Selenium"""
        found_articles = []
        self.initialize_driver()
        
        try:
            for media_name, config in self.media_config.items():
                for keyword in config["keywords"]:
                    try:
                        # Format URL with date if needed
                        if "{}" in config["url"]:
                            if config["url"].count("{}") == 3:  # URL needs date
                                url = config["url"].format(keyword, date, date)
                            else:
                                url = config["url"].format(keyword)
                        
                        # Load page
                        self.driver.get(url)
                        
                        # Wait for content to load
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, config["wait_for"]))
                            )
                        except TimeoutException:
                            print(f"Timeout waiting for content on {media_name}")
                            continue
                        
                        # Let JavaScript execute
                        time.sleep(2)
                        
                        # Find articles
                        for selector in config["selectors"]:
                            try:
                                elements = self.driver.find_elements(By.XPATH, selector)
                                for elem in elements:
                                    title = elem.text.strip()
                                    link = elem.get_attribute('href')
                                    
                                    if not title or not link:
                                        continue
                                    
                                    for known_title, known_info in known_articles.items():
                                        if self.titles_match(title, known_title) and not any(a['url'] == link for a in found_articles):
                                            found_articles.append({
                                                'title': known_title,
                                                'url': link,
                                                'source': media_name,
                                                'matched': True,
                                                'known_info': known_info
                                            })
                            except NoSuchElementException:
                                continue
                            
                    except Exception as e:
                        print(f"Error searching {media_name} with keyword '{keyword}': {str(e)}")
                        continue
                    
                    # Add delay between searches
                    time.sleep(1)
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return found_articles

    def verify_coverage(self, date: str):
        """Verify coverage of known articles"""
        known_articles = self.known_articles_dec18 if date == '2024-12-18' else self.known_articles_dec12
        found_articles = self.search_articles(date, known_articles)
        
        print(f"\nVerification Results for {date}")
        print("-" * 50 + "\n")
        
        print("Found Articles:")
        for article in found_articles:
            print(f"✓ {article['title']}")
            print(f"  Media: {article['known_info']['media']}")
            print(f"  Category: {article['known_info']['category']}")
            if 'journalist' in article['known_info']:
                print(f"  Journalist: {article['known_info']['journalist']}")
            print(f"  URL: {article['url']}\n")
        
        print("\nMissing Articles:")
        found_titles = {a['title'] for a in found_articles}
        for title, info in known_articles.items():
            if title not in found_titles:
                print(f"✗ {title}")
                print(f"  Expected Media: {info['media']}")
                print(f"  Expected Category: {info['category']}")
                if 'journalist' in info:
                    print(f"  Expected Journalist: {info['journalist']}")
                print()
        
        coverage = len(found_articles) / len(known_articles) * 100
        print(f"\nCoverage: {coverage:.1f}% ({len(found_articles)} out of {len(known_articles)} articles found)\n")


if __name__ == "__main__":
    verifier = NewsVerifierSelenium()
    
    print("\nVerifying December 18th, 2024 articles...")
    verifier.verify_coverage('2024-12-18')
    
    print("\nVerifying December 12th, 2024 articles...")
    verifier.verify_coverage('2024-12-12')
