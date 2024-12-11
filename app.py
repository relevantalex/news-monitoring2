import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai

st.set_page_config(page_title="News Monitor", layout="wide")

# OpenAI setup
api_key = st.text_input("Enter OpenAI API key:", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

openai.api_key = api_key

def search_news(keyword):
    """Basic Naver news search"""
    base_url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.select('.news_area'):
            articles.append({
                'title': item.select_one('.news_tit').text,
                'link': item.select_one('.news_tit')['href'],
                'media': item.select_one('.info_group a').text,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'keyword': keyword
            })
        return articles
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def get_analysis(title):
    """Get OpenAI analysis"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Analyze this Korean news title and provide:\n1. Category (CIP/Govt policy/Local govt policy/Stakeholders/RE Industry)\n2. English translation\n3. Brief synopsis\n\nTitle: {title}"
            }]
        )
        return response.choices[0].message['content']
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return "Error in analysis"

def main():
    st.title("News Monitor")
    
    # Keywords
    keywords = st.multiselect(
        "Select Keywords:",
        ['CIP', 'COP', '해상풍력', '전남해상풍력', '청정수소'],
        default=['CIP', '해상풍력']
    )

    if st.button("Search"):
        results = []
        for keyword in keywords:
            articles = search_news(keyword)
            for article in articles:
                analysis = get_analysis(article['title'])
                results.append({
                    'Title': article['title'],
                    'Media': article['media'],
                    'Analysis': analysis,
                    'Link': article['link']
                })
        
        if results:
            df = pd.DataFrame(results)
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Link": st.column_config.LinkColumn()
                }
            )
            
            # Download option
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "Download CSV",
                csv,
                "news_report.csv",
                "text/csv"
            )

if __name__ == "__main__":
    main()
