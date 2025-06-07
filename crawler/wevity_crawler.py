import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from server.db import run_query
from crawler.save_to_db import save_activities
from crawler.llm_processor import extract_activity_keyword

BASE_URL = "https://www.wevity.com"
FILE_NAME = "data/wevity_data.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
MAX_CRAWL_PAGE = 10

def get_soup(url):
    """웹 페이지를 요청하고 BeautifulSoup 객체 반환"""
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")

def is_special_activity(a_tag):
    """SPECIAL 게시물인지 확인"""
    return bool(a_tag.select_one("span.stat.spec"))

def get_latest_activity_id():
    """DB에서 가장 마지막 활동을 조회"""
    sql = """
        SELECT CAST(
            SUBSTRING_INDEX(
                SUBSTRING_INDEX(site_url, 'ix=', -1),
                '&', 1
            ) AS UNSIGNED
        ) as activity_id
        FROM activities 
        WHERE activity_site = "WEVITY"
        ORDER BY activity_id DESC 
        LIMIT 1;
    """
    result = run_query(sql)
    
    if result and result[0][0]:
        return int(result[0][0])
    else:
        return 0

def get_image_url(soup):
    """썸네일 이미지 URL 추출"""
    img_tag = soup.select_one("div.thumb img")
    if not img_tag or not img_tag.has_attr("src"):
        return ""
    img_src = img_tag["src"]
    return BASE_URL + img_src if img_src.startswith("/") else img_src

def get_date_range(soup):
    """접수기간 추출"""
    for li in soup.select("li"):
        if "접수기간" in li.get_text():
            match = re.search(r'(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})', li.get_text())
            if match:
                try:
                    start_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                    end_date = datetime.strptime(match.group(2), "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
                    return start_date, end_date
                except ValueError:
                    pass
    return None, None

def get_activity_type(soup):
    """활동 유형(카테고리) 결정"""
    li_tag = soup.select_one("ul.cd-info-list li")
    
    if li_tag:
        span_tag = li_tag.find("span", class_="tit")
        span_tag.decompose()
        category_text = li_tag.get_text(strip=True)

        if category_text == "대외활동/서포터즈":
            return "SUPPORTERS"
        elif category_text == "봉사활동":
            return "VOLUNTEER"
        else:
            return "CONTEST"
    
def get_activity_urls(list_url, last_activity_id):
    """활동 목록 페이지에서 새로운 활동 URL들을 수집"""
    activity_urls = []
    soup = get_soup(list_url)
    activity_items = soup.select("ul.list li")

    for item in activity_items:
        # 진행 중인 게시물만 처리
        if item.select_one("span.dday.end"):
            continue
            
        link_tag = item.select_one("a")
        if not link_tag:
            continue

        activity_url = BASE_URL + link_tag['href']
        # URL에서 활동 ID 추출
        parsed = urlparse(activity_url)
        query_params = parse_qs(parsed.query)
        current_activity_id = int(query_params.get('ix', ['0'])[0])
        
        # ID값이 ID의 마지막 활동 id보다 크면 추가
        if current_activity_id > last_activity_id:
            activity_urls.append(activity_url)
        # 특별 게시물이 아닌 경우에 ix 값이 작거나 같으면 더 이상 새로운 게시물이 없으므로 종료
        elif not is_special_activity(link_tag):
            return activity_urls

    return activity_urls

def get_activity_detail(url):
    """활동 상세 페이지에서 데이터 추출"""
    try:
        soup = get_soup(url)

        activity_type = get_activity_type(soup)
        activity_content = soup.select_one("#viewContents").get_text(strip=True) or None
        activity_name = soup.select_one("h6.tit").get_text(strip=True) or None
        start_date, end_date = get_date_range(soup)
        activity_image_url = get_image_url(soup)
        keyword = extract_activity_keyword(activity_content)

        return {
            "activity_site": "WEVITY",
            "activity_type": activity_type,
            "activity_content": activity_content,
            "end_date": end_date,
            "activity_image_url": activity_image_url,
            "keyword": keyword,
            "activity_name": activity_name,
            "site_url": url,
            "start_date": start_date
        }

    except Exception as e:
        print(f"[ERROR] {url} 에서 오류 발생: {e}")
        return None

def crawl():
    """위비티 활동 크롤링 실행"""
    print("[WEVITY] 크롤링 시작")
    
    last_activity_id = get_latest_activity_id()

    if last_activity_id > 0:      
        print(f"[WEVITY] DB의 마지막 활동 이후 데이터만 크롤링 시작 (ID : {last_activity_id})")      
    else:
        print(f"[WEVITY] DB에 활동 없음, 모든 데이터 크롤링 시작")

    collected_urls = []
    page = 1

    print("[WEVITY] 페이지별 활동 링크 수집 중...")
    while True and page <= MAX_CRAWL_PAGE:
        paged_url = f"{BASE_URL}/?c=find&s=1&gp={str(page)}"
        try:
            new_urls = get_activity_urls(paged_url, last_activity_id)
            if not new_urls:
                break
            collected_urls.extend(new_urls)
            page += 1
        except Exception as e:
            print(f"[ERROR] 목록 페이지 {paged_url} 에서 오류 발생: {e}")
            break

    crawled_activities = []
    if collected_urls:
        print(f"[WEVITY] {len(collected_urls)}개의 활동 링크 수집 완료")
        print("[WEVITY] 활동 상세내용 크롤링 중...")
        for url in collected_urls:
            activity_data = get_activity_detail(url)
            if activity_data:
                crawled_activities.append(activity_data)
                print(f"[WEVITY] 활동 크롤링 완료 : {activity_data['activity_name']}")
    
    if crawled_activities:
        print(f"[WEVITY] 크롤링 완료 : {len(crawled_activities)}개의 활동을 크롤링했습니다.")
        save_activities(crawled_activities)
    else:
        print("[WEVITY] 크롤링 완료 : 새로운 활동이 없습니다.")

if __name__ == "__main__":
    crawl()
