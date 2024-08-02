from functools import lru_cache
import logging
import aiohttp
from typing import Any, Callable, Dict, List, Tuple
from app.core.config import settings
import json
import http.client
from http import HTTPStatus
import requests

from app.core.config import settings
from app.utils.common import parse_quiz_content


SYSTEM_PROMPT_CHATBOT = '''대한민국 문화재를설명하는 문화해설사입니다. 경복궁과 관련한 문화재에 대한 설명을 출력합니다.
지시사항
-  모든 말은 '하오'체로 한다.
- 해당 문화재와 관련한 질문이 아니라면 답하지 않는다
- 정확한 정보만 전달한다.'''
SYSTEM_PROMPT_QUIZ = '''1. 너는 대한민국 문화재에 대한 정확한 정보를 바탕으로 퀴즈를 내는 퀴즈 전문가입니다.
2. 입력한 문화재와 관련한 퀴즈를 냅니다.
3. 문제, 5개의 보기, 정답, 설명 모두를 반환합니다.
4. 퀴즈 이외의 텍스트는 절대 표시하지 않습니다.
5. 모든 말은 '하오'체로 합니다.

### 예시
경복궁의 중심이 되는 건물은 다음 중 무엇일까요?

1. 근정전
2. 사정전
3. 교태전
4. 강녕전
5. 향원정


정답: 1번


설명: 근정전은 경복궁의 중심 건물로, 조선 왕조의 국왕이 공식적으로 업무를 보던 장소입니다. 중요한 의식과 국가 행사가 이곳에서 열렸으며, 경복궁의 주요 건물 중 하나로 손꼽힙니다.'''
SYSTEM_PROMPT_ANSWER = '''너는 대한민국 문화재에 대한 정확한 정보를 바탕으로 퀴즈를 내는 퀴즈 전문가야. 내가 문제와 답을 알려주면, 정답인지 아닌지 확인하고 간결하게 설명해줘.
지시사항
- 모든 말은 '하오'체로 한다.
- 정확하게 확인하고 설명한다.
{예시}
조선시대 임금의 즉위식이 거행되었던 경복궁의 전각은 다음 중 무엇일까요?
1. 근정전
2. 사정전
3. 교태전
4. 경회루
5. 자경전
###
4번
###
맞소! 정답은 4번 경회루요.'''
SYSTEM_PROMPT_SUMMARY = '''너는 대한민국 문화재를 정확하고 재미있게 설명하는 문화해설사야.
내가 문화재를 말하면, 그 문화재에 대한 키워드를 10가지 뽑아서 보여줘. 맨 처음에는 반드시 #너나들이 가 들어가야해. {예시} #너나들이 #광화문 #경복궁 #종로 #조선시대 #궁궐 #국보 #해치 #드므 #십장생 '''

SYSTEM_PROMPT_SUMMARY_TEST = '''너는 대한민국 문화재를 정확하고 재미있게 설명하는 문화해설사야.
내가 대화한 전체 내용을 읽고 뽑을 수 있는 키워드를 10가지 뽑아서 보여줘. 맨 처음에는 반드시 #너나들이 가 들어가야해. {예시} #너나들이 #광화문 #경복궁 #종로 #조선시대 #궁궐 #국보 #해치 #드므 #십장생 '''


MAX_TOKEN = 4000

def parse_non_stream_response(response):
    result = response.get('result', {})
    message = result.get('message', {})
    content = message.get('content', '')
    return content.strip()

logger = logging.getLogger(__name__)

class CLOVAStudioExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id
  
    def _send_request(self, completion_request, endpoint):
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id
        }
  
        conn = http.client.HTTPSConnection(self._host)
        conn.request('POST', endpoint, json.dumps(completion_request), headers)
        response = conn.getresponse()
        status = response.status
        result = json.loads(response.read().decode(encoding='utf-8'))
        conn.close()
        return result, status
  
    def execute(self, completion_request, endpoint):
        res, status = self._send_request(completion_request, endpoint)
        if status == HTTPStatus.OK:
            return res, status
        else:
            error_message = res.get("status", {}).get("message", "Unknown error") if isinstance(res, dict) else "Unknown error"
            raise ValueError(f"오류 발생: HTTP {status}, 메시지: {error_message}")

class ChatCompletionExecutor(CLOVAStudioExecutor):
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        super().__init__(host, api_key, api_key_primary_val, request_id)
 
    def execute(self, completion_request, stream=True):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream' if stream else 'application/json'
        }
 
        with requests.post(self._host + '/testapp/v1/chat-completions/HCX-003',
                           headers=headers, json=completion_request, stream=stream) as r:
            if stream:
                if r.status_code == HTTPStatus.OK:
                    response_data = ""
                    for line in r.iter_lines():
                        if line:
                            decoded_line = line.decode("utf-8")
                            print(decoded_line)
                            response_data += decoded_line + "\n"
                    return response_data
                else:
                    raise ValueError(f"오류 발생: HTTP {r.status_code}, 메시지: {r.text}")
            else:
                if r.status_code == HTTPStatus.OK:
                    return r.json()
                else:
                    raise ValueError(f"오류 발생: HTTP {r.status_code}, 메시지: {r.text}")

class SlidingWindowExecutor(CLOVAStudioExecutor):

    def execute(self, completion_request):
        endpoint = '/v1/api-tools/sliding/chat-messages/HCX-003'
        try:
            # logger.info(f"SlidingWindowExecutor input: {sliding_window}")
            # completion_request = {"messages": sliding_window}
            logger.info(f"SlidingWindowExecutor request: {completion_request}")
            result, status = super().execute(completion_request, endpoint)
            logger.info(f"SlidingWindowExecutor result: {result}, status: {status}")
            if status == 200:
                # 슬라이딩 윈도우 적용 후 메시지를 반환
                return result['result']['messages']
            else:
                error_message = result.get('status', {}).get('message', 'Unknown error')
                raise ValueError(f"오류 발생: HTTP {status}, 메시지: {error_message}")
        except Exception as e:
            print(f"Error in SlidingWindowExecutor: {e}")
            raise

class ClovaService:
    '''
    input: session_id, content(sliding_window + user_input)
    output: clova x output
    '''
    def __init__(self):
        self.api_key = settings.CLOVA_API_KEY
        self.api_key_primary_val = settings.CLOVA_API_KEY_PRIMARY_VAL
        self.api_sliding_url = settings.CLOVA_SLIDING_API_HOST
        self.api_completion_url = settings.CLOVA_COMPLETION_API_HOST

    async def get_chatting(self, session_id: int, sliding_window: list) -> str:
        try:
            logger.info(f"get_chatting input - session_id: {session_id}, sliding_window: {sliding_window}")

            if sliding_window is None:
                sliding_window = []

            # Sliding Window 요청
            sliding_window_executor = SlidingWindowExecutor(
                host = self.api_sliding_url,
                api_key = self.api_key,
                api_key_primary_val= self.api_key_primary_val,
                request_id = str(session_id)
            )

            request_data = {
                "messages": [{"role": "system", "content": SYSTEM_PROMPT_CHATBOT}] + sliding_window,
                "maxTokens": 3000
            }

            adjusted_sliding_window = sliding_window_executor.execute(request_data)
            logger.info(f"Adjusted sliding window: {adjusted_sliding_window}")

            # 마지막 메시지 ASSISTANT 응답인 경우 이를 resopnse로 사용
            if adjusted_sliding_window[-1]['role'] == 'assistant':
                response_text = adjusted_sliding_window[-1]['content']
            else:
                # ASSISTANT 응답 없는 경우 Completion 요청 실행
                completion_executor = ChatCompletionExecutor(
                    host = self.api_completion_url,
                    api_key = self.api_key,
                    api_key_primary_val = self.api_key_primary_val,
                    request_id = str(session_id)
                )

                # Completion 요청 실행
                completion_request_data = {
                    "messages": adjusted_sliding_window,
                    "maxTokens": 400,
                    "temperature": 0.5,
                    "topK": 0,
                    "topP": 0.8,
                    "repeatPenalty": 1.2,
                    "stopBefore": [],
                    "includeAiFilters": True,
                    "seed": 0
                }

                logger.info(f"요청 데이터 완료: {completion_request_data}")
                response = completion_executor.execute(completion_request_data, stream=False)

                # 응답 로깅
                logger.info(f"세션 ID {session_id}에 대한 Raw한 API 응답 {response}")

                response_text = parse_non_stream_response(response)
                logger.info(f"세션 ID {session_id}에 대한 Parsed 된 응답 {response_text}")

                # 새로운 sliding window에 방금 얻은 response를 더해서 반환
                # adjusted_sliding_window.append({"role":"assistant", "content":response_text})
        
            # new_sliding_window 크기 관리
            new_sliding_window = self.manage_sliding_window_size(adjusted_sliding_window)

            return {"response": response_text, "new_sliding_window": new_sliding_window }
        
        except Exception as e:
            logger.error(f"Error in get_chating: {str(e)}")
            raise ValueError("Failed to process chat request") from e
        
    def manage_sliding_window_size(self, sliding_window: List[Dict[str, str]]) -> List[Dict[str, str]]:
        max_window_size = settings.MAX_SLIDING_WINDOW_SIZE
        if len(sliding_window) > max_window_size:
            return [sliding_window[0]] + sliding_window[-(max_window_size-1):]
        return sliding_window

    # 여기서 퀴즈 버튼을 누를 때, 현재 위치의 이름을 받아와야 합니다. (ex - 근정전)
    # async def get_quiz(self, session_id: int, building_name: str) -> Dict[str, str]:
    async def get_quiz(self, session_id: int, building_name: str) -> str:
        try:
            completion_executor = ChatCompletionExecutor(
                host = self.api_completion_url,
                api_key = self.api_key,
                api_key_primary_val = self.api_key_primary_val,
                request_id = str(session_id)
            )
            
            request_data = [
                {"role": "system", "content": SYSTEM_PROMPT_QUIZ}, 
                {"role": "user", "content": f"{building_name}에 대한 퀴즈를 생성해주세요."}
            ]

            completion_request_data = {
                "messages": request_data,
                "maxTokens": 300,
                "temperature": 0.5,
                "topK": 0,
                "topP": 0.8,
                "repeatPenalty": 1.2,
                "stopBefore": [],
                "includeAiFilters": True,
                "seed": 0
            }

            logger.info(f"Quiz request data: {completion_request_data}")
            response = completion_executor.execute(completion_request_data, stream=False)
            logger.info(f"Raw API response for session ID {session_id}: {response}")
            
            # 경복궁의 중심이 되는 건물은 다음 중 무엇일까요?\n1. 근정전\n2. 사정전\n3. 교태전\n4. 강녕전\n5. 향원정 형식
            # 이 반환값이 full_conversation에 저장되어야 합니다.
            # 아니라면 퀴즈의 정답을 사용자가 선택할때까지 이 질문을 가지고 있어야 해요....
            response_text = parse_non_stream_response(response)
            logger.info(f"Parsed response for session ID {session_id}: {response_text}")

            return response_text
        except Exception as e:
            logger.error(f"Error in get_chating: {str(e)}")
            raise ValueError("Failed to process chat request") from e

    # 여기서는 full_conversation에 들어있던 question과 기존 sliding_window, 
    # 선택한 보기가 입력으로 들어와야 합니다. (ex - 1번)
    async def get_answer(self, session_id: int, sliding_window, question: str, answer: str) -> str:
        try:
            sliding_window_executor = SlidingWindowExecutor(
                    host = self.api_sliding_url,
                    api_key = self.api_key,
                    api_key_primary_val= self.api_key_primary_val,
                    request_id = str(session_id)
                )

            completion_executor = ChatCompletionExecutor(
                host = self.api_completion_url,
                api_key = self.api_key,
                api_key_primary_val = self.api_key_primary_val,
                request_id = str(session_id)
            )
            
            request_data = [{"role": "system", "content": SYSTEM_PROMPT_ANSWER}, {"role": "user", "content": question + "\n" + answer}]
            completion_request_data = {
                "messages": request_data,
                "maxTokens": 300,
                "temperature": 0.5,
                "topK": 0,
                "topP": 0.8,
                "repeatPenalty": 1.2,
                "stopBefore": [],
                "includeAiFilters": True,
                "seed": 0
            }

            response = completion_executor.execute(completion_request_data, stream=False)
            response_text = parse_non_stream_response(response)
            new_sliding_window = sliding_window_executor.execute(sliding_window + [{"role":"assistant", "content":response_text}])
            return {"response": response_text, "new_sliding_window":new_sliding_window}
        except Exception as e:
            logger.error(f"Error in get_chating: {str(e)}")
            raise ValueError("Failed to process chat request") from e
        
    def manage_sliding_window_size(self, sliding_window: List[Dict[str, str]]) -> List[Dict[str, str]]:
        max_window_size = settings.MAX_SLIDING_WINDOW_SIZE
        if len(sliding_window) > max_window_size:
            return [sliding_window[0]] + sliding_window[-(max_window_size-1):]
        return sliding_window
    
    def update_sliding_window_system(self, sliding_window: List[Dict[str, str]], new_system_prompt: str) -> List[Dict[str, str]]:
        # system 메시지를 새로운 프롬프트로 교체
        updated_window = [{"role": "system", "content": new_system_prompt}]
        
        # 기존의 user와 assistant 메시지만 유지
        for message in sliding_window:
            if message['role'] in ['user', 'assistant']:
                updated_window.append(message)
        
        return updated_window

    

    # content는 돌았던 코스 텍스트가 담겨있으면 됩니다.
    async def get_summary(self, session_id: int, content: str) -> str:
        try:
            completion_executor = ChatCompletionExecutor(
                host = self.api_completion_url,
                api_key = self.api_key,
                api_key_primary_val = self.api_key_primary_val,
                request_id = str(session_id)
            )

            completion_request_data = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_SUMMARY}, 
                    {"role":"user", "content": content}
                ],
                "maxTokens": 400,
                "temperature": 0.5,
                "topK": 0,
                "topP": 0.8,
                "repeatPenalty": 1.2,
                "stopBefore": [],
                "includeAiFilters": True,
                "seed": 0
            }

            response = completion_executor.execute(completion_request_data, stream=False)
            response_text = parse_non_stream_response(response)

            keywords = response_text.split()[1:]    # '너나들이' 키워드 제외
            return {"keywords": keywords}
        except Exception as e:
            logger.error(f"Error in get_chatting: {str(e)}")
            raise ValueError("Failed to process chat request") from e