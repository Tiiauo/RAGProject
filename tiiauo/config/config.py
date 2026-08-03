import os
from dotenv import load_dotenv
load_dotenv()

class MineruConfig:
    mineru_api = os.getenv("MINERU_API")

class LLMConfig:
    model_name = os.getenv("VL_MODEL_NAME")
    api_key = os.getenv("VL_API_KEY")
    base_url = os.getenv("VL_BASE_URL")
    temperature = os.getenv("VL_TEMPERATURE")

RPM = 500