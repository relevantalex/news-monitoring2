"""News verify with Playwright."""
from typing import Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright


class NewsVerifierPlaywright:
    """News verifier using Playwright."""

    def verify_coverage(self, date: str) -> List[Dict]:
        """Get verified news."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                results = [
                    article
                    for article in self._search(page, date)
                    if self._verify(page, article)
                ]
                browser.close()
                return results
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def _search(self, page: Page, date: str) -> List[Dict]:
        """Search news."""
        try:
            url = "https://search.naver.com/search.naver"
            query = f"{url}?where=news&query=news&sort=1&ds={date}&de={date}"
            page.goto(query)
            page.wait_for_selector(".news_area")
            soup = BeautifulSoup(page.content(), "html.parser")
            return self._parse(soup, date)
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def _parse(self, soup: BeautifulSoup, date: str) -> List[Dict]:
        """Parse results."""
        results = []
        for item in soup.select(".news_area"):
            title = item.select_one(".news_tit")
            if not title:
                continue
            results.append(
                {
                    "date": date,
                    "source": self._extract_source(title["href"]),
                    "title": title.text,
                    "url": title["href"],
                }
            )
        return results

    def _verify(self, page: Page, article: Dict) -> bool:
        """Verify article."""
        try:
            return page.goto(article["url"]).ok
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def _extract_source(self, url: str) -> str:
        """Extract source."""
        try:
            return url.split("/")[2].split(".")[-2].title()
        except IndexError:
            return "?"


def main() -> None:
    """Run main."""
    verifier = NewsVerifierPlaywright()
    print("\nVerifying December 18th, 2024 articles...")
    verifier.verify_coverage("2024-12-18")

    print("\nVerifying December 12th, 2024 articles...")
    verifier.verify_coverage("2024-12-12")


if __name__ == "__main__":
    main()
