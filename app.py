"""Main Streamlit application for news monitoring."""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from database import DatabaseManager
from verify_scraper import NewsVerifier
from verify_scraper_playwright import NewsVerifierPlaywright

# Initialize database
db = DatabaseManager("news_monitoring.db")

# Set page config
st.set_page_config(page_title="News Monitoring", page_icon="📰", layout="wide")

# Add title
st.title("News Monitoring Dashboard 📰")

# Main content
st.header("Search and Verify Articles")

# Date selection
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.now())
with col2:
    end_date = st.date_input("End Date", datetime.now())

# Search query
search_query = st.text_input("Search Query")

# Action buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("🔍 Search Articles"):
        articles = db.search_articles(
            start=start_date.strftime("%Y-%m-%d") if start_date else None,
            end=end_date.strftime("%Y-%m-%d") if end_date else None,
            query=search_query if search_query else None,
        )

        if not articles:
            st.info("No articles found.")
        else:
            # Display results
            for article in articles:
                with st.expander(article["title"]):
                    st.write(f"**Source:** {article['src']}")
                    st.write(f"**Category:** {article['cat']}")
                    st.write(f"**Date:** {article['pub_date']}")
                    st.write(article["content"])
                    st.markdown(f"[Read More]({article['url']})")

with col2:
    if st.button("🔄 Verify Articles"):
        with st.spinner("Verifying articles..."):
            verifier = NewsVerifierPlaywright()
            basic_verifier = NewsVerifier()

            # Run all verifiers
            articles = []
            for v in [verifier, basic_verifier]:
                try:
                    articles.extend(v.verify_coverage(start_date.strftime("%Y-%m-%d")))
                except Exception as e:
                    st.error(f"Error with verifier {v.__class__.__name__}: {str(e)}")

            # Save to database
            for article in articles:
                db.add_article(article)

            st.success(f"Verified and added {len(articles)} articles!")

# Stats section
st.header("Statistics")
stats = db.get_article_stats(
    start=start_date.strftime("%Y-%m-%d"),
    end=end_date.strftime("%Y-%m-%d"),
)

# Create columns for stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Articles", stats["n"])
with col2:
    st.metric("Categories", stats["c"])
with col3:
    st.metric("Sources", stats["s"])

# Export section
st.header("Export Data")
export_format = st.radio("Export Format", ["CSV", "JSON"], horizontal=True)
if st.button("📥 Export"):
    articles = db.get_articles(
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )

    if export_format == "CSV":
        df = pd.DataFrame(articles)
        st.download_button(
            "Download CSV", df.to_csv(index=False), "news_articles.csv", "text/csv"
        )
    else:
        st.download_button(
            "Download JSON",
            json.dumps(articles, indent=2),
            "news_articles.json",
            "application/json",
        )
