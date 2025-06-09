import re
import httpx
import asyncio
import requests
from bs4 import BeautifulSoup
from server.db import run_query
from crawler.save_to_db import save_activities
from crawler.llm_processor import extract_activity_keyword
from itertools import chain

LIST_ENDPOINT = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do"
DETAIL_ENDPOINT = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do?type=show&progrmRegistNo="
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
DEFAULT_IMAGE_URL = "https://play-lh.googleusercontent.com/9Kheg_iekobkZlP9XzKtwv_j_YL88oVzHCtHe4_hIL3JcQabCL3FFEw4vKzL1XQc8GE"
BATCH_SIZE = 5 # 한번에 BATCH_SIZE개의 HTTP 요청을 보냄
MAX_CRAWL_PAGE = 50 # 크롤링할 페이지 수

async def get_soup(url, params=None):
    """URL에 GET 요청을 보내고 BeautifulSoup 객체를 반환"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=HEADERS)
        return BeautifulSoup(response.text, "html.parser")

def get_exist_ids():
    """DB에서 이미 존재하는 모든 활동 ID들을 리스트로 반환"""
    sql = """
        SELECT CAST(
            SUBSTRING_INDEX(site_url, 'progrmRegistNo=', -1) AS UNSIGNED) AS id
        FROM activities
        WHERE activity_site = "KRVOLUNTEERS"
        ORDER BY id DESC
    """
    result = run_query(sql)
    return [int(row['id']) for row in result] if result else []

def get_last_page():
    """1365사이트의 마지막 페이지 번호를 반환"""
    params = {
                "requstSe": "N",
                "adultPosblAt": "Y",
                "yngbgsPosblAt": "Y",
    }
    response = requests.get(LIST_ENDPOINT, params=params, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    btn_last = soup.find('a', class_='btn_last')
    last_page = btn_last.get('href').split('=')[-1]

    return int(last_page)

def extract_name(soup):
    """상세 페이지에서 활동 이름을 추출"""
    name = soup.select_one('h3.tit_board_view input').get('value')
    return name if name else None

def extract_dates(soup):
    """상세 페이지에서 봉사기간 시작일, 종료일을 추출"""
    period = soup.find('dt', string='봉사기간')
    if period:
        period = period.find_next('dd').text
        start_date, end_date = period.split(' ~ ')
        return start_date.replace('.', '-'), end_date.replace('.', '-')
    return None, None

def extract_content(soup):
    """상세 페이지에서 활동 내용을 추출"""
    pre_tag = soup.find('pre')
    if pre_tag:
        return re.sub(r'[\r\n]+', ' ', pre_tag.get_text(separator="\n", strip=True))
    return ""

async def extract_ids(page):
    """해당 페이지의 활동 ID들을 리스트 형태로 반환"""
    params = {
        "cPage": page,
        "requstSe": "N",
        "adultPosblAt": "Y",
        "yngbgsPosblAt": "Y",
    }
    soup = await get_soup(LIST_ENDPOINT, params=params)
    
    id_list = []
    ul = soup.select_one("ul.list_wrap.wrap2")
    if ul:
        a_tags = ul.find_all("a", href=True)
        for a in a_tags:
            href = a['href']
            match = re.search(r'show\((\d+)\)', href)
            if match:
                id = int(match.group(1))
                id_list.append(id)

    return id_list

async def fetch_detail(id):
    """해당 ID에 해당하는 활동의 상세정보를 추출"""
    url = f"{DETAIL_ENDPOINT}{id}"
    soup = await get_soup(url)
    if not soup:
        return None

    start_date, end_date = extract_dates(soup)
    activity_content = extract_content(soup)
    keyword = extract_activity_keyword(activity_content)
    activity_name = extract_name(soup)

    return {
        "activity_site": "KRVOLUNTEERS",
        "activity_type": "VOLUNTEER",
        "activity_content": activity_content,
        "end_date": end_date,
        "activity_image_url": DEFAULT_IMAGE_URL,
        "keyword": keyword,
        "activity_name": activity_name,
        "site_url": url,
        "start_date": start_date
    }

async def crawl_async():
    """비동기적으로 1365 자원봉사 사이트에서 활동 정보를 수집"""
    last_page = get_last_page()
    start_page = max(last_page - MAX_CRAWL_PAGE, 1)  # 시작할 페이지 계산
    exist_ids = get_exist_ids()
    id_list = []
    activities = []
    print(f"[1365] 최근 {MAX_CRAWL_PAGE} 개의 페이지 ({start_page} ~ {last_page}) 에서 ID 수집중... ")
    
    # ID 수집 (start_page부터 last_page까지 BATCH_SIZE씩 증가)
    for start in range(start_page, last_page + 1, BATCH_SIZE):
        tasks = []
        end = min(start + BATCH_SIZE, last_page + 1)
        
        for current_page in range(start, end):
            tasks.append(extract_ids(current_page))
            
        result = await asyncio.gather(*tasks)
        id_list.extend(chain.from_iterable(result))

    # DB와 비교하여 새로운 ID만 남김
    filtered_id_list = list(set(id_list) - set(exist_ids))
    if not filtered_id_list:
        return []
    print(f"[1365] {len(filtered_id_list)} 개의 새로운 활동 ID 수집 완료")

    # DB에 없는 새로운 활동의 상세정보 수집 (BATCH_SIZE 단위로)
    for i in range(0, len(filtered_id_list), BATCH_SIZE):
        batch = filtered_id_list[i:i + BATCH_SIZE]
        detail_tasks = [fetch_detail(id) for id in batch]
        try:
            print(f"[1365] {len(filtered_id_list)} 개의 활동 중 {i+1} ~ {i+BATCH_SIZE} 의 상세정보 수집 중...")
            results = await asyncio.gather(*detail_tasks)
            # None이 아닌 결과만 추가
            activities.extend([r for r in results if r is not None])
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            continue

    return activities

def crawl():
    """외부 호출용 크롤링 함수"""
    print("[1365] 크롤링 시작")
    activities = asyncio.run(crawl_async())
    if activities:
        print(f"[1365] 크롤링 완료 : {len(activities)}개의 활동을 크롤링했습니다.")
        save_activities(activities)
    else:
        print("[1365] 크롤링 완료 : 새로운 활동이 없습니다.")

if __name__ == '__main__':
    crawl()