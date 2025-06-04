from apscheduler.schedulers.background import BackgroundScheduler
from crawler.main_crawler import run_all_crawlers

# 스케줄러가 동작할 시각 (시, 분)을 설정
START_TIME_HOUR = 2
START_TIME_MINUTE = 0

scheduler = BackgroundScheduler()

def start_scheduler():
    scheduler.add_job(
        func=run_all_crawlers, 
        trigger='cron', 
        hour=START_TIME_HOUR, 
        minute=START_TIME_MINUTE
    )
    scheduler.start()

def shutdown_scheduler():
    scheduler.shutdown()
