import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Literal

# .env 파일에서 환경변수 로드
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = 'gemini-2.0-flash-lite'
DELAY = 2.5 # 무료티어 RPM 제한 (분당 30회) 방지
KEYWORDS = ['Economy','Environment','PeopleAndSociety','Technology']
DEFAULT_KEYWORD = KEYWORDS[0]

class Issue(BaseModel):
    title: str
    summary: str
    keyword: Literal['Economy','Environment','PeopleAndSociety','Technology']

def translate_and_categorize(title: str, content: str) -> tuple[str, str, str]:
    """
    GEMINI API를 이용하여 영문 뉴스기사를 한글로 번역, 요약하고 키워드를 추출합니다.

    Parameters:
        title (str): 번역할 뉴스기사의 제목
        content (str): 번역할 뉴스기사의 내용

    Returns:
        Tuple[str, str, str]: 한글로 번역된 뉴스기사의 제목과 요약 (오류 발생 시 원문 반환), 키워드 (오류 발생 시 기본값 반환)
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        return title, content, DEFAULT_KEYWORD # 기본값 반환

    time.sleep(DELAY) # 무료티어 제한 (분당 30회) 회피를 위해 일정시간 대기
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=MODEL,
            contents=f"""
                You are a professional assistant that helps translate and summarize English news articles into Korean.
                Please perform the following tasks based on the article provided below:

                1. Translate the title into Korean.
                2. Summarize the content in **3 sentences** in Korean.
                3. Choose **one most relevant keyword** that best represents the article. Select only from this list: {', '.join(KEYWORDS)}.

                Respond strictly in the following JSON format:
                {{
                    "title": "<Korean translated title>",
                    "summary": "<3-sentence Korean summary>",
                    "keyword": "<one keyword from the list>"
                }}

                ---
                Title: {title}

                Content: {content}
                """,
            config=types.GenerateContentConfig(
                system_instruction="You are an assistant that helps translate English news articles into Korean and summarizes them.",
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=Issue,
            )
        )
        
        issue = Issue.model_validate_json(response.text)
        return issue.title, issue.summary, issue.keyword

    except Exception as e:
        print(f"❌ 번역 중 오류 발생, 원문을 반환합니다. : {e}")
        return title, content, DEFAULT_KEYWORD

if __name__ == "__main__":
    title = "Drinking water shortage in decade without new reservoirs, minister says"
    content = """England could face drinking water shortages within a decade unless new reservoirs are built, a minister has claimed.

The warning comes as the government announced it was speeding up the planning process for two reservoir projects.

But overriding local objections can be unpopular and the reservoirs could still be more than a decade away from opening.

Household consumption of water may also need to fall to secure supplies amid rising temperatures and a growing population, scientists warn.

The announcement means that final decisions about the proposed Fens Reservoir in Cambridgeshire and the Lincolnshire Reservoir will be taken by Environment Secretary Steve Reed, rather than at a local level.

This change amounts to "slashing red tape to make the planning process faster", according to Water Minister Emma Hardy.

Speaking to BBC Breakfast, she said: "This is really important because if we don't build the reservoirs, we're going to be running out of the drinking water that we need by the mid-2030s."

The reservoirs in Cambridgeshire and Lincolnshire are currently pencilled for completion in 2036 and 2040 respectively.

They "would provide more resilience to future droughts in a part of the country that is already dry and where there is high demand for water", said Dr Glenn Watts, water science director at the UK Centre for Ecology & Hydrology.

Reservoirs can help protect against the impacts of drought by collecting excess rainfall during wet periods.

With climate change likely to bring hotter, drier summers, the chances of drought could increase in the decades ahead, the Met Office says.

These preparations have been brought into sharp focus by this year's exceptionally dry spring.

North-west England is officially in drought, according to the Environment Agency, which says it is watching the situation closely in other regions.
Map showing water levels at the end of April, categorised relative to normal for the time of year, at 31 key reservoirs and groups of reservoirs serving England. Seven are “notably low” and are located in northern England or in the Welsh reservoirs that serve England. A further six are “below normal”.

Extra demand from new houses, data centres and other sectors could further squeeze supplies, but no major reservoirs have been completed in England since 1992, shortly after the water sector was privatised.

Last year the government and water companies announced proposals to build nine new reservoirs by 2050.

Together they have the potential to provide 670 million litres of extra water per day, they say.

That's in addition to the Havant Thicket reservoir project in Hampshire, which is already under way and is expected to be completed by 2031.

The government also says that it intends to pass legislation to automatically make the other seven proposed reservoirs "nationally significant", so the final decision would be taken by national government.

"Reservoir projects are very complex infrastructure projects that are slow to take forward, and so anything that can be done to streamline that process can be a positive thing," said David Porter, senior vice president of the Institution of Civil Engineers (ICE).
Anglian Water Artist's impression of what the Fens reservoir would look like. There is a large area of water with a building and road towards the bottom of the image. There are further roads in the background. Anglian Water
The Fens Reservoir could supply water to a quarter of a million homes, the government says

The water industry has also welcomed the announcement.

"It's absolutely critical that we build these reservoirs now," David Henderson, chief executive of Water UK, told BBC News.

"If we don't build them now, we wait another 10 years, it's going to cost even more, so we can't keep kicking the can down the road any longer."

But building reservoirs doesn't come cheaply, even with accelerated planning processes. That could ultimately filter down to people's bills.

Nor does it come quickly. No new major reservoirs are due to be completed this decade.

Some experts highlight that reservoirs are no silver bullet, and warn that managing how we use water needs to take greater precedence in a warming climate.

"We need a complete overhaul of the way we use water, to plug leaks, cut down on waste and store water where it falls as rain," said Prof Hannah Cloke of the University of Reading.

"It would be better to make more difficult decisions around regulation of new building, as well as retrofitting older homes and businesses, to cut waste and recycle water where it is used, rather than pumping water across huge distances," she added.

And like any major project, the new reservoirs could prove unpopular with local communities, particularly those whose homes and farmland are cleared to make way for them.

"The decision by the government to fast-track through the 'national significant infrastructure' route is in my opinion very bad and will make the public very angry," argued Dr Kevin Grecksch of the University of Oxford.

But David Porter of ICE stressed the need to take decisions "for the greater good".

"Now, that's not to say that we should ride roughshod over the views of local people, and that's not to say that every project is justifiable," he said.

"But if the decision maker is satisfied that on balance it is the right thing to do, you need to find a way through the objection in order to deliver these projects."

In response to the government's announcement, shadow environment secretary Victoria Atkins blamed Labour's farming and immigration policies for pressures on water supplies.

"The last Conservative government left behind a robust, coherent plan to safeguard food security and reduce net migration by more than half. Labour has chosen to abandon those plans and in doing so, it has surrendered control over both our rural community and our borders," she said.

Additional reporting by Justin Rowlatt, Esme Stallard and Miho Tanaka; map by Christine Jeavans
"""
    title, content, keyword = translate_and_categorize(title, content)
    print(f"번역된 제목 : {title}\n번역/요약된 내용 : {content}\n키워드 : {keyword}")