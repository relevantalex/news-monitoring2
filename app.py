import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from openai import OpenAI
import re

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
    # Add more translations as needed
}

def get_detailed_article_info(url):
    """Get detailed information from the article page"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get journalist name (looking for common patterns)
        journalist = "N/A"
        journalist_patterns = [
            soup.select_one('.journalist_name'),
            soup.select_one('.byline'),
            soup.select_one('.author'),
            soup.select_one('span[class*="journalist"]'),
        ]
        
        for pattern in journalist_patterns:
            if pattern:
                journalist = pattern.text.strip()
                if '기자' in journalist:
                    journalist = journalist.replace('기자', '').strip()
                break
        
        # Get proper date
        date = datetime.now().strftime('%Y-%m-%d')  # fallback
        date_patterns = [
            soup.select_one('meta[property="article:published_time"]'),
            soup.select_one('.article_date'),
            soup.select_one('.date'),
            soup.select_one('time'),
        ]
        
        for pattern in date_patterns:
            if pattern:
                try:
                    if pattern.get('content'):
                        date = datetime.fromisoformat(pattern['content'].split('T')[0])
                    else:
                        date_text = pattern.text.strip()
                        # Parse various Korean date formats
                        # Add more parsing logic here
                        date = datetime.strptime(date_text, '%Y-%m-%d')
                except:
                    continue
                break
        
        return journalist, date.strftime('%Y-%m-%d')
    except Exception as e:
        st.error(f"Error getting article details: {str(e)}")
        return "N/A", datetime.now().strftime('%Y-%m-%d')

def search_naver_news(keyword, start_date, end_date):
    """Search Naver News with date filtering"""
    base_url = (
        f"https://search.naver.com/search.naver?"
        f"where=news&query={keyword}&sort=1"
        f"&ds={start_date.strftime('%Y.%m.%d')}"
        f"&de={end_date.strftime('%Y.%m.%d')}"
    )
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    articles = []
    try:
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for item in soup.select('.news_area'):
            title = item.select_one('.news_tit').text
            link = item.select_one('.news_tit')['href']
            media = item.select_one('.info_group a').text
            
            # Get detailed info from article page
            journalist, date = get_detailed_article_info(link)
            
            # Translate media name if available
            media_english = KOREAN_MEDIA_TRANSLATIONS.get(media, media)
            
            articles.append({
                'title_kr': title,
                'media': media_english,
                'journalist': journalist,
                'date': date,
                'link': link,
                'keyword': keyword
            })
    except Exception as e:
        st.error(f"Error searching news: {str(e)}")
    
    return articles

def search_daum_news(keyword, start_date, end_date):
    """Search Daum News"""
    # Similar implementation to Naver but for Daum
    # Add Daum news search implementation
    return []

def get_category_and_translation(title_kr):
    """Get category, English translation, and summary using OpenAI"""
    try:
        prompt = f"""Analyze this Korean news article title and provide:
        1. Choose exactly one category from these options:
           - CIP (if about Copenhagen Infrastructure Partners)
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.choices[0].message.content
        category = result.split('Category:')[1].split('\n')[0].strip()
        title_en = result.split('English Title:')[1].split('\n')[0].strip()
        synopsis = result.split('Synopsis:')[1].strip()
        
        return category, title_en, synopsis
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return "N/A", "Translation error", "Error generating summary"

# Rest of the main interface code remains similar but updated to handle new fields
# [Continue in next part due to length...]

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

    # Keywords input
    default_keywords = [
        'CIP', 'Copenhagen Infrastructure Partners',
        '한전', '전기위원회',
        '해상풍력', '전남해상풍력', '제주해상풍력',
        '청정수소', '암모니아',
        '해상풍력 입찰', '풍력발전', 'RPS'
    ]
    
    keywords = st.multiselect(
        "Select Keywords:",
        default_keywords,
        default=default_keywords[:4]
    )

    # Custom keyword
    custom_keyword = st.text_input("Add Custom Keyword")
    if custom_keyword:
        keywords.append(custom_keyword)

    if st.button("🔍 Start News Monitor"):
        all_articles = []
        progress = st.progress(0)
        status = st.empty()
        
        # Search across all platforms
        for i, keyword in enumerate(keywords):
            status.text(f"Searching for: {keyword}")
            
            # Naver News
            articles = search_naver_news(keyword, start_date, end_date)
            all_articles.extend(articles)
            
            # Daum News
            daum_articles = search_daum_news(keyword, start_date, end_date)
            all_articles.extend(daum_articles)
            
            progress.progress((i + 1)/len(keywords))
        
        # Process articles
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
                'Link': f'[Link]({article["link"]})'
            })
            progress.progress((i + 1)/total)
        
        # Create DataFrame and sort by category and date
        df = pd.DataFrame(results)
        category_order = ['CIP', 'Govt policy', 'Local govt policy', 'Stakeholders', 'RE Industry']
        df['Category'] = pd.Categorical(df['Category'], categories=category_order, ordered=True)
        df = df.sort_values(['Category', 'Date'], ascending=[True, False])
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Title (KR)'])
        
        # Clear progress indicators
        progress.empty()
        status.empty()
        
        # Display results with markdown
        st.subheader("📊 Results")
        st.markdown(
            df.to_markdown(index=False),
            unsafe_allow_html=True
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
