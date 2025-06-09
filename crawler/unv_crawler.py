import requests
from datetime import datetime
from crawler.llm_processor import extract_activity_keyword
from crawler.save_to_db import save_activities
from server.db import run_query

PAGE_ENDPOINT = "https://app.unv.org/api/doa/doa/SearchDoaAsyncByAzureCognitive"
DETAIL_ENDPOINT = "https://app.unv.org/api/doa/doa/"
URL_BASE = "https://app.unv.org/opportunities/"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
DEFAULT_IMAGE_URL = "https://yt3.googleusercontent.com/ytc/AIdro_m9Ch_jB3G0voGzoFTOIWMxkpivX4xN9g3R_lnLHe9w6Uk=s900-c-k-c0x00ffffff-no-rj"

def get_latest_activity_id():
    query = """
        SELECT CAST(SUBSTRING_INDEX(site_url, '/', -1) AS UNSIGNED) as activity_id
        FROM activities 
        WHERE activity_site = "UNVOLUNTEERS"
        ORDER BY activity_id DESC
        LIMIT 1
    """
    result = run_query(query)
            
    return int(result[0]['activity_id']) if result else 0

def get_total_count():
    payload = {
        "take": 1,
        "skip": 0
    }
    response = requests.post(PAGE_ENDPOINT, headers=HEADERS, json=payload)
    data = response.json()
    total_count = data["value"]["total"]

    return total_count

def iso_to_utc(date_str):
    if not date_str:
        return None
    
    return datetime.fromisoformat(date_str)

def fetch_activity_id_list():
    latest_activity_id = get_latest_activity_id()
    total_count = get_total_count()
    
    # API 요청
    response = requests.post(
        PAGE_ENDPOINT, 
        headers=HEADERS, 
        json={"skip": 0, "take": total_count}
    )
    activities = response.json()["value"]["result"]
    
    # 마지막 활동이 있으면 그 이후의 데이터만, 없으면 전체 데이터를 가져옴
    if latest_activity_id > 0:
        print(f"[UNV] DB의 마지막 활동 이후 데이터만 크롤링 시작 (ID : {latest_activity_id})")
        return [activity["id"] for activity in activities if activity["id"] > latest_activity_id]
    else:
        print(f"[UNV] DB에 활동 없음, 모든 데이터 크롤링 시작")
        return [activity["id"] for activity in activities]

def fetch_activity_detail(activity_id_list):
    activities = []

    for activity_id in activity_id_list:
        response = requests.get(DETAIL_ENDPOINT + str(activity_id), headers=HEADERS)
        data = response.json()['value']

        activity_content = (
            f"[Mission and objectives] : {data.get('organizationMission', '')}"
            f"[Context] : {data.get('context', '')}"
            f"[Task description] : {data.get('taskDescription', '')}"
            f"[Required experience]: {data.get('requiredSkillExperience', '')}"
        )     
        activity_name = data.get("name")
        start_date = iso_to_utc(data.get("publishDate"))
        end_date = data.get("sourcingEndDate")
        site_url = URL_BASE + str(activity_id)
        keyword = extract_activity_keyword(data.get('organizationMission') or activity_name)

        activities.append(
            {
                "activity_site": "UNVOLUNTEERS",
                "activity_type": "VOLUNTEER",
                "activity_content": activity_content,
                "end_date": end_date,
                "site_url": site_url,
                "activity_image_url": DEFAULT_IMAGE_URL,
                "keyword": keyword,
                "activity_name": activity_name,
                "start_date": start_date
        })

        print(f"[UNV] 활동 크롤링 완료 : {activity_name}")

    return activities

def crawl():
    print("[UNV] 크롤링 시작")
    activity_id_list = fetch_activity_id_list()

    if activity_id_list:
        activities = fetch_activity_detail(activity_id_list)
        print(f"[UNV] 크롤링 완료 : {len(activity_id_list)}개의 활동을 크롤링했습니다.")
        save_activities(activities)
    else:
        print("[UNV] 크롤링 완료 : 새로운 활동이 없습니다.")
    
if __name__ == "__main__":
    crawl()