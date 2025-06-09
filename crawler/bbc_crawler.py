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
    'innovation' : '3da03ce0-ee41-4427-a5d9-1294491e0448'
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}
SIZE = 9

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

def is_end(date, end_time):
    date_dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    end_time_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")
    return date_dt <= end_time_dt

def get_datetime(time):
    dt = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")

def get_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    content_divs = soup.find_all('div', attrs={'data-component': 'text-block'})
    contents = [div.get_text(strip=True) for div in content_divs]
    full_content = '\n'.join(contents) if contents else None

    return full_content

def get_articles(page, collection_id, end_time):
    params = {
        'page': page,
        'size': SIZE,
    }

    response = requests.get(BASE_URL + collection_id, params=params, headers=HEADERS)

    if not response:
        return []

    datas = response.json().get('data')
    articles = []

    for data in datas:
        # article 타입이 아니면 무시
        if data.get('type') != 'article':
            continue

        date = get_datetime(data['firstPublishedAt'])   

        # DB의 마지막 날짜를 만나면 중지
        if end_time and is_end(date, end_time):
            break
        
        url = "https://www.bbc.com" + data['path']
        content = get_content(url)
        title, content, keyword = summarize_and_categorize_issue(data['title'], content) 
        image = data['indexImage']['model']['blocks']['src'] or None

        articles.append(
            {
                'content': content,
                'image_url': image,
                'issue_date': date,
                'keyword': keyword,
                'site_url': url,
                'title': title,
            }
        )
        print(f"[BBC] 크롤링 완료 : {title}")  

    return articles

def crawl():
    print("[BBC] 크롤링 시작")
    results = []
    last_issue_date = get_last_issue_date()

    if last_issue_date:
        print(f"[BBC] DB의 마지막 이슈 이후 데이터만 크롤링 시작 (DATE : {last_issue_date})")
    else:
        print(f"[BBC] DB에 이슈 없음, 모든 데이터 크롤링 시작")

    for category, collection_id in COLLECTIONS.items():
        # print(f"[BBC] 카테고리 {category} :")
        page = 0
        
        while True:
            articles = get_articles(page, collection_id, last_issue_date)

            if not articles:
                break

            results.extend(articles)
            page += 1

    if results:
        # 중복된 site_url 제거
        unique_results = {}
        for article in results:
            unique_results[article['site_url']] = article
        results = list(unique_results.values())
        print(f"[BBC] 크롤링 완료 : {len(results)}개의 이슈를 크롤링했습니다.")
        save_issues(results)
    else:
        print("[BBC] 크롤링 완료 : 새로운 이슈가 없습니다.")

if __name__ == '__main__':
    crawl()