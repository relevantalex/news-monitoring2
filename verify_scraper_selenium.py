"""News scraping module using Selenium.

This module provides functionality for scraping news articles using
Selenium WebDriver for browser automation.
"""

from typing import Dict, Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class NewsScraperSelenium:
    """A class for scraping news articles using Selenium WebDriver."""

    def __init__(self):
        """Initialize the NewsScraperSelenium with Chrome WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def __del__(self):
        """Clean up WebDriver resources."""
        if hasattr(self, "driver"):
            self.driver.quit()

    def scrape_article_content(self, url: str) -> Optional[Dict[str, str]]:
        """Scrape content from a news article URL.

        Args:
            url: The URL to scrape.

        Returns:
            Dictionary containing article content or None if scraping fails.
        """
        try:
            self.driver.get(url)

            # Wait for article content to load
            content = self._extract_content()
            if not content:
                return None

            return {"content": content}

        except Exception as e:
            print(f"Error scraping article: {str(e)}")
            return None

    def _extract_content(self) -> Optional[str]:
        """Extract the main content from the current page.

        Returns:
            Article content as string or None if not found.
        """
        content_selectors = [
            "article",
            ".article-content",
            ".article_body",
            "#article-body",
            ".content",
            ".post-content",
        ]

        for selector in content_selectors:
            try:
                element = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if element:
                    return self._clean_content(element.text)
            except TimeoutException:
                continue

        return None

    def _clean_content(self, text: str) -> str:
        """Clean and format extracted text content.

        Args:
            text: Raw text content to clean.

        Returns:
            Cleaned text content.
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove common noise phrases
        noise_phrases = [
            "Share this article",
            "Follow us on",
            "Related articles",
            "Advertisement",
            "Comments",
        ]

        for phrase in noise_phrases:
            text = text.replace(phrase, "")

        return text.strip()
