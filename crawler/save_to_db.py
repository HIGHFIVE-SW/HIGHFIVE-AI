from server.db import run_query
import uuid

def save_issues(issues):
    if not issues:
        print("[DB] 저장할 이슈가 없습니다.")
        return
    
    print("[DB] 크롤링한 이슈 DB 저장 중...")

    sql = """
        INSERT IGNORE INTO issues (
            issue_id,
            created_at,
            content,
            image_url,
            issue_date,
            keyword,
            site_url,
            title
        ) VALUES (%s, UTC_TIMESTAMP(6), %s, %s, %s, %s, %s, %s)
    """

    values = [
        (
            uuid.uuid4().bytes,
            issue['content'], 
            issue['image_url'],
            issue['issue_date'],
            issue['keyword'],
            issue['site_url'],
            issue['title']
        )
        for issue in issues
    ]

    if values:
        saved_rows = run_query(sql, values)
        print(f"[DB] {saved_rows}개의 이슈가 저장되었습니다.")

def save_activities(activities):
    if not activities:
        print("[DB] 저장할 활동이 없습니다.")
        return

    print("[DB] 크롤링한 활동 DB 저장 중...")

    sql = """
        INSERT IGNORE INTO activities (
            created_at,
            end_date,
            start_date,
            activity_id,
            activity_image_url,
            activity_name,
            site_url,
            activity_content,
            activity_site,
            activity_type,
            keyword
        ) VALUES (UTC_TIMESTAMP(6), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = [
        (
            activity['end_date'],
            activity['start_date'],
            uuid.uuid4().bytes,
            activity['activity_image_url'],
            activity['activity_name'],
            activity['site_url'],
            activity['activity_content'],
            activity['activity_site'],
            activity['activity_type'],
            activity['keyword']
        )
        for activity in activities
    ]

    if values:
        saved_rows = run_query(sql, values)
        print(f"[DB] {saved_rows}개의 활동이 저장되었습니다.")


