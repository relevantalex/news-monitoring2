import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from typing import Dict, List, Optional

class NewsVerifier:
    def __init__(self):
        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Search URLs for major platforms
        self.search_urls = {
            'naver': 'https://search.naver.com/search.naver?where=news&query={}&sort=1&ds={}&de={}&nso=so%3Ar%2Cp%3Afrom{}to{}',
            'daum': 'https://search.daum.net/search?w=news&q={}&sort=recency&sd={}&ed={}&period=u'
        }
        
        # Known articles for December 18th
        self.known_articles_dec18 = {
            "국립의대·공항·해상풍력 탈규제… 해 넘기는 전남 현안": {
                "media": "Newsis",
                "category": "Local govt policy"
            },
            "무탄소 에너지 강화… 정부, 5차 에너지기술개발계획 확정": {
                "media": "Yonhap",
                "category": "Govt policy"
            },
            "인천 해상풍력 성공 추진 토론회": {
                "media": "Jungdo ilbo",
                "category": "Local govt policy"
            },
            "중국까지… K-풍력시장 다 뺏길 판": {
                "media": "Green post",
                "category": "RE Industry"
            },
            "제13회 울산에너지포럼 개최… 부유식 해상풍력 확대 논의": {
                "media": "Energy platform",
                "category": "RE Industry"
            },
            "트럼프-머스크, CCUS 탄소포집 기술 지원 유력… 한수출 측면 강점": {
                "media": "Financial news",
                "category": "RE Industry"
            },
            "에어리퀴드, 암모니아 수소 생산·유통 위한 EU 보조금 받아": {
                "media": "Gas news",
                "category": "RE Industry"
            },
            "한국해외인프라도시개발지원공사, 일본 BESS 사업 투자": {
                "media": "The guru",
                "category": "RE Industry"
            },
            "1000억달러 쏜 손정의, 美 AI 데이터센터·칩에 집중 투자": {
                "media": "Chosun",
                "category": "RE Industry"
            },
            "피터틸·엔비디아·무바달라, 오픈AI 데이터센터 파트너 크루소 투자": {
                "media": "The guru",
                "category": "RE Industry"
            }
        }
        
        # Known articles for December 12th
        self.known_articles_dec12 = {
            "기후위기 문제 심각한데 또 깎인 예산안": {
                "media": "Fortune Korea",
                "category": "Govt policy",
                "journalist": "Nayoon Kim"
            },
            "해상풍력도 무늬만 한국산?…입찰 결과 앞두고 韓기자재 업계 '술렁'": {
                "media": "MTN News",
                "category": "Stakeholders",
                "journalist": "Jieun Park"
            },
            "글로벌 해상풍력 개발사…韓 시장서 지분 매각‧사업 축소 움직임": {
                "media": "Electimes",
                "category": "Stakeholders",
                "journalist": "Sangmin Ahn"
            },
            "LS전선, 9천73억원 규모 독일 해상풍력 프로젝트 수주": {
                "media": "Yonhap",
                "category": "Stakeholders",
                "journalist": "Ahram Kim"
            },
            "'3조9000억' 전남 신재생에너지 펀드 조성 잰걸음": {
                "media": "Money S",
                "category": "RE Industry",
                "journalist": "Kichul Hong"
            },
            "[EE칼럼] 부유식 해상풍력을 차세대 산업으로 키워야": {
                "media": "EKN",
                "category": "RE Industry"
            },
            "주민 반대 격한데…사하구, 다대포 풍력발전 강행하나": {
                "media": "Kookje",
                "category": "RE Industry",
                "journalist": "Changhoon Baek"
            }
        }
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
        # Media-specific search configuration
        self.media_config = {
            "yonhap": {
                "url": "https://www.yna.co.kr/search/index?query={}",
                "selectors": [".cts_atclst li a", ".news-tit"],
                "keywords": ["에너지기술개발계획", "무탄소 에너지", "해상풍력", "LS전선"]
            },
            "mtn": {
                "url": "https://news.mtn.co.kr/newscenter/news_search.mtn?keyword={}",
                "selectors": [".news-txt a", ".news-title"],
                "keywords": ["해상풍력", "기자재", "입찰"]
            },
            "electimes": {
                "url": "https://www.electimes.com/news/articleList.html?sc_word={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["해상풍력", "개발사", "지분"]
            },
            "fortune": {
                "url": "https://www.fortunekorea.co.kr/news/articleList.html?sc_word={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["기후위기", "예산", "탄소중립"]
            },
            "moneys": {
                "url": "https://moneys.mt.co.kr/news/mwList.php?keyword={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["신재생에너지", "펀드", "전남"]
            },
            "ekn": {
                "url": "https://www.ekn.kr/news/articleList.html?sc_word={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["부유식", "해상풍력", "울산"]
            },
            "kookje": {
                "url": "https://www.kookje.co.kr/news/articleList.html?sc_word={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["다대포", "풍력발전", "사하구"]
            },
            "newsis": {
                "url": "https://newsis.com/search/schlist.html?val={}",
                "selectors": [".news-title a", ".titles"],
                "keywords": ["해상풍력", "전남", "탈규제"]
            },
            "gasnews": {
                "url": "https://www.gasnews.com/news/articleList.html?sc_word={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["에어리퀴드", "암모니아", "수소"]
            },
            "theguru": {
                "url": "https://www.theguru.co.kr/news/articleList.html?sc_word={}",
                "selectors": [".article-list a", ".titles"],
                "keywords": ["BESS", "OpenAI", "데이터센터"]
            },
            "chosun": {
                "url": "https://www.chosun.com/search/?query={}",
                "selectors": [".story-card a", ".titles"],
                "keywords": ["손정의", "AI", "데이터센터"]
            }
        }

    def make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    verify=False,
                    timeout=10
                )
                response.raise_for_status()
                return response
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch {url} after {max_retries} attempts: {str(e)}")
                    return None
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        return None

    def clean_title(self, title: str) -> str:
        """Clean and normalize title text"""
        # Remove whitespace and convert to lowercase
        title = re.sub(r'\s+', ' ', title).strip().lower()
        # Remove special characters but keep Korean characters
        title = re.sub(r'[^\w\s가-힣]', '', title)
        return title

    def titles_match(self, title1: str, title2: str) -> bool:
        """Compare titles accounting for minor differences"""
        t1 = self.clean_title(title1)
        t2 = self.clean_title(title2)
        
        # Check exact match
        if t1 == t2:
            return True
        
        # Check if significant parts match (60% threshold)
        t1_parts = set(t1.split())
        t2_parts = set(t2.split())
        common_words = t1_parts.intersection(t2_parts)
        
        if len(common_words) >= min(len(t1_parts), len(t2_parts)) * 0.6:
            # Check if key terms are present
            key_terms = ['에너지', '해상풍력', 'CCUS', 'BESS', '데이터센터', 'OpenAI', '기후위기', '신재생']
            for term in key_terms:
                if term.lower() in t1 and term.lower() in t2:
                    return True
        
        return False

    def search_articles(self, date: str, known_articles: Dict) -> List[Dict]:
        """Search for articles across multiple platforms"""
        found_articles = []
        formatted_dates = self.format_date(date)
        
        # Search media sites directly
        for media_name, config in self.media_config.items():
            for keyword in config["keywords"]:
                try:
                    url = config["url"].format(keyword)
                    response = self.make_request(url)
                    
                    if response:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        for selector in config["selectors"]:
                            for elem in soup.select(selector):
                                try:
                                    title = elem.text.strip()
                                    link = elem.get('href', '')
                                    
                                    # Handle relative URLs
                                    if not link.startswith('http'):
                                        if media_name == "chosun":
                                            link = f"https://www.chosun.com{link}"
                                        else:
                                            link = f"https://{media_name}.co.kr{link}"
                                    
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
                                    print(f"Error processing article from {media_name}: {str(e)}")
                                    continue
                except Exception as e:
                    print(f"Error searching {media_name} with keyword '{keyword}': {str(e)}")
                    continue
        
        # Search Naver and Daum
        for platform, url_template in self.search_urls.items():
            for keyword in set().union(*[c["keywords"] for c in self.media_config.values()]):
                if platform == 'naver':
                    url = url_template.format(
                        keyword,
                        formatted_dates['naver'],
                        formatted_dates['naver'],
                        date.replace('-', ''),
                        date.replace('-', '')
                    )
                else:
                    url = url_template.format(
                        keyword,
                        formatted_dates['daum'],
                        formatted_dates['daum']
                    )
                
                response = self.make_request(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('.news_area' if platform == 'naver' else '.c-item')
                
                for article in articles:
                    title_elem = article.select_one('.news_tit' if platform == 'naver' else '.tit-g')
                    if title_elem:
                        title = title_elem.text.strip()
                        link = title_elem.get('href', '')
                        
                        for known_title, known_info in known_articles.items():
                            if self.titles_match(title, known_title) and not any(a['url'] == link for a in found_articles):
                                found_articles.append({
                                    'title': known_title,
                                    'url': link,
                                    'source': platform,
                                    'matched': True,
                                    'known_info': known_info
                                })
        
        return found_articles

    def format_date(self, date_str: str) -> Dict[str, str]:
        """Format date string for different search engines"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return {
            'naver': date_obj.strftime('%Y.%m.%d'),
            'daum': date_obj.strftime('%Y%m%d')
        }

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
    verifier = NewsVerifier()
    
    # Verify December 18th articles
    print("\nVerifying December 18th, 2024 articles...")
    verifier.verify_coverage('2024-12-18')
    
    # Verify December 12th articles
    print("\nVerifying December 12th, 2024 articles...")
    verifier.verify_coverage('2024-12-12')
