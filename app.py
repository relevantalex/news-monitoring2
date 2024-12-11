import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
import re
from urllib.parse import urlparse

st.set_page_config(page_title="CIP Korea News Monitor", layout="wide")

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
        
        # Get journalist name
        journalist = "N/A"
        journalist_patterns = [
            ('span.writer', 'text'),
            ('div.journalist', 'text'),
            ('p.writer', 'text'),
            ('meta[property="article:author"]', 'content'),
            ('span[class*="author"]', 'text'),
        ]
        
        for selector, attr in journalist_patterns:
            element = soup.select_one(selector)
            if element:
                journalist = element.get(attr) if attr == 'content' else element.text
                journalist = re.sub(r'기자|작성자|글', '', journalist).strip()
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
                    # Clean and standardize date
                    date_text = re.sub(r'입력|수정|:|\.', '-', date_text)
                    date_text = re.findall(r'\d{4}-\d{1,2}-\d{1,2}', date_text)[0]
                    date = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                    break
                except:
                    continue
                
        return journalist, date
    except Exception as e:
        st.error(f"Error getting article details: {str(e)}")
        return "N/A", datetime.now().strftime('%Y-%m-%d')

def search_news(keyword, start_date, end_date):
    """Enhanced Naver news search with date filtering"""
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
            
            # Get detailed info
            journalist, date = get_article_details(link)
            
            # Get media name from domain
            media_english = get_english_media_name(link)
            
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
    if name == "N/A" or not name:
        return "N/A"
        
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Translate this Korean name to English using standard romanization. Format as 'Firstname Lastname': {name}"
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
        
        3. Synopsis: Write a very detailed 3-4 paragraph summary (6-8 sentences total) that covers:
           - Main announcement or event
           - Key details and context
           - Implications or impact
           - Relevant stakeholder reactions or next steps
           Make it comprehensive and informative for executives.
        
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

def validate_results(df):
    """Validate and clean results"""
    try:
        # Check categories
        valid_categories = ['CIP', 'Govt policy', 'Local govt policy', 'Stakeholders', 'RE Industry']
        invalid_cats = df[~df['Category'].isin(valid_categories)]['Category'].unique()
        if len(invalid_cats) > 0:
            st.warning(f"Found invalid categories: {invalid_cats}")
        
        # Check dates
        df['Date'] = pd.to_datetime(df['Date'])
        future_dates = df[df['Date'] > datetime.now()]['Date'].unique()
        if len(future_dates) > 0:
            st.warning(f"Found future dates: {future_dates}")
        
        # Check synopsis length
        short_synopsis = df[df['Synopsis'].str.len() < 200]
        if len(short_synopsis) > 0:
            st.warning(f"Found {len(short_synopsis)} articles with short synopsis")
        
        # Check for missing translations
        missing_trans = df[df['English Title'].isnull() | (df['English Title'] == '')]
        if len(missing_trans) > 0:
            st.warning(f"Found {len(missing_trans)} articles with missing translations")
        
        # Check for duplicate articles
        duplicates = df[df.duplicated(subset=['Korean Title'], keep=False)]
        if len(duplicates) > 0:
            st.warning(f"Found {len(duplicates)} duplicate articles")
        
        return df
    except Exception as e:
        st.error(f"Error in validation: {str(e)}")
        return df

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
            articles = search_news(keyword, start_date, end_date)
            
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
            
            # Validate results
            df = validate_results(df)
            
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
