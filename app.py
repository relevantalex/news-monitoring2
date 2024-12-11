import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from openai import OpenAI
import time
from googlesearch import search
import urllib3

# Disable SSL verification warnings
urllib3.disable_warnings()

st.set_page_config(page_title="CIP Korea News Monitor", layout="wide")

# API key input
api_key = st.text_input("Enter your OpenAI API key:", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

KOREAN_MEDIA_TRANSLATIONS = {
    '조선일보': 'Chosun Ilbo',
    '중앙일보': 'JoongAng Ilbo',
    '동아일보': 'Dong-A Ilbo',
    '한국경제': 'Korea Economic Daily',
    '매일경제': 'Maeil Business News',
    '전기신문': 'Electric Times',
    '연합뉴스': 'Yonhap News',
    # Add more as needed
}

def safe_request(url, verify=False):
    """Make a request with error handling"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=verify, timeout=10)
        return response
    except Exception as e:
        st.error(f"Error accessing {url}: {str(e)}")
        return None

def get_detailed_article_info(url):
    """Get detailed information from article page with better error handling"""
    try:
        response = safe_request(url)
        if not response:
            return "N/A", datetime.now().strftime('%Y-%m-%d')
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get journalist name
        journalist = "N/A"
        journalist_patterns = [
            ('span.writer', 'text'),
            ('div.journalist', 'text'),
            ('meta[property="article:author"]', 'content'),
            ('span[class*="author"]', 'text'),
        ]
        
        for selector, attr in journalist_patterns:
            element = soup.select_one(selector)
            if element:
                journalist = element.get(attr) if attr == 'content' else element.text
                journalist = journalist.replace('기자', '').strip()
                break
        
        # Get date
        date_str = datetime.now().strftime('%Y-%m-%d')  # default
        date_patterns = [
            ('meta[property="article:published_time"]', 'content'),
            ('meta[name="article:published_time"]', 'content'),
            ('time.date', 'datetime'),
            ('span.time', 'text'),
        ]
        
        for selector, attr in date_patterns:
            element = soup.select_one(selector)
            if element:
                try:
                    date_text = element.get(attr) if attr == 'content' else element.text
                    # Handle various date formats
                    if 'T' in date_text:
                        date_str = date_text.split('T')[0]
                    else:
                        # Add more date parsing as needed
                        date_str = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                    break
                except:
                    continue
        
        return journalist, date_str
    except Exception as e:
        st.error(f"Error getting article details: {str(e)}")
        return "N/A", datetime.now().strftime('%Y-%m-%d')

def search_naver_news(keyword, start_date, end_date):
    """Search Naver News with date filtering"""
    all_articles = []
    base_url = (
        f"https://search.naver.com/search.naver?"
        f"where=news&query={keyword}&sort=1"
        f"&ds={start_date.strftime('%Y.%m.%d')}"
        f"&de={end_date.strftime('%Y.%m.%d')}"
    )
    
    try:
        response = safe_request(base_url)
        if not response:
            return all_articles
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for item in soup.select('.news_area'):
            try:
                title = item.select_one('.news_tit').text
                link = item.select_one('.news_tit')['href']
                media = item.select_one('.info_group a').text
                
                # Get detailed info
                journalist, date = get_detailed_article_info(link)
                
                # Translate media name
                media_english = KOREAN_MEDIA_TRANSLATIONS.get(media, media)
                
                all_articles.append({
                    'title_kr': title,
                    'media': media_english,
                    'journalist': journalist,
                    'date': date,
                    'link': link,
                    'keyword': keyword,
                    'source': 'Naver'
                })
            except Exception as e:
                st.error(f"Error processing article: {str(e)}")
                continue
                
    except Exception as e:
        st.error(f"Error searching Naver News: {str(e)}")
    
    return all_articles

def search_google_news(keyword, start_date, end_date):
    """Search Google News"""
    all_articles = []
    search_query = f"{keyword} site:kr news"
    
    try:
        for url in search(search_query, lang="ko", num_results=5):
            try:
                response = safe_request(url)
                if not response:
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.text if soup.title else "No title"
                
                # Get detailed info
                journalist, date = get_detailed_article_info(url)
                
                all_articles.append({
                    'title_kr': title,
                    'media': url.split('/')[2],
                    'journalist': journalist,
                    'date': date,
                    'link': url,
                    'keyword': keyword,
                    'source': 'Google'
                })
                
                time.sleep(2)  # Avoid rate limiting
            except Exception as e:
                st.error(f"Error processing Google result: {str(e)}")
                continue
                
    except Exception as e:
        st.error(f"Error searching Google News: {str(e)}")
    
    return all_articles

def get_category_and_translation(title_kr):
    """Get category and translation using OpenAI"""
    try:
        prompt = f"""Analyze this Korean news article title and provide:
        1. Choose exactly one category from these options:
           - CIP (if about Copenhagen Infrastructure Partners or Korean offshore wind projects)
           - Govt policy (if about national government policies)
           - Local govt policy (if about local/regional government policies)
           - Stakeholders (if about industry players, companies, or key individuals)
           - RE Industry (if about general renewable energy industry news)
        2. Translate the title to English professionally
        3. Write a detailed 3-4 sentence synopsis in English that covers all key points
        
        Korean Title: {title_kr}
        
        Format response as:
        Category: [category]
        English Title: [translation]
        Synopsis: [detailed synopsis]
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        result = response.choices[0].message.content
        category = result.split('Category:')[1].split('\n')[0].strip()
        title_en = result.split('English Title:')[1].split('\n')[0].strip()
        synopsis = result.split('Synopsis:')[1].strip()
        
        return category, title_en, synopsis
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return "N/A", "Translation error", "Error generating summary"

def main():
    st.title("🌊 CIP Korea News Monitor")
    
    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now() - timedelta(days=7)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            datetime.now()
        )

    # Keywords
    default_keywords = [
        'CIP', 'COP', '코펜하겐 인프라스트럭쳐 파트너스',
        '한전', '전기위원회', '울산 부유식', '해울이', '해송',
        '태안해상풍력', '뷔나에너지', '해상풍력', '전남해상풍력',
        '울산해상풍력', '신안해상풍력', '전북해상풍력', '인천해상풍력',
        '포항해상풍력', '영광해상풍력', '제주해상풍력', '부산해상풍력',
        '수협', '발전사업허가', '전기사업허가', '전기사업법',
        '전기본', '자원안보특별법', '전력 송전망', '풍력 인허가',
        '청정수소', '암모니아', 'PtX', 'BESS', '데이터센터'
    ]
    
    keywords = st.multiselect(
        "Select Keywords:",
        default_keywords,
        default=default_keywords[:5]
    )

    # Custom keyword
    custom_keyword = st.text_input("Add Custom Keyword")
    if custom_keyword:
        keywords.append(custom_keyword)

    if st.button("🔍 Start News Monitor"):
        all_articles = []
        progress = st.progress(0)
        status = st.empty()
        
        for i, keyword in enumerate(keywords):
            status.text(f"Searching for: {keyword}")
            
            # Naver News
            naver_articles = search_naver_news(keyword, start_date, end_date)
            all_articles.extend(naver_articles)
            
            # Google News
            google_articles = search_google_news(keyword, start_date, end_date)
            all_articles.extend(google_articles)
            
            progress.progress((i + 1)/len(keywords))
        
        results = []
        total = len(all_articles)
        
        for i, article in enumerate(all_articles):
            status.text(f"Analyzing article {i+1} of {total}")
            category, title_en, synopsis = get_category_and_translation(article['title_kr'])
            
            results.append({
                'Category': category,
                'Date': article['date'],
                'Media': article['media'],
                'Journalist': article['journalist'],
                'Title (KR)': article['title_kr'],
                'Title (EN)': title_en,
                'Synopsis': synopsis,
                'Link': article['link'],
                'Source': article['source']
            })
            progress.progress((i + 1)/total)
        
        # Create DataFrame and sort
        df = pd.DataFrame(results)
        category_order = ['CIP', 'Govt policy', 'Local govt policy', 'Stakeholders', 'RE Industry']
        df['Category'] = pd.Categorical(df['Category'], categories=category_order, ordered=True)
        df = df.sort_values(['Category', 'Date'], ascending=[True, False])
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Title (KR)'])
        
        # Clear progress
        progress.empty()
        status.empty()
        
        # Display results
        st.subheader("📊 Results")
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Link": st.column_config.LinkColumn(),
            }
        )
        
        # Download option
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 Download Full Report",
            csv,
            f"CIP_News_Report_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

if __name__ == "__main__":
    main()
