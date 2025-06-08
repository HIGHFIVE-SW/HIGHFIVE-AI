import requests
import json
from datetime import datetime, timedelta, timezone
from crawler.llm_processor import extract_activity_keyword
from crawler.save_to_db import save_activities
from server.db import run_query

ENDPOINT = "https://nsv3auess7-dsn.algolia.net/1/indexes/*/queries"
HEADERS = {
    "Content-Type": "application/json",
    "x-algolia-agent": "Algolia for JavaScript (5.20.0); Search (5.20.0); Browser",
    "x-algolia-api-key": "c2730ea10ab82787f2f3cc961e8c1e06",
    "x-algolia-application-id": "NSV3AUESS7"
}
DEFAULT_IMAGE_URL = "https://www.idealist.org/assets/417d88fd628db1c1ac861f3ea8db58c1a159d52a/images/icons/action-opps/action-opps-volunteermatch.svg"

def get_last_timestamp():
    sql = """
        SELECT start_date
        FROM activities
        WHERE activity_site = 'IDEALIST'
        ORDER BY start_date DESC
        LIMIT 1;
    """
    last_timestamp = run_query(sql)

    if last_timestamp:
        dt = last_timestamp[0]['start_date'].replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    else:
        return 0
        
def build_payload(page, type='volunteer', timestamp=0):
    if type == 'volunteer':
        filters = f"actionType:'VOLOP' AND published > {timestamp}"
        index_name = "idealist7-production-action-opps"
    else:
        filters = f"type:'INTERNSHIP' AND published > {timestamp}"
        index_name = "idealist7-production"

    return {
        "requests": [
            {
                "indexName": index_name,
                "facets": ["*"],
                "hitsPerPage": 100,
                "attributesToSnippet": ["description:20"],
                "attributesToRetrieve": ["*"],
                "filters": filters,
                "removeStopWords": True,
                "ignorePlurals": True,
                "advancedSyntax": True,
                "queryLanguages": ["en"],
                "page": page,
                "query": "",
                "getRankingInfo": True,
                "clickAnalytics": True,
                "analytics": True
            }
        ]
    }

def get_url(item):
    url = item.get("url")
    if isinstance(url, str):
        return url
    elif isinstance(url, dict):
        return "https://www.idealist.org" + next(iter(url.values()), "")
    return ""

def get_image(item):
    img = item.get("imageUrl") or DEFAULT_IMAGE_URL
    return img

def get_published(item):
    timestamp = item.get("published")
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')

def get_activities(page, timestamp, type):
    payload = build_payload(page, type, timestamp)
    response = requests.post(ENDPOINT, headers=HEADERS, json=payload)
    
    try:
        data = response.json()["results"][0]["hits"]
    except Exception as e:
        print(f"[!] JSON 파싱 에러: {e}")
        return None

    result = []

    if data:
        for item in data:
            activity_type = "VOLUNTEER" if type=='volunteer' else 'INTERNSHIP'
            activity_content = item.get("description")
            activity_name = item.get("name")
            activity_image_url = get_image(item)
            activity_url = get_url(item)
            start_date = get_published(item)
            end_date = None
            keyword = extract_activity_keyword(activity_content)

            result.append(
                {
                    "activity_site": "IDEALIST",
                    "activity_type": activity_type,
                    "activity_content": activity_content,
                    "end_date": end_date,
                    "activity_image_url": activity_image_url,
                    "keyword": keyword,
                    "activity_name": activity_name,
                    "site_url": activity_url,
                    "start_date": start_date
                }
            )
            print(f"[IDEALIST] 크롤링 완료 : {item.get('name', '')}")
        return result
    else:
        return None

def crawl():
    print("[IDEALIST] 크롤링 시작")
    crawled_activities = []
    last_timestamp = get_last_timestamp()

    if last_timestamp > 0:
        print(f"[IDEALIST] DB의 마지막 활동 이후 데이터만 크롤링 시작 (TIMESTAMP: {last_timestamp})")
    else:
        print(f"[IDEALIST] DB에 활동 없음, 모든 데이터 크롤링 시작")

    for type in ['volunteer', 'internship']:
        page = 0
        while True:
            activities = get_activities(page, last_timestamp, type)
            if not activities:
                break
            crawled_activities.extend(activities)
            page += 1

    if crawled_activities:
        print(f"[IDEALIST] 크롤링 완료 : {len(crawled_activities)}개의 활동을 크롤링했습니다.")
        save_activities(crawled_activities)
    else:
        print("[IDEALIST] 크롤링 완료 : 새로운 활동이 없습니다.") 

if __name__ == "__main__":
    crawl()
