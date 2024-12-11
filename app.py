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

def search_naver_news(keyword):
    """Search Naver News"""
    base_url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    articles = []
    try:
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for item in soup.select('.news_area'):
            title = item.select_one('.news_tit').text
            media = item.select_one('.info_group a').text
            articles.append({
                'title': title,
                'media': media,
                'keyword': keyword
            })
    except Exception as e:
        st.error(f"Error searching news: {str(e)}")
    
    return articles

def get_summary(title):
    """Get summary using OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", 
                 "content": f"Summarize this news title in one sentence: {title}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return "Error generating summary"

# Main interface
st.title("📰 News Monitor")

# Keywords input
keywords = st.text_input("Enter keywords (separated by comma):", "CIP, 한전, 해상풍력")
keywords = [k.strip() for k in keywords.split(",")]

if st.button("Search News"):
    all_articles = []
    progress = st.progress(0)
    
    # Search for each keyword
    for i, keyword in enumerate(keywords):
        articles = search_naver_news(keyword)
        all_articles.extend(articles)
        progress.progress((i + 1)/len(keywords))
    
    # Get summaries
    results = []
    for i, article in enumerate(all_articles):
        summary = get_summary(article['title'])
        results.append({
            'Media': article['media'],
            'Title': article['title'],
            'Summary': summary,
            'Keyword': article['keyword']
        })
        progress.progress((i + 1)/len(all_articles))
    
    # Display results
    df = pd.DataFrame(results)
    st.dataframe(df)
    
    # Download option
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 Download CSV",
        csv,
        f"news_report_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )
