import time
import re
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

# 1. 셀레니움 헤드리스 브라우저 설정
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

# 3. 게시글 목록 파싱 (테이블 행 또는 리스트 아이템 찾기)
# 보통 <div class="board_list"> 안의 <ul><li> 이거나 <table><tbody><tr> 입니다.
list_items = soup.select('.board_list tbody tr')
if not list_items:
    list_items = soup.select('.board_list ul li') # 다른 구조일 경우 대비
if not list_items:
    list_items = soup.select('div[class*="list"] > div') # 최후의 수단 (클래스에 list가 포함된 div의 자식 div들)

items_found = 0

for item in list_items:
    # 각 항목에서 가장 주요한 링크(제목 링크) 찾기
    link_element = item.find('a')
    if not link_element:
        continue

    # 제목 정제: <a> 태그 안의 텍스트만 추출 (공지, 새글 등의 뱃지 텍스트 제거)
    title = link_element.get_text(strip=True)
    
    # 만약 '공지' 나 다른 텍스트가 같이 섞여 나오는 경우를 대비한 정제
    # (이미지 상에서 <a> 태그 안에 불필요한 텍스트가 있다면 구조 확인이 더 필요할 수 있습니다)
    
    link = link_element.get('href')
    onclick = link_element.get('onclick') or ''

    # 링크 주소 정리
    if not link or link == '#' or 'javascript' in link:
        # onclick 속성에서 fnDetail('1234') 같은 형태를 찾음
        nums = re.findall(r"\d+", onclick)
        link = f"{url}#{nums[0]}" if nums else f"{url}#{hash(title)}"
    elif link.startswith('/'):
        link = base_url + link

    # 날짜 추출: 2026-03-27 과 같은 형식 찾기
    date_str = ""
    # 전체 텍스트에서 날짜 형식을 검색
    date_match = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}', item.get_text())
    if date_match:
        date_str = date_match.group().replace('.', '-').replace('/', '-')

    # 유효한 제목인지 확인 (빈 제목 방지)
    if len(title) < 5: 
        continue

    # RSS 엔트리 추가
    fe = fg.add_entry()
    fe.id(link)
    fe.title(title)
    fe.link(href=link)
    
    # 시간대 설정
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

# 4. XML 파일 저장
fg.rss_file('rss.xml')
