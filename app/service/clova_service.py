import logging
import random
from typing import Dict, List
from app.core.config import settings
import json
import http.client
from http import HTTPStatus
import requests

SYSTEM_PROMPT_CHATBOT = "너는 대한민국 문화재를 정확하고 재미있게 설명하는 문화해설사야. 문화재와 관련 없는 내용이 조금이라도 포함되면 {자, 다시 질문해줄래?}라고 답해."
SYSTEM_PROMPT_QUIZ = '''너는 대한민국 문화재에 대한 정확한 정보를 바탕으로 퀴즈를 내는 퀴즈 전문가야.
내가 문화재를 말하면, 그 문화재와 관련한 5지선다 퀴즈를 한문제만 내줘. 
내가 답을 말하면, 정답인지 확인해줘. 정답이라면 정답과 함께 간단한 설명을 해주고, 오답이라면 {오답입니다. 다시 한번 기회를 드리겠습니다.}라고 말해줘.
그 이외의 다른 텍스트는 절대 출력하지마. '''
SYSTEM_PROMPT_SUMMARY = '''너는 대한민국 문화재를 정확하고 재미있게 설명하는 문화해설사야.
내가 문화재를 말하면, 그 문화재에 대한 키워드를 10가지 뽑아서 보여줘. 맨 처음에는 반드시 #너나들이 가 들어가야해. {예시} #너나들이 #광화문 #경복궁 #종로 #조선시대 #궁궐 #국보 #해치 #드므 #십장생 '''
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
        self.response = [
            "네 그렇군요. 더 자세히 말씀해 주시겠어요?",
            "그걸로 포텐데이 원픽 하실수 있으시겠어요?",
            "이렇게 개발하다 배포는 언제하실거에요?",
            "너나들이 개발 언제 끝나요? 광고 붙이고싶어요"
        ]
        self.api_key = settings.CLOVA_API_KEY
        self.api_key_primary_val = settings.CLOVA_API_KEY_PRIMARY_VAL
        self.api_sliding_url = settings.CLOVA_SLIDING_API_HOST
        self.api_completion_url = settings.CLOVA_COMPLETION_API_HOST

    async def get_clova(self, session_id: int, message: str) -> str:
        # 임시 테스트 챗봇 응답 데이터 추출 
        return random.choice(self.response)

    async def get_chatting(self, session_id: int, sliding_window: list) -> str:
        try:
            logger.info(f"get_chatting input - session_id: {session_id}, sliding_window: {sliding_window}")

            sliding_window_executor = SlidingWindowExecutor(
                host = self.api_sliding_url,
                api_key = self.api_key,
                api_key_primary_val= self.api_key_primary_val,
                request_id = str(session_id)
            )

            request_data = { "messages": sliding_window, "maxTokens":256 }
            # logger.info(f"Adjusted sliding window: {adjusted_sliding_window}")

            completion_executor = ChatCompletionExecutor(
                host = self.api_completion_url,
                api_key = self.api_key,
                api_key_primary_val = self.api_key_primary_val,
                request_id = str(session_id)
            )

            adjusted_sliding_window = sliding_window_executor.execute(request_data)

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

            logger.info(f"Completion request data: {completion_request_data}")
            response = completion_executor.execute(completion_request_data, stream=False)

            # 응답 로깅
            logger.info(f"Raw API response: {response}")

            response = completion_executor.execute(completion_request_data, stream=False)
            response_text = parse_non_stream_response(response)

            logger.info(f"Parsed response text: {response_text}")
            return {"response": response_text}
        except Exception as e:
            logger.error(f"Error in get_chating: {str(e)}")
            raise ValueError("Failed to process chat request") from e
    

    async def get_quiz(self, session_id: int, question: str) -> str:
        completion_executor = ChatCompletionExecutor(
            host = self.api_completion_url,
            api_key = self.api_key,
            api_key_primary_val = self.api_key_primary_val,
            request_id = session_id
        )
        completion_request_data = {
            "messages": question,
            "maxTokens": 2000,
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

        # 여기서 response_text를 파싱하여 구조화된 데이터로 변환
        parsed_quiz = self._parse_quiz_response(response_text)

        return parsed_quiz
    
    def _parse_quiz_response(self, response_text: str) -> dict:
        # 여기서 response_text를 파싱하여 필요한 형식으로 변환
        # 이 부분은 실제 API 응답 형식에 따라 구현해야 합니다
        # 예시:
        quiz_text = "퀴즈 질문 추출"
        options = [
            {"id": 1, "text": "선택지 1"},
            {"id": 2, "text": "선택지 2"},
            {"id": 3, "text": "선택지 3"},
            {"id": 4, "text": "선택지 4"},
            {"id": 5, "text": "선택지 5"}
        ]
        correct_option_id = 1  # 정답 옵션 ID 추출

        return {
            "quiz_text": quiz_text,
            "options": options,
            "correct_option_id": correct_option_id
        }

    async def get_summary(self, session_id: int, content: str) -> str:
        completion_executor = ChatCompletionExecutor(
            host = self.api_completion_url,
            api_key = self.api_key,
            api_key_primary_val = self.api_key_primary_val,
            request_id = session_id
        )

        completion_request_data = {
            "messages": content,
            "maxTokens": 4000,
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

        return {"response": response_text}