import requests
import os
import time
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 키워드 후보
KEYWORDS = ['Economy','Environment','PeopleAndSociety','Technology']
MODEL = 'gemini-2.0-flash-lite'
DELAY = 2.5 # 무료티어 RPM 제한 (분당 30회) 방지

def extract_keyword(text: str) -> str:
    """
    봉사활동 내용을 입력받아 적절한 키워드를 반환합니다.

    Parameters:
        text (str): 봉사활동 내용

    Returns:
        str: 봉사활동 내용에 맞는 키워드
    """

    # Gemini API 키 가져오기
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    # API 엔드포인트 URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"

    # 프롬프트 작성
    prompt = f"""
Read the following volunteer activity description and choose the **most appropriate keyword** from the provided list.

Only output **one keyword**, exactly as it appears in the list. Do not add any extra words or punctuation.

Volunteer Description:
{text}

Keyword List:
{', '.join(KEYWORDS)}
"""

    # API 요청 데이터 준비
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    # API 호출
    headers = {'Content-Type': 'application/json'}
    try:
        time.sleep(DELAY) # 무료티어 제한 (분당 30회) 회피를 위해 일정시간 대기
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # HTTP 에러 체크
        
        # 응답 파싱
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            # 응답에서 키워드만 추출 (앞뒤 공백 제거)
            keyword = generated_text.strip()
            
            # 추출된 키워드가 후보 목록에 있는지 확인
            if keyword in KEYWORDS:
                return keyword
            else:
                return KEYWORDS[0]  # 기본값으로 첫 번째 키워드 반환
                
    except Exception as e:
        print(f"API 호출 중 오류 발생: {e}")
        return KEYWORDS[0]  # 오류 발생 시 기본값으로 첫 번째 키워드 반환

    return KEYWORDS[0]  # 기본값으로 첫 번째 키워드 반환

if __name__ == "__main__":
    # 테스트용 예시
    text = """
    'Are you passionate about creating a positive change in society? Our CBS-featured non-profit wants you to join us in making a difference. About Us: Bright Mind is an award-winning non-profit organization recognized for our innovative initiatives such as Wellness Week and Street Care. Our outreach has reached up to 60 million people and has been featured on CBS, Politico, ABC, and Newsweek. We are looking for a passionate and versatile volunteer to join our team. If you have a desire to make a positive impact in the lives of those experiencing homelessness, we would love to hear from you! Position Overview ● Bright Mind is seeking dedicated and compassionate individuals to join our Street Care team as Homelessness Volunteers. ● In this role, you will have the opportunity to make a tangible difference in the lives of those experiencing homelessness. ● You will work closely with our Community Outreach team to provide support, resources, and advocacy for homeless individuals and families. ● We have decades of experience providing aid to homeless and highly at risk people, and our program always places safety first. ● We have a variety of openings, whether you’re interested in going out on the street or looking to help in other ways. Key Responsibilities ● Direct Support: ○ Engage with homeless individuals and families to assess their needs and provide appropriate support. ○ Distribute essential items such as food, clothing, hygiene products, and blankets. ● Resource Connection: ○ Connect individuals with local services, including housing, medical care, job training, and mental health support. ○ Provide information about available resources and help individuals navigate the social services system. ● Advocacy and Education: ○ Participate in community education programs to inform the public about homelessness issues and how they can help. ○ Work with local businesses and organizations to secure support (notably in-kind, such as food and clothing) and collaborate on our homeless initiatives. ● Event Coordination: ○ Assist in organizing and executing events such as donation drives, community meals, and health fairs. ○ Support the planning and logistics of outreach activities and special programs. ● Data Collection and Reporting: ○ Maintain accurate records of interactions and services provided to homeless individuals. ○ Assist with data collection and reporting to help track the impact of Bright Mind’s homelessness programs. Qualifications ● Skills and Competencies: ○ Strong interpersonal and communication skills. ○ Empathy, patience, and a non-judgmental attitude towards individuals experiencing homelessness. ○ Ability to work independently and as part of a team. ○ Flexibility and adaptability in a dynamic work environment. ○ Basic knowledge of social services and resources available for homeless individuals (preferred but not required). ● Experience: ○ Previous volunteer experience, especially in community outreach or working with vulnerable populations, is preferred but not required. ○ Experience in event coordination, advocacy, or data collection is a plus. ● Education: ○ Relevant coursework or training in social work, psychology, or a related field is welcomed. Benefits ● Opportunity to make a meaningful impact in the community. ● Hands-on experience in community outreach and social services. ● Professional development and training opportunities. ● Flexible volunteer schedules to accommodate your availability. Note: This is an unpaid position. Contact Us Please reach out to us at info@brightmindenrichment.org. To apply for this position, email your resume to hr@brightmindenrichment.org. Learn more about our initiatives at Street Care (https://streetcare.us/) and Bright Mind (https://brightmindenrichment.org/). Bright Mind is a federally-recognized 501(c)(3) wellness education non-profit and recipient of awards and certifications in recognition of our achievements.'
    """
    keyword = extract_keyword(text)
    print(f"선택된 키워드: {keyword}")