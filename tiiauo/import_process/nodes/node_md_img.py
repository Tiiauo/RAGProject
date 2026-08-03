import base64
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Any

from langchain.chat_models import init_chat_model

from tiiauo.config.config import LLMConfig
from tiiauo.import_process.base import NodeBase
from tiiauo.import_process.state import ImportGraphState
from tiiauo.tool.logger import logger
from tiiauo.tool.to_json_format import to_json


class NodeMDImg(NodeBase):
    """
    MarkDown图片处理节点：多模态图片理解
    """

    name = "node_md_img"

    def process(self, state: ImportGraphState):

        # 校验md路径,并读取md文件内容
        md_content, md_path_obj = self.check_md_path(state)

        # 获取md中图片内容
        images_path_obj = md_path_obj.parent / "images"
        if not images_path_obj.exists():
            logger.error(f"图片目录不存在：{images_path_obj}")
            return state
        if not images_path_obj.is_dir():
            logger.error(f"图片路径不是目录：{images_path_obj}")
            return state
        file_name_list = os.listdir(images_path_obj)
        if not file_name_list:
            logger.error(f"图片目录为空：{images_path_obj}")
            return state

        image_file_list = []

        self.get_images_desc(file_name_list, image_file_list, images_path_obj, md_content)

        logger.info(f"图片描述：{to_json(image_file_list)}")

        return state

    def get_images_desc(self, file_name_list, image_file_list, images_path_obj,md_content):
        IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        MAX_CONTEXT_LEN = 300
        for file_name in file_name_list:
            if Path(file_name).suffix.lower() not in IMAGE_EXTENSIONS:
                logger.warning(f"图片格式不支持：{file_name}")
                continue
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(file_name) + r"\)")
            match = pattern.search(md_content)

            if not match:
                logger.warning(f"图片未引用：{file_name}")
                continue

            start, end = match.span()
            pre_context = md_content[max(0, start - MAX_CONTEXT_LEN):start]
            post_context = md_content[end:min(end + MAX_CONTEXT_LEN, len(md_content))]

            image_file_list.append({
                "file_name": file_name,
                "pre_context": pre_context,
                "post_context": post_context,
                "images_path": str(images_path_obj / file_name),
            })

        llm = init_chat_model(
            model=LLMConfig.model_name,
            model_provider='openai',
            api_key=LLMConfig.api_key,
            base_url=LLMConfig.base_url,
            temperature=float(LLMConfig.temperature),
        )

        MIME_MAP = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }

        dq = deque()
        for image_file in image_file_list:
            self.acquire(dq, 100)
            with open(image_file["images_path"], "rb") as f:
                image_bytes = f.read()
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                mime_type = MIME_MAP.get(Path(image_file["images_path"]).suffix.lower(), "image/jpeg")
                base64_url =  f"data:{mime_type};base64,{base64_image}"
            messages = [
                {
                    "role": "system",
                    "content": """你是企业知识库的技术文档图片解析助手。
                    你的任务是根据用户提供的上下文信息以及图片base64信息,
                    把图片中的有效信息转换为准确、独立、可检索的 Markdown 文本。
                    必须以图片中的真实内容为依据，不得猜测看不清或无法确认的信息。"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                                        这是一张图片，图片上文部分为"{image_file.get("pre_context")}"，
                                        下文部分为"{image_file.get("post_context")}"，
                                        请用中文根据上下文信息对这张图片进行描述!"""

                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": base64_url
                            }
                        }
                    ]
                }
            ]
            res = llm.invoke(messages)
            image_file["description"] = res.content

    def check_md_path(self, state: ImportGraphState) -> tuple[str, Path]:
        md_path = state.get("md_path", "")
        if not isinstance(md_path, str) or not md_path.strip():
            logger.error("未提供 Markdown 文件路径")
            raise ValueError("Markdown 文件路径不能为空")

        md_path_obj = Path(md_path.strip())
        if not md_path_obj.exists():
            logger.error(f"Markdown 文件不存在：{md_path_obj}")
            raise FileNotFoundError(f"Markdown 文件不存在：{md_path_obj}")

        if not md_path_obj.is_file():
            logger.error(f"Markdown 路径不是文件：{md_path_obj}")
            raise ValueError(f"Markdown 路径不是文件：{md_path_obj}")

        if md_path_obj.suffix.lower() != ".md":
            logger.error(f"文件不是 Markdown 格式：{md_path_obj}")
            raise ValueError(f"文件不是 Markdown 格式：{md_path_obj}")

        logger.info(f"Markdown 文件校验成功：{md_path_obj}")

        with open(md_path_obj, "r", encoding="utf-8") as f:
            md_content = f.read()

        if not md_content:
            logger.error(f"Markdown 文件内容为空：{md_path_obj}")
            raise ValueError(f"Markdown 文件内容为空：{md_path_obj}")
        return md_content, md_path_obj

    @staticmethod
    def acquire(dq,rpm):
        if rpm <= 0:
            raise ValueError("rpm 必须大于 0")
        while True:
            now = time.monotonic()
            while dq and now - dq[0] >= 60:
                dq.popleft()
            if len(dq) < rpm:
                dq.append(now)
                return
            wait_time = 60 - (now - dq[0])
            if wait_time > 0:
                time.sleep(wait_time)

if __name__ == '__main__':
    node = NodeMDImg()
    init_state = {
        "md_path": r"D:\Learn_AI\RAGProjectData\hak180产品安全手册\hak180产品安全手册.md"
    }
    node.process(init_state)