import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re

# 경상남도교육청 통합공공도서관 공지사항 URL
base_url = "https://gnelib.gne.go.kr"
url = f"{base_url}/boardNoticeMerge.es?mid=a10701000000"

# 1. 웹페이지 가져오기 (봇 차단 우회를 위한 헤더 추가)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

print("경상남도교육청 통합공공도서관 접속 중...")
response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()
soup = BeautifulSoup(response.text, 'html.parser')

# 2. RSS 피드 생성기 초기화
fg = FeedGenerator()
fg.id(url)
fg.title('경상남도교육청 통합공공도서관 공지사항 RSS')
fg.author({'name': '경상남도교육청 통합공공도서관'})
fg.link(href=url, rel='alternate')
fg.description('경상남도교육청 산하 통합공공도서관의 최신 공지사항을 제공합니다.')
fg.language('ko')

# 3. 게시판 목록 파싱 (표 형태)
# 보통 <table> 안의 <tbody> 안의 <tr> 들이 각각의 게시글입니다.
rows = soup.select('table tbody tr')
items_found = 0

for row in rows:
    # 각 줄(tr) 안의 칸(td)들을 가져옵니다.
    cols = row.find_all('td')
    
    # 데이터가 비어있거나(예: '게시글이 없습니다'), 열 개수가 부족하면 패스
    if len(cols) < 5:
        continue

    # 이미지 구조상: 0:번호, 1:제목, 2:작성자(도서관명), 3:작성일자, 4:첨부, 5:조회수
    title_element = cols[1].find('a')
    if not title_element:
        continue

    # 제목 정제 (도서관 뱃지 텍스트가 a 태그 안에 함께 있을 수 있으므로 여백 정리)
    title = title_element.get_text(separator=' ', strip=True)
    author = cols[2].get_text(strip=True)
    date_str = cols[3].get_text(strip=True) # 2026/03/27 형식
    
    # 제목에 작성자(도서관명)를 말머리처럼 추가해 주면 구독할 때 보기 좋습니다.
    display_title = f"[{author}] {title}"

    # 링크 추출 및 정제
    href = title_element.get('href', '')
    
    # 링크가 상대경로(/boardNoticeMerge...)인 경우 절대경로로 변환
    if href.startswith('/'):
        link = base_url + href
    # 자바스크립트 함수(예: javascript:fn_view(1234))로 되어 있는 경우 처리
    elif 'javascript' in href or href == '#':
        onclick = title_element.get('onclick', '')
        nums = re.findall(r"\d+", onclick)
        if nums:
            # 게시글 번호를 추출하여 직접 주소 조립 (사이트 구조에 따라 파라미터가 다를 수 있음)
            # 보통 &act=view&boardNo=번호 와 같은 형태를 띕니다.
            link = f"{url}&act=view&boardNo={nums[0]}"
        else:
            link = f"{url}#{hash(title)}"
    else:
        link = base_url + "/" + href

    # 4. RSS 엔트리 추가
    fe = fg.add_entry()
    fe.id(link)
    fe.title(display_title)
    fe.link(href=link)
    
    # 날짜 적용 (YYYY/MM/DD 형식)
    if date_str:
        try:
            # 2026/03/27 형식을 파싱
            date_str_clean = date_str.replace('.', '/').replace('-', '/')
            dt = datetime.strptime(date_str_clean, '%Y/%m/%d')
            kst = pytz.timezone('Asia/Seoul')
            dt = kst.localize(dt)
            fe.pubDate(dt)
        except ValueError:
            pass
            
    items_found += 1

print(f"탐색 완료: 총 {items_found}개의 공지사항을 찾았습니다.")

# 5. XML 파일로 저장
xml_filename = 'gne_rss.xml'
fg.rss_file(xml_filename)
print(f"RSS 피드 생성 완료: {xml_filename}")
