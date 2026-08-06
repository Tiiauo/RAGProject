import re
from pathlib import Path
from typing import Any

from charset_normalizer import md
from langchain_text_splitters import RecursiveCharacterTextSplitter

from tiiauo.import_process.base import NodeBase
from tiiauo.import_process.state import ImportGraphState
from tiiauo.tool.logger import logger
from tiiauo.tool.to_json_format import to_json


class NodeDocumentSplit(NodeBase):
    """
    文档切分节点：智能文档切片
    """

    name = "node_document_split"

    def __init__(self):
        super().__init__()
        self.title_pattern = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
        self.code_pattern = re.compile(r"^(`{3,}|~{3,})")
        self.chunk_size = 300
        self.chunk_overlap = 0

    def process(self, state: ImportGraphState):

        # 获取修改后的md内容
        md_content, file_title = self.get_md_content(state)

        # 统一换行符
        md_content = md_content.replace("\r\n", "\n").replace("\r", "\n")

        # 按行切分
        sections = self.split_sections(file_title, md_content)

        final_sections = self.split_long_sections(sections)

        json_path = self.backup_chunks(file_title, final_sections, state)

        return {
            "chunks": final_sections,
            "chunks_json_path": str(json_path)
        }

    def backup_chunks(self, file_title: str, final_sections: list[Any], state: ImportGraphState) -> Path:
        json_path = Path(state.get("md_path")).parent / f"{file_title}.json"
        if not json_path.exists():
            json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(to_json(final_sections))
        return json_path

    def split_long_sections(self, sections: list[Any]) -> list[Any]:
        final_sections = []
        spliter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " "]
        )

        for content_split in sections:
            title = content_split.get("title", "")
            content = content_split.get("content", "")
            content_len = len(content)
            real_content = self.get_real_content(title, content)

            if len(real_content) < self.chunk_size:
                final_sections.append({
                    **content_split,
                    "part": 0,
                    "content_len": content_len,
                })
                continue

            if "<table" in real_content:
                final_sections.append({
                    **content_split,
                    "part": 0,
                    "content_len": content_len,
                })
                continue

            for part, chunk in enumerate(spliter.split_text(real_content), start=1):
                final_sections.append({
                    "title": title,
                    "content": title + "\n\n" + chunk,
                    "part": part,
                    "chunk_len": len(chunk),
                    "content_len": content_len,

                })
        return final_sections

    def split_sections(self, file_title: str, md_content: str) -> list[Any]:
        in_code_block = False
        code_fence = None
        start_index = 0

        sections = []
        current_lines = []
        for end_index, line in enumerate(md_content.split("\n")):
            line = line.strip()
            code_match = self.code_pattern.match(line)

            if code_match:
                maker = code_match.group(1)
                if not in_code_block:
                    in_code_block = True
                    code_fence = maker
                    logger.info(f"进入代码围栏: {maker}")
                elif code_fence == maker:
                    in_code_block = False
                    code_fence = None
                    logger.info(f"退出代码围栏: {maker}")

            if not in_code_block and self.title_pattern.match(line):

                # 跳过空列表以及只包含空白行的切片
                if any(item.strip() for item in current_lines):
                    sections.append(self.build_sections(current_lines, file_title))
                    current_lines = [line]
            current_lines.append(line)

        if any(item.strip() for item in current_lines):
            sections.append(self.build_sections(current_lines, file_title))
        return sections

    @staticmethod
    def get_md_content(state: ImportGraphState):
        file_title = state.get("file_title", "")
        if not file_title:
            raise ValueError("未提供文件标题")

        md_content = state.get("md_content", "")

        if isinstance(md_content, str) and md_content.strip():
            return md_content, file_title

        md_path = state.get("md_path", "")
        if not md_path:
            raise ValueError("未提供文档路径")

        md_path_obj = Path(md_path)

        if not md_path_obj.exists():
            raise ValueError("文档路径不存在")
        if not md_path_obj.is_file():
            raise ValueError("文档路径不是一个文件")
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        return md_content, file_title

    def build_sections(self, current_lines, file_title):
        content = "\n".join(current_lines)
        first_line = current_lines[0].strip() if current_lines else ""

        if self.title_pattern.match(first_line):
            title = first_line
        else:
            title = "No title"

        return {
            "title": title,
            "content": content,
            "file_title": file_title,
        }

    @staticmethod
    def get_real_content(title, content):
        lines = content.split("\n")

        if title.startswith("#") and lines and lines[0].strip() == title.strip():
            return "\n".join(lines[1:]).lstrip("\n")

        return content


if __name__ == '__main__':
    node = NodeDocumentSplit()
    init_state = {
        "task_id": "T1-hak180产品安全手册",
        "md_path": r"D:\Learn_AI\RAGProjectData\T1-hak180产品安全手册\hak180产品安全手册\hak180产品安全手册_new.md",
        "file_title": "hak180产品安全手册",
    }
    result = node(init_state)
    logger.info(to_json(result))
