import requests
from crawler.llm_processor import summarize_and_categorize_issue
from crawler.save_to_db import save_issues
from bs4 import BeautifulSoup
from datetime import datetime
from server.db import run_query

BASE_URL = 'https://web-cdn.api.bbci.co.uk/xd/content-collection/'
COLLECTIONS = {
    'natural-wonders' : '9f0b9075-b620-4859-abdc-ed042dd9ee66',
    'weather-science' : '696fca43-ec53-418d-a42c-067cb0449ba9',
    'climate-solutions' : '5fa7bbe8-5ea3-4bc6-ac7e-546d0dc4a16b',
    'world' : '07cedf01-f642-4b92-821f-d7b324b8ba73',
    'innovation' : '3da03ce0-ee41-4427-a5d9-1294491e0448',
    'business' : 'daa2a2f9-0c9e-4249-8234-bae58f372d82'
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}
SIZE = 9
REQUEST_TIMEOUT = 10 # 요청 타임아웃을 상수로 정의

# 이 함수는 더 이상 필터링 목적으로 사용되지 않습니다. (참고용으로 남겨둠)
def get_last_issue_date():
    sql = """
        SELECT MAX(issue_date) AS max_date
        FROM issues;
    """
    result = run_query(sql)

    if result and result[0]['max_date']:
        dt = result[0]['max_date']
        latest_issue_date = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        return latest_issue_date
    else:
        return None

def get_existing_site_urls():
    """
    데이터베이스의 issues 테이블에서 모든 site_url을 검색합니다.
    효율적인 조회를 위해 URL 세트를 반환합니다.
    """
    sql = """
        SELECT site_url
        FROM issues;
    """
    results = run_query(sql)
    if results:
        # 각 딕셔너리에서 site_url을 추출하여 set에 추가
        return {row['site_url'] for row in results}
    else:
        return set() # URL이 없으면 빈 set 반환

# 이 함수는 더 이상 사용되지 않습니다.
def is_end(date, end_time):
    date_dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    end_time_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")
    return date_dt <= end_time_dt

def get_datetime(time):
    dt = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")

def get_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT) # 타임아웃 사용
        response.raise_for_status() # 200 이외의 응답에 대해 예외 발생
        soup = BeautifulSoup(response.content, "html.parser")
        content_divs = soup.find_all('div', attrs={'data-component': 'text-block'})
        contents = [div.get_text(strip=True) for div in content_divs]
        full_content = '\n'.join(contents) if contents else None
        return full_content
    except requests.exceptions.RequestException as e:
        print(f"[BBC] URL '{url}' 에서 내용을 가져오는 중 오류 발생: {e}")
        return None
    except Exception as e: # 기타 예상치 못한 오류 처리
        print(f"[BBC] URL '{url}' 에서 내용을 가져오는 중 알 수 없는 오류 발생: {e}")
        return None


def get_articles(page, collection_id, existing_urls):
    """
    지정된 페이지에서 기사를 가져옵니다.
    반환: (새로운 기사 리스트, API가 해당 페이지에 데이터를 반환했는지 여부)
    """
    params = {
        'page': page,
        'size': SIZE,
    }

    try:
        response = requests.get(BASE_URL + collection_id, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status() # 200 이외의 응답에 대해 예외 발생
    except requests.exceptions.RequestException as e:
        print(f"[{collection_id}] 페이지 {page} 기사 가져오기 오류: {e}")
        return [], False # API 호출 실패: 데이터 반환 여부 False
    except Exception as e: # 기타 예상치 못한 오류 처리
        print(f"[{collection_id}] 페이지 {page} 기사 가져오는 중 알 수 없는 오류 발생: {e}")
        return [], False # API 호출 실패: 데이터 반환 여부 False

    datas = response.json().get('data')

    # API 자체가 이 페이지에 데이터를 반환하지 않은 경우
    if not datas:
        return [], False # 새로운 기사 없음, API도 데이터 없음

    newly_found_articles = []

    for data in datas:
        # article 타입이 아니면 무시
        if data.get('type') != 'article':
            continue

        url = "https://www.bbc.com" + data['path']

        # URL이 이미 DB에 존재하는지 확인
        if url in existing_urls:
            # print(f"[BBC] 중복된 URL 무시: {url}") # 선택 사항: 디버깅용
            continue # DB에 이미 있는 기사는 건너뛰기

        date = get_datetime(data['firstPublishedAt'])

        content = get_content(url)
        # 페이지 구조가 변경되거나 접근이 거부되어 내용을 가져오지 못할 수 있음
        if not content:
            print(f"[BBC] 경고: '{url}' 에서 내용을 가져올 수 없습니다. 해당 기사를 건너뜁니다.")
            continue

        title, summarized_content, keyword = summarize_and_categorize_issue(data['title'], content)

        # 이미지 URL을 try-except 블록으로 안전하게 접근
        image = None
        try:
            image = data['indexImage']['model']['blocks']['src']
        except (KeyError, TypeError):
            # indexImage, model, blocks, src 중 하나라도 없거나 None이어서 접근 불가 시
            image = None # 이미 None으로 초기화되었지만 명시적으로 다시 할당

        newly_found_articles.append(
            {
                'content': summarized_content, # 요약된 content 사용
                'image_url': image,
                'issue_date': date,
                'keyword': keyword,
                'site_url': url,
                'title': title,
            }
        )
        print(f"[BBC] 크롤링 완료 : {title}")

    return newly_found_articles, True # 새로 발견된 기사 리스트와 API가 데이터가 있었음을 True로 반환

def crawl():
    print("[BBC] 크롤링 시작")
    results = []
    # DB에 있는 모든 기존 URL 가져오기
    existing_urls = get_existing_site_urls()
    print(f"[BBC] DB에 {len(existing_urls)}개의 기존 URL이 있습니다.")

    for category, collection_id in COLLECTIONS.items():
        print(f"[BBC] 카테고리 '{category}' 크롤링 시작...")
        page = 0

        while True:
            # get_articles에서 새로운 기사 리스트와 API 데이터 반환 여부 받기
            articles_on_page, api_had_data_for_page = get_articles(page, collection_id, existing_urls)

            # Case 1: BBC API 자체가 이 페이지에 데이터를 반환하지 않은 경우
            # 즉, 해당 카테고리의 모든 기사를 소진했음을 의미.
            if not api_had_data_for_page:
                print(f"[BBC] 카테고리 '{category}'의 페이지 {page}에서 더 이상 API 데이터가 없습니다. 다음 카테고리로 이동합니다.")
                break # 다음 카테고리로 넘어감

            # Case 2: BBC API는 데이터를 반환했지만, 해당 페이지의 모든 기사가 이미 DB에 있는 중복된 기사인 경우
            if not articles_on_page: # api_had_data_for_page는 True였지만, articles_on_page는 비어있음
                print(f"[BBC] 카테고리 '{category}'의 페이지 {page}에서 새로운 이슈를 찾을 수 없습니다 (모두 중복된 기사). 이전 데이터이므로 다음 페이지를 확인합니다.")
                # break 하지 않고, page를 증가시켜 다음 페이지를 계속 확인
            else:
                # Case 3: 새로운 기사를 발견한 경우
                results.extend(articles_on_page)
                # 새로 발견된 URL들을 existing_urls set에 추가하여, 동일한 크롤링 실행 내에서 중복 방지
                for article in articles_on_page:
                    existing_urls.add(article['site_url'])
                print(f"[BBC] 카테고리 '{category}' 페이지 {page}에서 {len(articles_on_page)}개의 새 이슈를 발견했습니다.")

            page += 1 # 페이지 증가 (중복 기사만 있는 경우에도 증가)

    if results:
        print(f"[BBC] 최종적으로 {len(results)}개의 새로운 이슈를 크롤링했습니다.")
        save_issues(results)
    else:
        print("[BBC] 크롤링 완료 : 새로운 이슈가 없습니다.")

if __name__ == '__main__':
    crawl()