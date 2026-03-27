import time
import re
import hashlib
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

url = "https://www.nl.go.kr/NL/contents/N50602000000.do"
base_url = "https://www.nl.go.kr"

# 1. 크롬 브라우저 설정 및 접속
print("크롬 브라우저를 시작합니다...")
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("웹페이지에 접속하여 데이터를 기다립니다...")
driver.get(url)
time.sleep(5) # 렌더링 대기

html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')
driver.quit()

# 2. RSS 피드 생성기 초기화
fg = FeedGenerator()
fg.id(url)
fg.title('국립중앙도서관 인재채용 RSS')
fg.author({'name': '국립중앙도서관'})
fg.link(href=url, rel='alternate')
fg.description('국립중앙도서관 인재채용 게시판의 최신 공고를 제공합니다.')
fg.language('ko')

# 3. 데이터 파싱 및 정제
links = soup.find_all('a')
added_links = set()
items_found = 0

for a in links:
    # a 태그 안의 모든 텍스트를 공백으로 띄워 가져옵니다.
    raw_title = a.get_text(separator=' ', strip=True)
    
    # 채용 관련 키워드가 없으면 메뉴 링크이므로 패스
    if not any(k in raw_title for k in ['채용', '공고', '합격', '서류전형', '면접', '근로자']):
        continue

    # 날짜 추출 (2026-03-27 형식)
    date_str = ""
    date_match = re.search(r'(20\d{2})[-./](\d{2})[-./](\d{2})', raw_title)
    if date_match:
        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

    # -----------------------------------
    # 제목 정제 (핵심 로직)
    # -----------------------------------
    title = raw_title
    
    # 1. 앞부분의 '공지'나 '새글' 글자 제거
    title = re.sub(r'^(공지|새글)\s*', '', title)
    
    # 2. 날짜와 그 뒤에 붙어있는 글자(조회수 등)를 통째로 잘라냄
    title = re.sub(r'\s*20\d{2}[-./]\d{2}[-./]\d{2}.*$', '', title).strip()
    
    # 3. 끝부분에 부서명(예: 온라인자료과, 자료보존연구센터)이 중복 표기된 경우 제거
    title = re.sub(r'\s+[가-힣]+과$', '', title).strip()
    title = re.sub(r'\s+[가-힣]+센터$', '', title).strip()

    if len(title) < 5:
        continue

    # -----------------------------------
    # 링크 식별자 고유화 로직 ('#none' 중복 방지)
    # -----------------------------------
    href = a.get('href', '').strip()
    onclick = a.get('onclick', '') or ''

    real_link = ""
    if not href or href in ['#', '#none'] or href.startswith('javascript'):
        # onclick 속성에서 fnDetail('12345') 같은 번호를 찾아 고유 링크 생성
        nums = re.findall(r"\d{4,}", onclick) 
        if nums:
            real_link = f"{url}?seq={nums[0]}"
        else:
            # 번호마저 없다면 제목을 해시(Hash) 처리하여 겹치지 않는 가상 주소 부여
            real_link = f"{url}#{hashlib.md5(title.encode()).hexdigest()[:8]}"
    else:
        if href.startswith('/'):
            real_link = base_url + href
        else:
            real_link = href

    # 고유 링크를 기준으로 중복 방지
    if real_link in added_links:
        continue
    added_links.add(real_link)

    # 4. RSS 항목 추가
    fe = fg.add_entry()
    fe.id(real_link)
    fe.title(title)
    fe.link(href=real_link)

    if date_str:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            kst = pytz.timezone('Asia/Seoul')
            dt = kst.localize(dt)
            fe.pubDate(dt)
        except ValueError:
            pass
            
    items_found += 1

print(f"탐색 완료: 총 {items_found}개의 채용 공고를 찾았습니다.")
fg.rss_file('rss.xml')
