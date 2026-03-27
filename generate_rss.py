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

# 1. 셀레니움(Selenium) 헤드리스 브라우저 설정
print("크롬 브라우저를 시작합니다...")
chrome_options = Options()
chrome_options.add_argument('--headless') # 화면 없이 백그라운드에서 실행
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("웹페이지에 접속하여 데이터를 기다립니다...")
driver.get(url)
time.sleep(5) # 자바스크립트가 리스트를 렌더링할 수 있도록 5초 대기

# 렌더링이 끝난 전체 HTML 가져오기
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

# 3. 유연한 게시글 탐색 (테이블/Div 구조 무관)
links = soup.find_all('a')
added_urls = set()
items_found = 0

for a in links:
    title = a.get_text(strip=True)
    # 제목에 관련 키워드가 있는 링크만 추출
    if not title or not any(keyword in title for keyword in ['채용', '공고', '모집', '합격']):
        continue
        
    link = a.get('href')
    onclick = a.get('onclick') or ''
    
    # href가 '#' 이거나 자바스크립트 함수인 경우, onclick 속성에서 번호 추출
    if not link or link == '#' or link.startswith('javascript'):
        nums = re.findall(r"\d+", onclick)
        link = f"{url}#{nums[0]}" if nums else f"{url}#{hash(title)}"
    elif link.startswith('/'):
        link = base_url + link
        
    # 중복 게시글 방지
    if link in added_urls:
        continue
    added_urls.add(link)

    # 4. 날짜 추출 (부모 태그를 거슬러 올라가며 YYYY-MM-DD 형식 찾기)
    date_str = ""
    parent = a.find_parent()
    for _ in range(4): # 최대 4단계 위까지 탐색
        if not parent: break
        match = re.search(r'\d{4}[-./]\d{2}[-./]\d{2}', parent.get_text(separator=' '))
        if match:
            date_str = match.group().replace('.', '-').replace('/', '-')
            break
        parent = parent.find_parent()

    # 5. RSS 엔트리 추가
    fe = fg.add_entry()
    fe.id(link)
    fe.title(title)
    fe.link(href=link)
    
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

# 6. XML 파일 저장
fg.rss_file('rss.xml')
