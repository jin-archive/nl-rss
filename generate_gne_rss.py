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
rows = soup.select('table tbody tr')
items_found = 0

# 중요: 웹페이지의 목록(최신순)을 뒤집어서 과거 글부터 RSS에 추가합니다.
# 그래야 RSS 리더기에서 가장 최근에 추가된(원래 웹페이지의 맨 위) 글이 최상단에 노출됩니다.
for row in reversed(rows):
    cols = row.find_all('td')
    
    # 데이터가 비어있거나, 열 개수가 부족하면 패스
    if len(cols) < 5:
        continue

    title_element = cols[1].find('a')
    if not title_element:
        continue

    # 제목 정제
    title = title_element.get_text(separator=' ', strip=True)
    author = cols[2].get_text(strip=True)
    date_str = cols[3].get_text(strip=True) 
    
    display_title = f"[{author}] {title}"

    # 링크 추출 및 정제
    href = title_element.get('href', '')
    
    if href.startswith('/'):
        link = base_url + href
    elif 'javascript' in href or href == '#':
        onclick = title_element.get('onclick', '')
        nums = re.findall(r"\d+", onclick)
        if nums:
            link = f"{url}&act=view&boardNo={nums[0]}"
        else:
            link = f"{url}#{hash(title)}"
    else:
        link = base_url + "/" + href

    # URL의 '&' 기호가 XML에서 오류를 일으킬 수 있으므로 안전하게 처리 (feedgen이 자동으로 처리하지만 확실히 하기 위함)
    link = link.replace('&amp;', '&')

    # 4. RSS 엔트리 추가
    fe = fg.add_entry()
    fe.id(link)
    fe.title(display_title)
    fe.link(href=link)
    
    # 날짜 적용
    if date_str:
        try:
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
