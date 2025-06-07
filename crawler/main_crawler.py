from crawler.bbc_crawler import crawl as bbc_crawler
from crawler.wevity_crawler import crawl as wevity_crawler
from crawler.idealist_crawler import crawl as idealist_crawler
from crawler.unv_crawler import crawl as unv_crawler
from crawler.v1365_crawler import crawl as v1365_crawler
import sys

CRAWLER_MAP = {
    "bbc": bbc_crawler,
    "wevity": wevity_crawler,
    "idealist": idealist_crawler,
    "unv": unv_crawler,
    "v1365": v1365_crawler,
}

def run_crawlers(targets=None):
    """
    특정 크롤러 이름을 리스트로 넘기면 해당 크롤러만 실행.
    targets=None이면 전체 실행
    """
    if targets is None:
        targets = CRAWLER_MAP.keys()

    print("===== 크롤링 시작 =====")

    for name in targets:
        crawler_func = CRAWLER_MAP.get(name)
        if crawler_func:
            try:
                print(f"[{name.upper()}] 크롤러 실행 중...")
                crawler_func()
            except Exception as e:
                print(f"[{name.upper()}] 크롤러 실행 오류 발생: {e}")
        else:
            print(f"[{name}] 은(는) 등록되지 않은 크롤러입니다.")

    print("===== 크롤링 종료 =====")

if __name__ == '__main__':
    selected = sys.argv[1:]  # 인자 없으면 전체 실행
    run_crawlers(selected if selected else None)