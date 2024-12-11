import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
import time
import urllib3

# Disable SSL verification warnings
urllib3.disable_warnings()

st.set_page_config(page_title="CIP Korea News Monitor", layout="wide")

# API key input
api_key = st.text_input("Enter your OpenAI API key:", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

# Initialize OpenAI
openai.api_key = api_key

def search_naver_news(keyword, start_date, end_date):
    """Search Naver News with date filtering"""
    base_url = (
        f"https://search.naver.com/search.naver?"
        f"where=news&query={keyword}&sort=1"
        f"&ds={start_date.strftime('%Y.%m.%d')}"
        f"&de={end_date.strftime('%Y.%m.%d')}"
    )
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(base_url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.select('.news_area'):
            title = item.select_one('.news_tit').text
            link = item.select_one('.news_tit')['href']
            media = item.select_one('.info_group a').text
            
            # Try to get the date
            date_elem = item.select_one('.info_group span.info')
            if date_elem and '분 전' not in date_elem.text and '시간 전' not in date_elem.text:
                date = date_elem.text
            else:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Get journalist
            try:
                journalist = item.select_one('.info_group span.journalist').text.replace('기자', '').strip()
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
        articles = []
    
    return articles

def get_category_and_summary(title):
    """Get category and summary using OpenAI"""
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
        
        Korean Title: {title}
        
        Format response as:
        Category: [category]
        English Title: [translation]
        Synopsis: [detailed synopsis]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        result = response.choices[0].message['content']
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
        
        # Search articles
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
            category, title_en, synopsis = get_category_and_summary(article['title'])
            
            results.append({
                'Category': category,
                'Date': article['date'],
                'Media': article['media'],
                'Journalist': article['journalist'],
                'Title (KR)': article['title'],
                'Title (EN)': title_en,
                'Synopsis': synopsis,
                'Link': article['link']
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
