import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from openai import OpenAI

st.set_page_config(page_title="News Monitor", layout="wide")

# API key input
api_key = st.text_input("Enter your OpenAI API key:", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

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
            
            # Extract date
            date_elem = item.select_one('.info_group span.info')
            date = date_elem.text if date_elem else "N/A"
            
            # Extract journalist
            try:
                journalist = item.select_one('.info_group span.journalist').text
            except:
                journalist = "N/A"
            
            articles.append({
                'title': title,
                'media': media,
                'journalist': journalist,
                'date': date,
                'link': link,
                'keyword': keyword
            })
    except Exception as e:
        st.error(f"Error searching news: {str(e)}")
    
    return articles

def get_category_and_summary(title):
    """Get category and summary using OpenAI"""
    try:
        prompt = f"""Analyze this Korean news article title and provide:
        1. Choose exactly one category from these options:
           - CIP (if about Copenhagen Infrastructure Partners)
           - Govt policy (if about national government policies)
           - Local govt policy (if about local/regional government policies)
           - Stakeholders (if about industry players, companies, or key individuals)
           - RE Industry (if about general renewable energy industry news)
        2. Write a detailed 2-3 sentence synopsis in English
        
        Title: {title}
        
        Format response as:
        Category: [category]
        Synopsis: [synopsis]
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.choices[0].message.content
        category = result.split('Category:')[1].split('\n')[0].strip()
        synopsis = result.split('Synopsis:')[1].strip()
        
        return category, synopsis
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return "N/A", "Error generating summary"

# Main interface
st.title("📰 News Monitor")

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
    'CIP', '한전', '전기위원회',
    '해상풍력', '전남해상풍력',
    '청정수소', '암모니아'
]
keywords = st.multiselect("Select Keywords:", default_keywords, default=default_keywords[:3])

# Custom keyword
custom_keyword = st.text_input("Add Custom Keyword")
if custom_keyword:
    keywords.append(custom_keyword)

if st.button("🔍 Search News"):
    all_articles = []
    progress = st.progress(0)
    status = st.empty()
    
    # Search for each keyword
    for i, keyword in enumerate(keywords):
        status.text(f"Searching for: {keyword}")
        articles = search_naver_news(keyword, start_date, end_date)
        all_articles.extend(articles)
        progress.progress((i + 1)/len(keywords))
    
    # Process articles
    results = []
    total = len(all_articles)
    
    for i, article in enumerate(all_articles):
        status.text(f"Analyzing article {i+1} of {total}")
        category, synopsis = get_category_and_summary(article['title'])
        
        results.append({
            'Category': category,
            'Date': article['date'],
            'Media': article['media'],
            'Journalist': article['journalist'],
            'Synopsis': synopsis,
            'Link': article['link']
        })
        progress.progress((i + 1)/total)
    
    # Create DataFrame and sort by category
    df = pd.DataFrame(results)
    category_order = ['CIP', 'Govt policy', 'Local govt policy', 'Stakeholders', 'RE Industry']
    df['Category'] = pd.Categorical(df['Category'], categories=category_order, ordered=True)
    df = df.sort_values('Category')
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['Synopsis'])
    
    # Clear progress indicators
    progress.empty()
    status.empty()
    
    # Display results
    st.subheader("📊 Results")
    st.dataframe(df, use_container_width=True)
    
    # Download option
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 Download CSV",
        csv,
        f"news_report_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )
