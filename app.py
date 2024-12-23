"""Main application module for news monitoring.

This module contains the core functionality for the news monitoring app.
"""

from datetime import datetime
from typing import Dict

from flask import Flask, jsonify, request

from database import DatabaseManager
from verify_scraper import NewsVerifier
from verify_scraper_playwright import NewsVerifierPlaywright
from verify_scraper_selenium import NewsScraperSelenium

app = Flask(__name__)
db = DatabaseManager("news_monitoring.db")


@app.route("/health")
def health_check() -> Dict[str, str]:
    """Check if the application is healthy."""
    try:
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.route("/verify", methods=["POST"])
def verify_articles() -> Dict:
    """Verify articles using multiple scrapers."""
    try:
        data = request.get_json()
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        verifier = NewsVerifier()
        playwright_verifier = NewsVerifierPlaywright()
        selenium_verifier = NewsScraperSelenium()

        # Run verification with different scrapers
        results = {
            "standard": verifier.verify_coverage(date),
            "playwright": playwright_verifier.verify_coverage(date),
            "selenium": selenium_verifier.scrape_article_content(date),
        }

        return jsonify(results)
    except Exception as e:
        return {"error": str(e)}


@app.route("/articles", methods=["GET"])
def get_articles() -> Dict:
    """Retrieve articles from the database."""
    try:
        articles = db.get_articles()
        return jsonify({"articles": articles})
    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/search", methods=["GET"])
def search_articles() -> Dict:
    """Search articles based on query parameters."""
    try:
        query = request.args.get("q", "")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        category = request.args.get("category")

        articles = db.search_articles(
            query=query,
            start_date=start_date,
            end_date=end_date,
            category=category,
        )
        return jsonify({"articles": articles})
    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/stats", methods=["GET"])
def get_article_stats() -> Dict:
    """Get statistics about articles in the database."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        stats = db.get_article_stats(start_date=start_date, end_date=end_date)
        return jsonify(stats)
    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/categories", methods=["GET"])
def get_categories() -> Dict:
    """Get list of unique article categories."""
    try:
        categories = db.get_categories()
        return jsonify({"categories": categories})
    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/export", methods=["GET"])
def export_articles() -> Dict:
    """Export articles to a specified format."""
    try:
        format_type = request.args.get("format", "json")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if format_type not in ["json", "csv"]:
            return {"error": "Unsupported export format"}

        articles = db.get_articles(
            start_date=start_date,
            end_date=end_date,
        )

        if format_type == "json":
            return jsonify({"articles": articles})
        else:
            # Handle CSV export
            return {"error": "CSV export not implemented"}

    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/add", methods=["POST"])
def add_article() -> Dict:
    """Add a new article to the database."""
    try:
        data = request.get_json()
        required_fields = ["title", "url", "category"]

        if not all(field in data for field in required_fields):
            return {"error": "Missing required fields"}

        article_id = db.add_article(
            title=data["title"],
            url=data["url"],
            category=data["category"],
            source=data.get("source"),
            published_date=data.get("published_date"),
        )

        return {"id": article_id, "message": "Article added successfully"}
    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/update/<int:article_id>", methods=["PUT"])
def update_article(article_id: int) -> Dict:
    """Update an existing article in the database."""
    try:
        data = request.get_json()
        success = db.update_article(article_id, data)

        if success:
            return {"message": "Article updated successfully"}
        return {"error": "Article not found"}

    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/delete/<int:article_id>", methods=["DELETE"])
def delete_article(article_id: int) -> Dict:
    """Delete an article from the database."""
    try:
        success = db.delete_article(article_id)

        if success:
            return {"message": "Article deleted successfully"}
        return {"error": "Article not found"}

    except Exception as e:
        return {"error": str(e)}


@app.route("/articles/batch", methods=["POST"])
def batch_process_articles() -> Dict:
    """Process multiple articles in a single request."""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return {"error": "Expected a list of articles"}

        results = []
        for article in data:
            try:
                article_id = db.add_article(
                    title=article["title"],
                    url=article["url"],
                    category=article["category"],
                    source=article.get("source"),
                    published_date=article.get("published_date"),
                )
                results.append({"id": article_id, "status": "success"})
            except Exception as e:
                results.append(
                    {
                        "title": article.get("title"),
                        "status": "error",
                        "error": str(e),
                    }
                )

        return jsonify({"results": results})
    except Exception as e:
        return {"error": str(e)}


def run_server() -> None:
    """Start the Flask server."""
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    run_server()
