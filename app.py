import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
import re
from urllib.parse import urlparse
from database import init_db, save_article, get_articles_by_date, save_keyword, get_keywords, remove_keyword, get_scraped_dates
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="🌊 CIP Korea News Monitor", layout="wide")

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
        st.error(f"⚠️ Timeout while accessing {url}. Using current date.")
        return datetime.now().strftime('%Y-%m-%d')
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Error accessing {url}: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d')
    except Exception as e:
        st.error(f"⚠️ Unexpected error processing {url}: {str(e)}")
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
    """Get detailed OpenAI analysis of the article"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are a professional news analyst specializing in Korean energy industry news.
                Provide detailed analysis in the following format:
                1. English Title: Direct but natural English translation
                2. Synopsis: Detailed 4-5 sentence summary organized in 1-2 paragraphs. Focus on key points, implications, and context
                3. Category: Classify into EXACTLY ONE of: CIP, Govt Policy, Local Govt Policy, Stakeholders, RE Industry
                4. Stakeholders: List main organizations/entities mentioned (comma-separated)"""},
                {"role": "user", "content": f"Analyze this Korean news title: {title}"}
            ],
            temperature=0.5
        )
        
        analysis = response.choices[0].message.content
        
        # Parse the response
        english_title = ""
        synopsis = ""
        category = ""
        stakeholder = ""
        
        sections = analysis.split('\n')
        for section in sections:
            if section.startswith("1. English Title:"):
                english_title = section.replace("1. English Title:", "").strip()
            elif section.startswith("2. Synopsis:"):
                synopsis = section.replace("2. Synopsis:", "").strip()
            elif section.startswith("3. Category:"):
                category = section.replace("3. Category:", "").strip()
            elif section.startswith("4. Stakeholders:"):
                stakeholder = section.replace("4. Stakeholders:", "").strip()
        
        return {
            'english_title': english_title,
            'synopsis': synopsis,
            'category': category,
            'stakeholder': stakeholder
        }
    except Exception as e:
        st.error(f"Error in analysis: {str(e)}")
        return {
            'english_title': 'Analysis Failed',
            'synopsis': 'Error during analysis',
            'category': 'Unknown',
            'stakeholder': 'Unknown'
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
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().lower() == 'yes'
    except:
        return True  # Default to True in case of API error

def validate_news_relevance(article):
    """Simplified relevance check to avoid over-filtering"""
    # Basic checks for empty or invalid content
    if not article.get('title') or not article.get('url'):
        return False
    
    # Accept most articles that made it through the keyword search
    return True

def display_agent_status(status_container, stats_container, phase, message, details=None):
    """Display professional AI agent status in a single organized container"""
    with status_container:
        st.empty()  # Clear previous status
        
        # Status header with phase indicator
        col1, col2 = st.columns([1, 4])
        with col1:
            if phase == "initialize":
                st.info("🤖 Initializing")
            elif phase == "search":
                st.info("🔍 Searching")
            elif phase == "analyze":
                st.info("🧠 Analyzing")
            elif phase == "complete":
                st.success("✅ Complete")
        
        with col2:
            st.write(message)
            if details:
                st.caption(details)

def scrape_news(date_range):
    """Scrape news for a date or range of dates"""
    if isinstance(date_range, tuple):
        start_date, end_date = date_range
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Only weekdays
                _scrape_single_date(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
    else:
        _scrape_single_date(date_range)

def _scrape_single_date(target_date):
    """Scrape news for a single date"""
    status_container = st.empty()
    stats_container = st.empty()
    
    display_agent_status(status_container, stats_container, "Initialization", "Starting news scraping...")
    
    # Get all keywords
    keywords = get_keywords()
    if not keywords:
        st.warning("⚠️ No keywords defined. Please add some keywords first.")
        return
    
    # Initialize counters
    total_articles = 0
    saved_articles = 0
    
    # Search for each keyword
    for keyword in keywords:
        display_agent_status(status_container, stats_container, "Searching", f"Looking for articles with keyword: {keyword}")
        
        articles = search_news(keyword, target_date)
        total_articles += len(articles)
        
        for article in articles:
            if not validate_news_relevance(article):
                continue
                
            try:
                # Get OpenAI analysis
                analysis = get_analysis(article['title'])
                
                # Add analysis results to article data
                article.update(analysis)
                
                # Save to database
                if save_article(article):
                    saved_articles += 1
                    
            except Exception as e:
                st.error(f"Error processing article: {str(e)}")
                continue
    
    # Final status update
    display_agent_status(
        status_container,
        stats_container,
        "Complete",
        f"✅ Scraping complete for {target_date}",
        f"Found {total_articles} articles, saved {saved_articles} relevant ones."
    )

def display_news(date):
    st.subheader(f"📊 News Analysis Results - {date.strftime('%Y-%m-%d (%A)')}")
    
    articles_df = get_articles_by_date(date.strftime('%Y-%m-%d'))
    
    if not articles_df.empty:
        # Filter to ensure only articles from the correct date
        articles_df = articles_df[articles_df['date'] == date.strftime('%Y-%m-%d')]
        
        if not articles_df.empty:
            # Add analysis explanation
            st.info("""
            🤖 **AI Analysis Details**
            Each article has been analyzed with the following information:
            - 📝 Korean Title: Original article title
            - 🌐 English Title: AI-translated title
            - 📰 Media: Source media outlet
            - 📋 Synopsis: Detailed 4-5 sentence summary in English
            - 📅 Date: Publication date
            - 🏷️ Category: One of: CIP, Govt Policy, Local Govt Policy, Stakeholders, RE Industry
            - 👥 Stakeholders: Key organizations or entities mentioned
            - 🔗 Link: Direct link to the original article
            """)
            
            # Make URLs clickable
            def make_clickable(url):
                return f'<a href="{url}" target="_blank">🔗 Link</a>'
            
            # Ensure all required columns exist
            if 'english_title' not in articles_df.columns:
                articles_df['english_title'] = ''
            
            # Select available columns
            columns = ['title', 'english_title', 'media_name', 'synopsis', 'date', 'category', 'stakeholder', 'url']
            display_df = articles_df[columns]
            
            # Rename columns
            display_df.columns = ['📝 Korean Title', '🌐 English Title', '📰 Media', '📋 Synopsis', '📅 Date', '🏷️ Category', '👥 Stakeholders', '🔗 Link']
            
            # Convert URLs to clickable links
            display_df['🔗 Link'] = display_df['🔗 Link'].apply(make_clickable)
            
            # Display table with HTML rendering
            st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            # Add export option
            if st.button("📥 Export Results to CSV"):
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download CSV",
                    csv,
                    f"news_analysis_{date.strftime('%Y-%m-%d')}.csv",
                    "text/csv",
                    key='download-csv'
                )
        else:
            st.info("📭 No news articles found for this date. Click 'Scrape News' to fetch articles.")
    else:
        st.info("📭 No news articles found for this date. Click 'Scrape News' to fetch articles.")

def main():
    st.title("🌊 CIP Korea News Monitor")
    
    # Sidebar
    st.sidebar.title("📰 News Management")
    
    # Date selection at the top of sidebar
    st.sidebar.subheader("📅 Select Date")
    
    # Date range selection
    date_selection_mode = st.sidebar.radio("Date Selection Mode", ["Single Date", "Date Range"])
    
    today = datetime.now().date()
    if date_selection_mode == "Single Date":
        selected_date = st.sidebar.date_input(
            "Choose a date",
            today,
            max_value=today
        )
    else:
        col1, col2 = st.sidebar.columns(2)
        start_date = col1.date_input(
            "Start Date",
            today - timedelta(days=7),
            max_value=today
        )
        end_date = col2.date_input(
            "End Date",
            today,
            min_value=start_date,
            max_value=today
        )
        if start_date > end_date:
            st.sidebar.error("End date must be after start date")
            selected_date = None
        else:
            selected_date = (start_date, end_date)
    
    # Previously scraped dates dropdown
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Previously Scraped")
    scraped_dates = get_scraped_dates()
    if scraped_dates:
        selected_scraped_date = st.sidebar.selectbox(
            "Select a date to view",
            scraped_dates,
            format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%Y-%m-%d (%A)')
        )
    else:
        st.sidebar.text("No previously scraped dates")
        selected_scraped_date = None
    
    st.sidebar.markdown("---")
    
    # Scrape News button
    if selected_date and st.sidebar.button("🔍 Scrape News"):
        scrape_news(selected_date)
    
    # Add new keyword right under scrape news
    new_keyword = st.sidebar.text_input("✨ Add new keyword", placeholder="Type new keyword here...")
    if st.sidebar.button("➕ Add Keyword"):
        if new_keyword:
            save_keyword(new_keyword)
            st.sidebar.success(f"✅ Added: {new_keyword}")
    
    st.sidebar.markdown("---")
    
    # Show existing keywords
    st.sidebar.subheader("🔑 Current Keywords")
    
    # Default keywords - add them to database if not present
    default_keywords = [
        "CIP", "Climate Investment Partnership", "기후투자동반자",
        "그린수소", "재생에너지", "탄소중립", "에너지전환",
        "해상풍력", "풍력발전", "신재생에너지", "재생에너지",
        "해상풍력단지", "부유식", "고정식", "풍력",
        "Copenhagen Infrastructure Partners", "Copenhagen Offshore Partners",
        "코펜하겐 인프라스트럭처", "코펜하겐 오프쇼어"
    ]
    
    # Add default keywords to database if they don't exist
    for keyword in default_keywords:
        save_keyword(keyword)
    
    # Display all keywords with remove option
    all_keywords = get_keywords()
    for keyword in all_keywords:
        col1, col2 = st.sidebar.columns([4, 1])
        col1.markdown(f"🔸 {keyword}")
        if col2.button("🗑️", key=f"remove_{keyword}", help=f"Remove {keyword}"):
            if remove_keyword(keyword):
                st.rerun()
    
    # Add a button to restore default keywords
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Restore Default Keywords"):
        for keyword in default_keywords:
            save_keyword(keyword)
        st.rerun()
    
    # Add a button to remove all keywords
    if st.sidebar.button("🗑️ Remove All Keywords"):
        for keyword in all_keywords:
            remove_keyword(keyword)
        st.rerun()
    
    # Main content area
    if selected_scraped_date:
        display_news(selected_scraped_date)
    elif isinstance(selected_date, tuple):
        # For date range, show the most recent date's news
        display_news(selected_date[1].strftime('%Y-%m-%d'))
    else:
        display_news(selected_date.strftime('%Y-%m-%d'))

if __name__ == "__main__":
    main()
