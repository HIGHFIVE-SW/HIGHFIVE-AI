from crawler.bbc_crawler import crawl as bbc_crawler
from crawler.wevity_crawler import crawl as wevity_crawler
from crawler.idealist_crawler import crawl as idealist_crawler
from crawler.unv_crawler import crawl as unv_crawler
from crawler.v1365_crawler import crawl as v1365_crawler 

def run_all_crawlers():
    print("===== 전체 크롤링 시작 =====")
    
    try:
        bbc_crawler()
    except Exception as e:
        print(f"BBC 크롤러 실행중 오류 발생: {e}")

    # try:
    #     wevity_crawler()
    # except Exception as e:
    #     print(f"WEVITY 크롤러 실행중 오류 발생: {e}")

    # try:
    #     v1365_crawler()
    # except Exception as e:
    #     print(f"1365 크롤러 실행중 오류 발생: {e}")

    # try:
    #     idealist_crawler()
    # except Exception as e:
    #     print(f"IDEALIST 크롤러 실행중 오류 발생: {e}")

    # try:
    #     unv_crawler()
    # except Exception as e:
    #     print(f"UN Volunteers 크롤러 실행중 오류 발생: {e}")

    print("===== 전체 크롤링 종료 =====")

if __name__ == '__main__':
    run_all_crawlers()