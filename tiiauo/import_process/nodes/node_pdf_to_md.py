from pathlib import Path
from typing import Any

from tiiauo.config.config import MineruConfig
from tiiauo.import_process.base import NodeBase
from tiiauo.import_process.state import ImportGraphState
from tiiauo.tool.logger import logger
from tiiauo.tool.to_json_format import to_json


class NodePDFToMD(NodeBase):
    """
    PDF 转 Markdown 节点：PDF结构化解析
    """

    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState):

        # 判断PDF文件路径是否提供&文件是否存在
        local_dir_obj, pdf_path_obj = self.check_path(state)

        # 判断api_token是否正确提供
        token = self.get_mineru_token()

        # 上传pdf文件并获取batch_id
        batch_id = self.get_batch_id(pdf_path_obj,token)

        # 根据batch_id轮询获取解析结果----zip_url(同样是像mineru服务器发起请求)
        zip_url = self.get_zip_url(batch_id,token)

        # 根据zip_url下载zip文件
        zip_path = self.download_zip(local_dir_obj, pdf_path_obj, zip_url)

        # 解压文件并进行处理(重命名)
        new_md_path_obj = self.unzip_file_with_rename(local_dir_obj, pdf_path_obj, zip_path)

        return {"md_path": str(new_md_path_obj)}

    def get_mineru_token(self) -> str:
        token = MineruConfig.mineru_api

        if not isinstance(token, str) or not token.strip():
            logger.error("未配置 MinerU API Token，请检查环境变量 MINERU_API")
            raise ValueError("缺少 MinerU API Token 配置：MINERU_API")

        return token.strip()

    def unzip_file_with_rename(self, local_dir_obj: Path, pdf_path_obj: Path, zip_path: Path):
        import zipfile
        import shutil
        unzipped_file_path_obj = local_dir_obj / pdf_path_obj.stem
        if unzipped_file_path_obj.exists():
            shutil.rmtree(unzipped_file_path_obj)
        unzipped_file_path_obj.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            zip_file.extractall(unzipped_file_path_obj)

        logger.info(f"zip文件解压成功，解压路径：{unzipped_file_path_obj}")

        # 重命名
        origin_md_path_obj = unzipped_file_path_obj / "full.md"

        if not origin_md_path_obj.is_file():
            raise FileNotFoundError(
                f"解压结果中不存在预期的 Markdown 文件：{origin_md_path_obj}"
            )
        new_md_path_obj = origin_md_path_obj.with_name(f"{pdf_path_obj.stem}.md")
        origin_md_path_obj.rename(new_md_path_obj)

        logger.info(f"md文件重命名成功，重命名路径：{new_md_path_obj}")

        return new_md_path_obj

    def download_zip(self, local_dir_obj: Path, pdf_path_obj: Path, zip_url) -> Path:
        import requests

        zip_path = local_dir_obj / f"{pdf_path_obj.stem}.zip"
        res_download = requests.get(zip_url)
        # 此处虽然是请求,但所需的二进制文件可以直接获取到,而不是像之前那样数据在json中,所以不需要转json再深入判断
        if res_download.status_code == 200:
            with open(zip_path, 'wb') as f:
                f.write(res_download.content)
                logger.info(f"zip文件下载成功，保存路径：{zip_path}")
        else:
            logger.error(f"zip文件下载失败，状态码：{res_download.status_code}")
            raise ValueError(f"zip文件下载失败，状态码：{res_download.status_code}")
        return zip_path

    def get_zip_url(self, batch_id,token) -> Any:
        import requests
        import time
        url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        total_time = 300
        deadline = time.monotonic() + total_time
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("等待时间过长")
            try:
                response = requests.get(url, headers=header,timeout=10)
            except requests.RequestException as e:
                logger.warning(f"轮询请求异常，将重试：{e}")
            else:
                if response.status_code != 200:
                    raise ValueError(f"请求失败,状态码：{response.status_code}")

                try:
                    result = response.json()
                except ValueError:
                    raise ValueError(f"返回数据不是JSON:{response.text[:200]}")

                if result["code"] != 0:
                    raise ValueError(f"请求数据失败,{result['msg']}")

                data = result["data"]['extract_result'][0]

                if data["state"] == "done":
                    logger.info("解析完成")
                    zip_url = data["full_zip_url"]
                    return zip_url

                elif data["state"] == "failed":
                    raise ValueError(f"解析失败:{data.get('err_msg')}")

                else:
                    logger.info("解析进行中，等待2秒后重新轮询")

            time.sleep(2)

    def get_batch_id(self, pdf_path_obj: Path,token:str) -> Any:
        import requests

        url = "https://mineru.net/api/v4/file-urls/batch"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "files": [
                {"name": pdf_path_obj.name, "data_id": "abcd"}
            ],
            "model_version": "vlm"
        }
        file_path = [str(pdf_path_obj)]

        # 发起请求,获取batch_id
        # 一旦进行请求,必须优先考虑三层判断
        # 1. 请求是否成功
        # 2. 请求返回数据是否成功
        # 3. 请求返回结果是否完整
        try:
            response = requests.post(url, headers=header, json=data, timeout=10)
            if response.status_code != 200:
                raise ValueError(f"请求失败,状态码：{response.status_code}")

            try:
                result = response.json()
            except ValueError:
                raise ValueError(f"返回数据不是JSON:{response.text[:200]}")

            if result["code"] != 0:
                raise ValueError(f"请求数据失败,{result['msg']}")

            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]

            if len(urls) != len(file_path):
                raise ValueError(f"上传地址数量与文件数量不一致：urls={len(urls)}, files={len(file_path)}")

            for i in range(len(urls)):
                with open(file_path[i], 'rb') as f:
                    res_upload = requests.put(urls[i], data=f, timeout=60)
                    if res_upload.status_code == 200:
                        logger.info(f"{file_path[i]} 文件上传成功")
                    else:
                        logger.error(f"{file_path[i]} 文件上传失败")
                        raise RuntimeError(f"批次 {batch_id} 已创建，但 PDF 上传失败，状态码：{res_upload.status_code}")

        except Exception:
            logger.exception("文件上传流程失败")
            raise

        return batch_id

    def check_path(self, state: ImportGraphState) -> tuple[Path, Path]:

        pdf_path = state.get("pdf_path", "")
        if not pdf_path:
            logger.error("未提供PDF文件路径")
            raise ValueError("PDF文件路径不能为空")
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            logger.error("PDF文件不存在")
            raise ValueError("PDF文件不存在")
        if not pdf_path_obj.is_file():
            logger.error(f"PDF 路径不是文件：{pdf_path_obj}")
            raise ValueError(f"PDF 路径不是文件：{pdf_path_obj}")

        # 判断输出目录路径是否提供&目录是否存在，不存在则创建
        local_dir = state.get("local_dir", "")
        if not local_dir:
            logger.error("未提供输出目录路径")
            raise ValueError("输出目录路径不能为空")

        local_dir_obj = Path(local_dir)
        if local_dir_obj.exists() and not local_dir_obj.is_dir():
            logger.error(f"输出路径存在，但不是目录：{local_dir_obj}")
            raise NotADirectoryError(f"输出路径存在，但不是目录：{local_dir_obj}")
        local_dir_obj.mkdir(parents=True, exist_ok=True)


        return local_dir_obj, pdf_path_obj


if __name__ == '__main__':
    node = NodePDFToMD()
    init_state = {
        "pdf_path": r"D:\资料\资料\11、掌柜智库01\资料\05-设备手册汇总\doc\hak180产品安全手册.pdf",
        "local_dir":r"D:\Learn_AI\RAGProjectData"
    }
    result = node.process(init_state)
    logger.info(to_json(result))
