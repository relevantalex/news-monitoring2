import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
import re
from urllib.parse import urlparse
from database import init_db, save_article, get_articles_by_date, save_keyword, get_keywords
import time

st.set_page_config(page_title="CIP Korea News Monitor", layout="wide")

# Custom CSS for larger table and professional look
st.markdown("""
    <style>
    .stTable {
        font-size: 1rem;
    }
    .agent-status {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .agent-header {
        color: #0068c9;
        font-weight: bold;
    }
    .processing-status {
        margin-top: 10px;
        padding: 10px;
        background-color: #e6f3ff;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, verify=False, timeout=10)
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
    except requests.exceptions.Timeout:
        display_agent_status(f"⚠️ Timeout while accessing {url}. Using current date.")
        return datetime.now().strftime('%Y-%m-%d')
    except requests.exceptions.RequestException as e:
        display_agent_status(f"⚠️ Error accessing {url}: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d')
    except Exception as e:
        display_agent_status(f"⚠️ Unexpected error processing {url}: {str(e)}")
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
    prompt = f"""Analyze this Korean news title and provide the following information in JSON format:
    1. A detailed synopsis in English (2-3 sentences)
    2. Category (CIP if related to MOU, contracts, or new projects; otherwise categorize as Government, Industry, or Technology)
    3. Main stakeholder mentioned
    
    Title: {title}
    
    Respond EXACTLY in this format:
    {{"synopsis": "detailed synopsis here", "category": "category here", "stakeholder": "main stakeholder here"}}"""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        # Get the response text
        response_text = response.choices[0].message.content.strip()
        
        # Handle potential formatting issues
        try:
            # Try direct eval first
            result = eval(response_text)
        except:
            # If eval fails, try to clean up the response
            # Remove any markdown formatting
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            # Ensure proper JSON format
            response_text = response_text.replace('\n', '').replace('  ', ' ')
            result = eval(response_text)
        
        # Validate required fields
        required_fields = ['synopsis', 'category', 'stakeholder']
        if not all(field in result for field in required_fields):
            raise ValueError("Missing required fields in response")
            
        return result
        
    except Exception as e:
        display_agent_status(f"⚠️ Error in OpenAI analysis: {str(e)}")
        return {
            "synopsis": "Error in analysis",
            "category": "Unknown",
            "stakeholder": "Unknown"
        }

def is_korean_news(url, title):
    """Check if the news is from South Korea"""
    korean_domains = ['.kr', '.co.kr', '.com.kr', '.go.kr', '.or.kr']
    if not any(domain in url.lower() for domain in korean_domains):
        return False
    
    # Additional check using OpenAI to verify content relevance
    try:
        prompt = f"""Is this news title related to South Korea? Answer with just 'yes' or 'no':
        Title: {title}"""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().lower() == 'yes'
    except:
        return True  # Default to True in case of API error

def validate_news_relevance(article):
    """Validate if the news is relevant to CIP/COP operations"""
    try:
        prompt = f"""Given the following context about CIP/COP operations:
        "Copenhagen Infrastructure Partners (CIP) and Copenhagen Offshore Partners (COP) are key players in South Korea's renewable energy sector, focusing on offshore wind projects to support the country's ambitious goals for energy independence and carbon neutrality."
        
        Is this news article relevant to their operations? Consider the following article details:
        Title: {article['title']}
        Synopsis: {article['synopsis']}
        Category: {article['category']}
        
        Answer with just 'yes' or 'no'."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().lower() == 'yes'
    except:
        return True  # Default to True in case of API error

def display_agent_status(message, progress=None):
    """Display AI agent status with professional styling"""
    with st.container():
        st.markdown(f"""
        <div class="agent-status">
            <div class="agent-header">🤖 AI Agent Status</div>
            <div class="processing-status">{message}</div>
            </div>
        """, unsafe_allow_html=True)
        if progress is not None:
            st.progress(progress)

def main():
    st.title("CIP Korea News Monitor")
    
    # Move date selection to sidebar
    st.sidebar.title("News by Date")
    
    # Generate dates (newest first)
    today = datetime.now().date()
    dates = []
    current_date = today
    for _ in range(7):
        if current_date.weekday() < 5:
            dates.append(current_date)
        current_date = current_date - timedelta(days=1)
    dates = sorted(dates, reverse=True)  # Sort dates newest first
    
    # Create date selection in sidebar
    selected_date = st.sidebar.selectbox(
        "Select Date",
        dates,
        format_func=lambda x: x.strftime('%Y-%m-%d (%A)')
    )
    
    # Keywords section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Keywords Management")
    
    # Scrape News button
    if st.sidebar.button("🔍 Scrape News"):
        scrape_news(selected_date)
    
    # Add new keyword under scrape news
    new_keyword = st.sidebar.text_input("Add new keyword:")
    if st.sidebar.button("➕ Add Keyword"):
        if new_keyword:
            save_keyword(new_keyword)
            st.sidebar.success(f"Added keyword: {new_keyword}")
    
    # Display news in main area
    display_news(selected_date)

def scrape_news(date):
    default_keywords = [
        "CIP", "Climate Investment Partnership", "기후투자동반자",
        "그린수소", "재생에너지", "탄소중립", "에너지전환"
    ]
    all_keywords = default_keywords + get_keywords()
    
    display_agent_status("Initializing news search...")
    progress_bar = st.progress(0)
    
    all_articles = []
    for idx, keyword in enumerate(all_keywords):
        display_agent_status(f"Searching for keyword: {keyword}", progress=(idx / len(all_keywords)))
        articles = search_news(keyword, date.strftime('%Y-%m-%d'))
        
        for article in articles:
            # Check if it's Korean news
            if not is_korean_news(article['url'], article['title']):
                continue
                
            display_agent_status(f"Analyzing article: {article['title'][:50]}...")
            analysis = get_analysis(article['title'])
            article.update(analysis)
            
            # Validate relevance
            if validate_news_relevance(article):
                save_article(article)
        
        progress_bar.progress((idx + 1) / len(all_keywords))
    
    display_agent_status("News scraping completed! ✅")

def display_news(date):
    articles = get_articles_by_date(date.strftime('%Y-%m-%d'))
    if articles:
        df = pd.DataFrame(articles)
        df = df[['title', 'media_name', 'synopsis', 'category', 'stakeholder', 'url']]
        df.columns = ['Title', 'Media', 'Synopsis', 'Category', 'Stakeholder', 'URL']
        
        # Make table larger
        st.dataframe(df, height=600)
    else:
        st.info("No news articles found for this date. Click 'Scrape News' to fetch articles.")

if __name__ == "__main__":
    main()
