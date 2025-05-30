from crawler.bbc_crawler import crawl as bbc_crawler
from crawler.wevity_crawler import crawl as wevity_crawler
from crawler.idealist_crawler import crawl as idealist_crawler
from crawler.unv_crawler import crawl as unv_crawler
from crawler.v1365_crawler import crawl as v1365_crawler 

if __name__ == "__main__":
    # BBC News
    # bbc_crawler()

    # WEVITY
    wevity_crawler()

    # 1365
    v1365_crawler()
    
    # IDEALIST
    # idealist_crawler()

    # UNVOLUNTEERS
    # unv_crawler()

    