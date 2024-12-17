import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
import re
from urllib.parse import urlparse
from database import init_db, save_article, get_articles_by_date, save_keyword, get_keywords

st.set_page_config(page_title="CIP Korea News Monitor", layout="wide")

# Initialize database
init_db()

# OpenAI setup
api_key = st.text_input("Enter OpenAI API key:", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

openai.api_key = api_key

def get_english_media_name(url):
    """Get English media name from domain"""
    try:
        domain = urlparse(url).netloc
        # Remove common subdomains and .com/.co.kr
        media_name = domain.split('.')[-2]
        return media_name.capitalize()
    except:
        return domain

def get_article_details(url):
    """Get detailed information from article page"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get date
        date = datetime.now().strftime('%Y-%m-%d')  # default
        date_patterns = [
            ('meta[property="article:published_time"]', 'content'),
            ('meta[name="article:published_time"]', 'content'),
            ('time.date', 'datetime'),
            ('.article_date', 'text'),
            ('.date', 'text'),
        ]
        
        for selector, attr in date_patterns:
            element = soup.select_one(selector)
            if element:
                try:
                    date_text = element.get(attr) if attr == 'content' else element.text
                    date_text = re.sub(r'입력|수정|:|\.', '-', date_text)
                    date_text = re.findall(r'\d{4}-\d{1,2}-\d{1,2}', date_text)[0]
                    date = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                    break
                except:
                    continue
                
        return date
    except Exception as e:
        st.error(f"Error getting article details: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d')

def search_news(keyword, target_date):
    """Enhanced Naver news search with date filtering"""
    base_url = (
        f"https://search.naver.com/search.naver?"
        f"where=news&query={keyword}&sort=1"
        f"&ds={target_date}&de={target_date}"
    )
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(base_url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.select('.news_area'):
            title = item.select_one('.news_tit').text
            link = item.select_one('.news_tit')['href']
            
            # Get article date and validate
            article_date = get_article_details(link)
            if article_date != target_date:
                continue
                
            media_name = get_english_media_name(link)
            
            articles.append({
                'title': title,
                'url': link,
                'media_name': media_name,
                'date': article_date
            })
        
        return articles
    except Exception as e:
        st.error(f"Error searching news: {str(e)}")
        return []

def get_analysis(title):
    """Get detailed OpenAI analysis"""
    prompt = f"""Analyze this Korean news article title and provide the following information in JSON format:
    1. A detailed synopsis in English (2-3 sentences)
    2. Category (CIP if related to MOU, contracts, or new projects; otherwise categorize as Government, Industry, or Technology)
    3. Main stakeholder mentioned
    
    Title: {title}
    
    Format:
    {{
        "synopsis": "detailed synopsis here",
        "category": "category here",
        "stakeholder": "main stakeholder here"
    }}"""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return eval(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error in OpenAI analysis: {str(e)}")
        return {
            "synopsis": "Error in analysis",
            "category": "Unknown",
            "stakeholder": "Unknown"
        }

def main():
    st.title("CIP Korea News Monitor")
    
    # Sidebar with weekday tabs
    st.sidebar.title("News by Day")
    
    # Generate weekday dates (excluding future dates)
    today = datetime.now().date()
    dates = []
    current_date = today
    for _ in range(7):  # Look back 7 days
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            dates.append(current_date)
        elif current_date.weekday() == 5:  # Saturday
            next_monday = current_date + timedelta(days=2)
            if next_monday <= today:
                dates.append(next_monday)
        elif current_date.weekday() == 6:  # Sunday
            next_monday = current_date + timedelta(days=1)
            if next_monday <= today:
                dates.append(next_monday)
        current_date = current_date - timedelta(days=1)
    
    dates = sorted(list(set(dates)))  # Remove duplicates and sort
    
    # Create tabs for each date
    tabs = st.tabs([d.strftime('%Y-%m-%d (%A)') for d in dates])
    
    # Default keywords
    default_keywords = [
        "CIP", "Climate Investment Partnership", "기후투자동반자",
        "그린수소", "재생에너지", "탄소중립", "에너지전환"
    ]
    
    # Custom keywords section
    st.sidebar.markdown("---")
    st.sidebar.subheader("Custom Keywords")
    new_keyword = st.sidebar.text_input("Add new keyword:")
    if st.sidebar.button("Add Keyword"):
        if new_keyword:
            save_keyword(new_keyword)
            st.sidebar.success(f"Added keyword: {new_keyword}")
    
    # Combine default and custom keywords
    all_keywords = default_keywords + get_keywords()
    
    # Process each date tab
    for i, (tab, date) in enumerate(zip(tabs, dates)):
        with tab:
            st.write(f"News for {date.strftime('%Y-%m-%d (%A)')}")
            
            if st.button(f"Scrape News", key=f"scrape_{date}"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                all_articles = []
                for idx, keyword in enumerate(all_keywords):
                    status_text.text(f"Searching for keyword: {keyword}")
                    articles = search_news(keyword, date.strftime('%Y-%m-%d'))
                    
                    for article in articles:
                        analysis = get_analysis(article['title'])
                        article.update(analysis)
                        save_article(article)
                    
                    progress = (idx + 1) / len(all_keywords)
                    progress_bar.progress(progress)
                
                status_text.text("Done!")
            
            # Display saved articles for this date
            df = get_articles_by_date(date.strftime('%Y-%m-%d'))
            if not df.empty:
                # Remove journalist column and reorder columns
                display_columns = ['title', 'media_name', 'synopsis', 'category', 'stakeholder', 'url']
                st.dataframe(df[display_columns], use_container_width=True)
            else:
                st.info("No articles found for this date. Click 'Scrape News' to search for articles.")

if __name__ == "__main__":
    main()
