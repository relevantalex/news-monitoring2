"""Main Streamlit application for news monitoring."""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from database import DatabaseManager
from verify_scraper import NewsVerifier
from verify_scraper_playwright import NewsVerifierPlaywright
from verify_scraper_selenium import NewsScraperSelenium

# Initialize database
db = DatabaseManager("news_monitoring.db")

# Set page config
st.set_page_config(page_title="News Monitoring", page_icon="📰", layout="wide")

# Add title
st.title("News Monitoring Dashboard 📰")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Select Page", ["Dashboard", "Verify Articles", "Search", "Categories", "Export"]
)

if page == "Dashboard":
    st.header("Article Statistics")
    stats = db.get_article_stats()

    # Create columns for stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Articles", stats["n"])
    with col2:
        st.metric("Categories", stats["c"])
    with col3:
        st.metric("Sources", stats["s"])

    st.subheader("Date Range")
    st.write(f"From: {stats['d1']} To: {stats['d2']}")

elif page == "Verify Articles":
    st.header("Verify Articles")
    date = st.date_input("Select Date", datetime.now())

    if st.button("Verify Articles"):
        with st.spinner("Verifying articles..."):
            verifier = NewsVerifierPlaywright()
            selenium_verifier = NewsScraperSelenium()
            basic_verifier = NewsVerifier()

            # Run all verifiers
            articles = []
            for v in [verifier, selenium_verifier, basic_verifier]:
                try:
                    articles.extend(v.verify_coverage(date.strftime("%Y-%m-%d")))
                except Exception as e:
                    st.error(f"Error with verifier {v.__class__.__name__}: {str(e)}")

            # Save to database
            for article in articles:
                db.add_article(article)

            st.success(f"Verified and added {len(articles)} articles!")

elif page == "Search":
    st.header("Search Articles")

    # Search filters
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")

    search_query = st.text_input("Search Query")

    if st.button("Search"):
        articles = db.search_articles(
            start=start_date.strftime("%Y-%m-%d") if start_date else None,
            end=end_date.strftime("%Y-%m-%d") if end_date else None,
            query=search_query if search_query else None,
        )

        # Display results
        for article in articles:
            with st.expander(article["title"]):
                st.write(f"**Source:** {article['src']}")
                st.write(f"**Category:** {article['cat']}")
                st.write(f"**Date:** {article['pub_date']}")
                st.write(article["content"])
                st.markdown(f"[Read More]({article['url']})")

elif page == "Categories":
    st.header("Article Categories")
    categories = db.get_categories()

    # Display categories as chips
    st.write("Available Categories:")
    cols = st.columns(4)
    for idx, category in enumerate(categories):
        with cols[idx % 4]:
            st.button(category, key=category)

elif page == "Export":
    st.header("Export Articles")

    format_type = st.selectbox("Export Format", ["CSV", "JSON"])
    date_range = st.date_input("Date Range", value=(datetime.now(), datetime.now()))

    if st.button("Export"):
        start_date, end_date = date_range
        articles = db.get_articles(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
        )

        if format_type == "CSV":
            df = pd.DataFrame(articles)
            st.download_button(
                "Download CSV",
                df.to_csv(index=False),
                "news_articles.csv",
                "text/csv",
            )
        else:
            st.download_button(
                "Download JSON",
                json.dumps(articles, indent=2),
                "news_articles.json",
                "application/json",
            )
