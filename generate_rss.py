import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re

# 국립중앙도서관 인재채용 URL
url = "https://www.nl.go.kr/NL/contents/N50602000000.do"
base_url = "https://www.nl.go.kr"

# 1. 웹페이지 가져오기
response = requests.get(url)
response.raise_for_status()
soup = BeautifulSoup(response.text, 'html.parser')

# 2. RSS 피드 생성기 초기화
fg = FeedGenerator()
fg.id(url)
fg.title('국립중앙도서관 인재채용 RSS')
fg.author({'name': '국립중앙도서관'})
fg.link(href=url, rel='alternate')
fg.description('국립중앙도서관 인재채용 게시판의 최신 공고를 제공합니다.')
fg.language('ko')

# 3. 게시판 목록 파싱
# 웹사이트의 구조에 따라 CSS 선택자를 조정해야 할 수 있습니다. 
# 일반적인 테이블 형태의 게시판 구조를 기준으로 작성되었습니다.
board_items = soup.select('table tbody tr')

if not board_items:
    # Div 기반 리스트일 경우 대비
    board_items = soup.select('.board_list .item, .list_wrap > div')

for item in board_items:
    title_element = item.select_one('a')
    if not title_element:
        continue
        
    title = title_element.text.strip()
    link = title_element.get('href')
    
    # 상대 경로인 경우 절대 경로로 변환
    if link and link.startswith('/'):
        link = base_url + link
        
    # 날짜 추출 (YYYY-MM-DD 형식의 텍스트 찾기)
    date_str = ""
    date_match = re.search(r'\d{4}-\d{2}-\d{2}', item.text)
    if date_match:
        date_str = date_match.group()

    # RSS 엔트리 추가
    fe = fg.add_entry()
    fe.id(link)
    fe.title(title)
    fe.link(href=link)
    
    # KST 시간대 적용
    if date_str:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            kst = pytz.timezone('Asia/Seoul')
            dt = kst.localize(dt)
            fe.pubDate(dt)
        except ValueError:
            pass

# 4. XML 파일로 저장
fg.rss_file('rss.xml')
print("RSS 피드 생성 완료: rss.xml")
