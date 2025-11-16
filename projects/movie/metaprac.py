import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict


def fetch_html(url: str, timeout: int = 10) -> str:
    """
    주어진 URL에서 HTML을 가져오는 함수
    - 역할: HTTP GET으로 HTML을 받아와 문자열로 반환
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_books(html: str, base_url: str) -> List[Dict[str, str]]:
    """
    Books to Scrape 목록 페이지에서 책 이미지/제목/가격을 파싱하는 함수
    - 역할: 각 책 카드를 순회하며 필요한 필드를 구조화해 반환
    """
    soup = BeautifulSoup(html, "html.parser")
    books: List[Dict[str, str]] = []

    for card in soup.select("article.product_pod"):
        # 제목: h3 > a 의 title 속성
        a = card.select_one("h3 a")
        title = a.get("title", "").strip() if a else ""

        # 가격: p.price_color 텍스트
        price_el = card.select_one("p.price_color")
        price = price_el.get_text(strip=True) if price_el else ""

        # 이미지: img[src] 상대경로 -> 절대경로로 변환
        img_el = card.select_one("img")
        img_src = img_el.get("src", "").strip() if img_el else ""
        # src가 상대경로('../../...')이므로 절대경로로 보정
        image_url = urljoin(base_url, img_src)

        books.append(
            {
                "title": title,
                "price": price,
                "image_url": image_url,
            }
        )

    return books


def parse_book_detail(html: str, base_url: str) -> Dict[str, str]:
    """
    Books to Scrape의 '개별 도서 상세 페이지'에서 이미지/제목/가격을 파싱하는 함수
    - 역할: 상세 페이지 구조(.product_main, #product_gallery)를 기준으로 1건만 반환
    """
    soup = BeautifulSoup(html, "html.parser")

    # 제목
    title_el = soup.select_one(".product_main h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # 가격
    price_el = soup.select_one(".product_main .price_color")
    price = price_el.get_text(strip=True) if price_el else ""

    # 이미지 (상세 페이지의 갤러리)
    img_el = soup.select_one("#product_gallery img") or soup.select_one(".carousel-inner .item.active img") or soup.select_one(".thumbnail img")
    img_src = img_el.get("src", "").strip() if img_el else ""
    image_url = urljoin(base_url, img_src) if img_src else ""

    return {
        "title": title,
        "price": price,
        "image_url": image_url,
    }


if __name__ == "__main__":
    base_url = "https://books.toscrape.com/"
    html = fetch_html(base_url)
    books = parse_books(html, base_url)

    # 상위 10개만 샘플 출력
    for i, b in enumerate(books[:10], start=1):
        print(f"{i}. {b['title']} | {b['price']} | {b['image_url']}")
