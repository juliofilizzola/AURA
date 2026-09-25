from src.schema import RequestUser, ResponseUser
from src.erros import BadRequestError
import ollama

class ServiceAura:
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name

    def process_request(self, request: RequestUser) -> ResponseUser:
        message_format = {
            'role': 'user',
            'content': request.msg
        }
        try:
            response = ollama.chat(model=self.model_name, messages=[message_format])['message']['content']
        except Exception as e:
            raise BadRequestError(f"Erro ao processar a solicitação: {str(e)}")

        return ResponseUser(result=response)
