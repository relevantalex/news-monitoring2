import asyncio
from playwright.async_api import async_playwright
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import time

class NewsVerifierPlaywright:
    def __init__(self):
        # Media configuration with Playwright selectors
        self.media_config = {
            "yonhap": {
                "url": "https://www.yna.co.kr/search/index?query={}&ctype=A&from={}&to={}",
                "selectors": ["div.cts_atclst a", "div.news-tit"],
                "keywords": ["에너지기술개발계획", "무탄소 에너지", "해상풍력", "LS전선"],
                "wait_for": "div.cts_atclst"
            },
            "mtn": {
                "url": "https://news.mtn.co.kr/newscenter/news_search.mtn?keyword={}",
                "selectors": ["div.news-txt a", "div.news-title"],
                "keywords": ["해상풍력", "기자재", "입찰"],
                "wait_for": "div.news-txt"
            },
            "electimes": {
                "url": "https://www.electimes.com/news/articleList.html?sc_word={}",
                "selectors": ["div.article-list a", "div.titles"],
                "keywords": ["해상풍력", "개발사", "지분"],
                "wait_for": "div.article-list"
            },
        }
        
        # Known articles
        self.known_articles_dec18 = {
            "국립의대·공항·해상풍력 탈규제… 해 넘기는 전남 현안": {
                "media": "Newsis",
                "category": "Local govt policy"
            }
        }
        
        self.known_articles_dec12 = {
            "기후위기 문제 심각한데 또 깎인 예산안": {
                "media": "Fortune Korea",
                "category": "Govt policy",
                "journalist": "Nayoon Kim"
            }
        }

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

    async def search_articles(self, date: str, known_articles: Dict) -> List[Dict]:
        """Search for articles using Playwright"""
        found_articles = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Create a new page
            page = await context.new_page()
            
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
                            
                            # Navigate to page
                            await page.goto(url, wait_until='networkidle')
                            
                            # Wait for content
                            try:
                                await page.wait_for_selector(config["wait_for"], timeout=10000)
                            except Exception as e:
                                print(f"Timeout waiting for content on {media_name}")
                                continue
                            
                            # Let JavaScript execute
                            await page.wait_for_timeout(2000)
                            
                            # Find articles
                            for selector in config["selectors"]:
                                elements = await page.query_selector_all(selector)
                                for elem in elements:
                                    title = await elem.text_content()
                                    link = await elem.get_attribute('href')
                                    
                                    if not title or not link:
                                        continue
                                    
                                    title = title.strip()
                                    
                                    for known_title, known_info in known_articles.items():
                                        if self.titles_match(title, known_title) and not any(a['url'] == link for a in found_articles):
                                            found_articles.append({
                                                'title': known_title,
                                                'url': link,
                                                'source': media_name,
                                                'matched': True,
                                                'known_info': known_info
                                            })
                            
                        except Exception as e:
                            print(f"Error searching {media_name} with keyword '{keyword}': {str(e)}")
                            continue
                        
                        # Add delay between searches
                        await page.wait_for_timeout(1000)
            
            finally:
                await browser.close()
        
        return found_articles

    async def verify_coverage(self, date: str):
        """Verify coverage of known articles"""
        known_articles = self.known_articles_dec18 if date == '2024-12-18' else self.known_articles_dec12
        found_articles = await self.search_articles(date, known_articles)
        
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


async def main():
    verifier = NewsVerifierPlaywright()
    
    print("\nVerifying December 18th, 2024 articles...")
    await verifier.verify_coverage('2024-12-18')
    
    print("\nVerifying December 12th, 2024 articles...")
    await verifier.verify_coverage('2024-12-12')


if __name__ == "__main__":
    asyncio.run(main())
