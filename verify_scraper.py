"""News verify."""
from typing import Dict, List

from bs4 import BeautifulSoup
from requests import RequestException, get


class V:
    """News verifier."""

    def __init__(self) -> None:
        """Initialize verifier."""
        self.h = {"User-Agent": "Mozilla/5.0"}

    def verify_coverage(self, d: str) -> List[Dict]:
        """Get verified news."""
        try:
            arts = self._s(d)
            return [a for a in arts if self._v(a)]
        except (RequestException, ValueError):
            return []

    def _s(self, d: str) -> List[Dict]:
        """Search news."""
        try:
            u = "https://search.naver.com/search.naver"
            q = f"{u}?where=news&query=news&sort=1&ds={d}&de={d}"
            r = get(q, headers=self.h, timeout=10)
            s = BeautifulSoup(r.text, "html.parser")
            return self._p(s, d)
        except (RequestException, ValueError):
            return []

    def _p(self, s: BeautifulSoup, d: str) -> List[Dict]:
        """Parse results."""
        r = []
        for i in s.select(".news_area"):
            t = i.select_one(".news_tit")
            if not t:
                continue
            r.append(
                {
                    "date": d,
                    "source": self._e(t["href"]),
                    "title": t.text,
                    "url": t["href"],
                }
            )
        return r

    def _v(self, a: Dict) -> bool:
        """Verify article."""
        try:
            r = get(a["url"], headers=self.h, timeout=10)
            return r.ok
        except RequestException:
            return False

    def _e(self, u: str) -> str:
        """Extract source."""
        try:
            return u.split("/")[2].split(".")[-2].title()
        except IndexError:
            return "?"


if __name__ == "__main__":
    v = V()

    # Verify December 18th articles
    print("\nVerifying December 18th, 2024 articles...")
    v.verify_coverage("2024-12-18")

    # Verify December 12th articles
    print("\nVerifying December 12th, 2024 articles...")
    v.verify_coverage("2024-12-12")
