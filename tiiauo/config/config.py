import os
from dotenv import load_dotenv
load_dotenv()



RPM = 60
class MineruConfig:
    mineru_api = os.getenv("MINERU_API")

class LLMConfig:
    model_name = os.getenv("VL_MODEL_NAME")
    api_key = os.getenv("VL_API_KEY")
    base_url = os.getenv("VL_BASE_URL")
    temperature = os.getenv("VL_TEMPERATURE")

class MinIoConfig:
    minio_endpoint = os.getenv("MINIO_ENDPOINT")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY")
    minio_bucket_name = os.getenv("MINIO_BUCKET")

