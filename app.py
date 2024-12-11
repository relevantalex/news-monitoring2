import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
import re

st.set_page_config(page_title="CIP Korea News Monitor", layout="wide")

# OpenAI setup
api_key = st.text_input("Enter OpenAI API key:", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

openai.api_key = api_key

# Media translations
KOREAN_MEDIA_TRANSLATIONS = {
    '조선일보': 'Chosun Ilbo',
    '중앙일보': 'JoongAng Ilbo',
    '동아일보': 'Dong-A Ilbo',
    '한국경제': 'Korea Economic Daily',
    '매일경제': 'Maeil Business News',
    '전기신문': 'Electric Times',
    '연합뉴스': 'Yonhap News',
    '한겨레': 'Hankyoreh',
    '경향신문': 'Kyunghyang Shinmun',
    # Add more as needed
}

def get_article_details(url):
    """Get detailed information from article page"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get journalist name
        journalist = "N/A"
        journalist_patterns = [
            soup.select_one('.journalist_name'),
            soup.select_one('.byline'),
            soup.select_one('.author'),
            soup.select_one('span[class*="journalist"]'),
            soup.select_one('div[class*="journalist"]'),
        ]
        
        for pattern in journalist_patterns:
            if pattern:
                journalist = pattern.text.strip()
                if '기자' in journalist:
                    journalist = journalist.replace('기자', '').strip()
                break
        
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
                    # Handle various date formats
                    if 'T' in date_text:
                        date = date_text.split('T')[0]
                    else:
                        # Clean date text
                        date_text = re.sub(r'입력|수정', '', date_text).strip()
                        date = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                    break
                except:
                    continue
                
        return journalist, date
    except Exception as e:
        st.error(f"Error getting article details: {str(e)}")
        return "N/A", datetime.now().strftime('%Y-%m-%d')

def search_news(keyword):
    """Enhanced Naver news search"""
    base_url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.select('.news_area'):
            title = item.select_one('.news_tit').text
            link = item.select_one('.news_tit')['href']
            media = item.select_one('.info_group a').text
            
            # Get detailed info
            journalist, date = get_article_details(link)
            
            # Translate media name
            media_english = KOREAN_MEDIA_TRANSLATIONS.get(media, media)
            
            articles.append({
                'title': title,
                'link': link,
                'media': media_english,
                'journalist': journalist,
                'date': date,
                'keyword': keyword
            })
        return articles
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def translate_journalist(name):
    """Translate journalist name to English"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Translate this Korean name to English using standard romanization: {name}"
            }]
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return name

def get_analysis(title):
    """Get detailed OpenAI analysis"""
    try:
        prompt = f"""Analyze this Korean news title and provide in this exact format:
        
        1. Category: Choose exactly one:
           - CIP (if about Copenhagen Infrastructure Partners or Korean offshore wind projects)
           - Govt policy (if about national government policies)
           - Local govt policy (if about local/regional government policies)
           - Stakeholders (if about industry players, companies, or key individuals)
           - RE Industry (if about general renewable energy industry news)
        
        2. English Title: [Professional translation]
        
        3. Synopsis: Write a detailed 2-3 paragraph summary (4-6 sentences total) covering all key points
        
        Korean Title: {title}
        
        Format your response exactly as:
        Category: [category]
        English Title: [translation]
        Synopsis: [detailed synopsis]"""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message['content']
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return "Error in analysis"

def main():
    st.title("🌊 CIP Korea News Monitor")
    
    # Full keyword list
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
    
    # Custom keyword option
    custom_keyword = st.text_input("Add Custom Keyword")
    if custom_keyword:
        keywords.append(custom_keyword)

    if st.button("🔍 Start Monitoring"):
        progress = st.progress(0)
        status = st.empty()
        
        results = []
        total_keywords = len(keywords)
        
        for idx, keyword in enumerate(keywords):
            status.text(f"Searching for: {keyword}")
            articles = search_news(keyword)
            
            for article in articles:
                status.text(f"Analyzing: {article['title'][:50]}...")
                
                # Get analysis
                analysis = get_analysis(article['title'])
                
                # Parse analysis
                try:
                    category = analysis.split('Category:')[1].split('\n')[0].strip()
                    english_title = analysis.split('English Title:')[1].split('\n')[0].strip()
                    synopsis = analysis.split('Synopsis:')[1].strip()
                    
                    # Translate journalist name
                    english_journalist = translate_journalist(article['journalist'])
                    
                    results.append({
                        'Category': category,
                        'Media': article['media'],
                        'Journalist': english_journalist,
                        'Korean Title': article['title'],
                        'English Title': english_title,
                        'Synopsis': synopsis,
                        'Link': article['link'],
                        'Date': article['date']
                    })
                except:
                    st.error(f"Error processing article: {article['title']}")
            
            progress.progress((idx + 1) / total_keywords)
        
        progress.empty()
        status.empty()
        
        if results:
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Sort by category and date
            category_order = ['CIP', 'Govt policy', 'Local govt policy', 'Stakeholders', 'RE Industry']
            df['Category'] = pd.Categorical(df['Category'], categories=category_order, ordered=True)
            df = df.sort_values(['Category', 'Date'], ascending=[True, False])
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['Korean Title'])
            
            # Display results
            st.subheader("📊 Results")
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Link": st.column_config.LinkColumn("Article Link"),
                    "Korean Title": st.column_config.TextColumn("Korean Title", width="large"),
                    "English Title": st.column_config.TextColumn("English Title", width="large"),
                    "Synopsis": st.column_config.TextColumn("Synopsis", width="large"),
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
