from flask import Flask, render_template, request, jsonify
app = Flask(__name__)

from metaprac import fetch_html, parse_books, parse_book_detail  # 크롤링 유틸(HTML/목록/상세 파싱)
from urllib.parse import urlsplit, urlunsplit
from pymongo import MongoClient

# MongoDB Atlas 연결 (사용자 제공 예시 기반)
# - 역할: 애플리케이션 시작 시 한 번만 연결하여 재사용
client = MongoClient('mongodb+srv://test:sparta@sparta.dko5uap.mongodb.net/?appName=sparta')
db = client.dbsparta

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/movie", methods=["POST"])
def movie_post():
    """
    POST /movie 핸들러
    - 역할: 클라이언트로부터 URL을 받아 해당 페이지를 크롤링하고 결과를 JSON으로 반환
    - 현재는 Books to Scrape 구조(이미지/제목/가격)를 파싱하는 예제
    """
    url_receive = request.form.get('url_give', '').strip()
    # 별점/코멘트는 현재 저장 로직 없이 에코만 함 (향후 DB 연동 시 사용)
    star_receive = request.form.get('star_give', '').strip()
    comment_receive = request.form.get('comment_give', '').strip()

    if not url_receive:
        return jsonify({'msg': 'error', 'error': 'url_give 값이 비어있습니다.'}), 400

    try:
        # base_url 보정: 상대 이미지 경로 보완을 위해 마지막 슬래시를 보존
        parts = urlsplit(url_receive)
        # path가 파일이 아닌 디렉토리 루트처럼 보이면 끝에 슬래시 유지
        if not parts.path or parts.path.endswith('/'):
            base_url = urlunsplit((parts.scheme, parts.netloc, parts.path or '/', '', ''))
        else:
            # 파일 경로인 경우 디렉토리 경로만 base로
            base_url = urlunsplit((parts.scheme, parts.netloc, parts.path.rsplit('/', 1)[0] + '/', '', ''))

        html = fetch_html(url_receive)
        # 1) 상세 페이지 파싱 시도 (사용자가 상세 URL을 준 경우)
        book = parse_book_detail(html, base_url)
        # 2) 상세 페이지가 아니거나 실패 시, 목록 페이지에서 첫 1건만 사용 (폴백)
        if not book.get("title") or not book.get("price") or not book.get("image_url"):
            books_from_list = parse_books(html, base_url)
            if books_from_list:
                book = books_from_list[0]
            else:
                return jsonify({'msg': 'error', 'error': '책 정보를 찾을 수 없습니다. 상세 페이지 URL을 사용해 주세요.'}), 400

        # DB 저장: dbsparta.books 컬렉션에 이미지 URL 기준 upsert
        coll = db.books
        res = coll.update_one(
            {'image_url': book['image_url']},
            {
                '$set': {
                    'title': book['title'],
                    'price': book['price'],
                    'url': url_receive,
                    'star': star_receive,
                    'comment': comment_receive
                }
            },
            upsert=True
        )

        return jsonify({
            'msg': 'success',
            'db': {
                'matched': res.matched_count,
                'modified': res.modified_count,
                'upserted': 1 if res.upserted_id is not None else 0
            },
            'item': book,  # 단일 책 정보
            'echo': {
                'url': url_receive,
                'star': star_receive,
                'comment': comment_receive
            }
        })
    except Exception as e:
        return jsonify({'msg': 'error', 'error': str(e)}), 500

@app.route("/movie", methods=["GET"])
def movie_get():
    """
    GET /movie 핸들러
    - 역할: MongoDB에 저장된 크롤링 결과를 조회하여 반환
    """
    # _id는 프론트에서 사용하지 않으므로 제외
    docs = list(db.books.find({}, {'_id': False}))
    return jsonify({
        'msg': 'success',
        'count': len(docs),
        'items': docs
    })

if __name__ == '__main__':
    app.run('0.0.0.0', port=5003, debug=True)