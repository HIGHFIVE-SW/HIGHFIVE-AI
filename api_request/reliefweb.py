import requests
import json

# API 엔드포인트
api_url = "https://api.reliefweb.int/v1/jobs?limit=10&offset=1120"
# API링크를 저장하기 위한 배열
description_endpoint=[]
# API요청을 보내 
while api_url: # 다음으로 참고할 데이터가 없을 경우 조건문 종료
    response = requests.get(api_url)
    if response.status_code==200:
        data=response.json()

        links = data.get('links', {})
        if links:
            next_link = links.get('next', None)
            api_url = next_link.get('href', None) if next_link else None
        else:
            api_url = None  # 'next'가 없으면 종료 조건으로 설정
            

        print(api_url) # 디버깅용
        jobs=data.get("data", [])
        description_endpoint.append([job['href'] for job in jobs])

        # for job in jobs:
        #     href = job.get("href", "No Link")
            
        #     description_endpoint.append({"href": href})
            
        
    else:
        print("API 요청 실패:", response.status_code, response.text)
        break

# print(description_endpoint)

job_list=[]
flattened_data = [item for sublist in description_endpoint for item in sublist]

# print(flattened_data)

for info in flattened_data:
    
    response=requests.get(info)
    
    if response.status_code==200:
        data=response.json()
        jobs=data.get("data", [])
        for job in jobs:
            fields=job.get("fields", {})
            title=fields.get("title", "No title")
            body=fields.get("body", "No body")
            job_list.append({"title": title, "body": body})

print(json.dumps(job_list, indent=4, ensure_ascii=False))