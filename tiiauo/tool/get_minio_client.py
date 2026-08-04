import json
from functools import lru_cache

from minio import Minio

from tiiauo.config.config import MinIoConfig
from tiiauo.tool.logger import logger


@lru_cache(maxsize=1)
def get_minio_client():
    try:
        minio_client = Minio(
            endpoint=MinIoConfig.minio_endpoint,
            access_key=MinIoConfig.minio_access_key,
            secret_key=MinIoConfig.minio_secret_key,
            secure=False,
        )

        if not minio_client.bucket_exists(MinIoConfig.minio_bucket_name):
            minio_client.make_bucket(MinIoConfig.minio_bucket_name)

        policy =  {
        "Version": "2012-10-17",
        "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": f"arn:aws:s3:::{MinIoConfig.minio_bucket_name}",
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{MinIoConfig.minio_bucket_name}/*",
                },
            ],
        }

        minio_client.set_bucket_policy(
            MinIoConfig.minio_bucket_name, json.dumps(policy)
        )
    except Exception as e:
        logger.error(f"MinIO客户端初始化失败: {e}")
        raise

    return minio_client

if __name__ == '__main__':
    minio_client = get_minio_client()