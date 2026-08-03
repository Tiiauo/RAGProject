from pathlib import Path

from tiiauo.import_process.base import NodeBase
from tiiauo.import_process.state import ImportGraphState
from tiiauo.tool.logger import logger
from tiiauo.tool.to_json_format import to_json


class NodeEntry(NodeBase):
    """
    入口节点：任务分发
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):
        local_file_path = state.get("local_file_path", "")
        if not local_file_path:
            logger.error("缺少文件路径")
            raise ValueError("文件路径不能为空")

        local_file_path_obj = Path(local_file_path)

        if not local_file_path_obj.exists():
            logger.error(f"文件不存在")
            raise FileNotFoundError(f"文件不存在：{local_file_path}")
        if not local_file_path_obj.is_file():
            logger.error(f"PDF 路径不是文件：{local_file_path_obj}")
            raise ValueError(f"PDF 路径不是文件：{local_file_path_obj}")

        file_title = local_file_path_obj.stem
        suffix = local_file_path_obj.suffix

        if suffix.lower() == ".pdf":
            return {
                "is_pdf_read_enabled": True,
                "file_title": file_title,
                "pdf_path": local_file_path,
            }
        elif suffix.lower() == ".md":
            return {
                "is_md_read_enabled": True,
                "file_title": file_title,
                "md_path": local_file_path,
            }
        else:
            logger.error(f"不支持的文件类型：{suffix}")
            raise ValueError(f"不支持的文件类型：{suffix}")

if __name__ == '__main__':
    node = NodeEntry()
    init_state = {
        "local_file_path":r"D:\资料\资料\11、掌柜智库01\资料\05-设备手册汇总\doc\hak180产品安全手册.txt"
    }
    result = node.process(init_state)
    logger.info(to_json(result))

