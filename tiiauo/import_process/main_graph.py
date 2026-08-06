from langgraph.constants import END
from langgraph.graph import StateGraph

from tiiauo.import_process.nodes.node_bge_embedding import NodeBGEEmbedding
from tiiauo.import_process.nodes.node_document_split import NodeDocumentSplit
from tiiauo.import_process.nodes.node_entry import NodeEntry
from tiiauo.import_process.nodes.node_import_milvus import NodeImportMilvus
from tiiauo.import_process.nodes.node_item_name_recognition import NodeItemNameRecognition
from tiiauo.import_process.nodes.node_md_img import NodeMDImg
from tiiauo.import_process.nodes.node_pdf_to_md import NodePDFToMD
from tiiauo.import_process.state import ImportGraphState
from tiiauo.tool.logger import logger
from tiiauo.tool.to_json_format import to_json


class ImportMainGraphRunner:
    def __init__(self):
        self.builder = StateGraph(state_schema=ImportGraphState)
        self.add_nodes()
        self.add_edges()
        self.graph = None


    def add_nodes(self):
        self.builder.add_node(NodeEntry.name, NodeEntry())
        self.builder.add_node(NodePDFToMD.name, NodePDFToMD())
        self.builder.add_node(NodeMDImg.name, NodeMDImg())
        self.builder.add_node(NodeDocumentSplit.name, NodeDocumentSplit())
        self.builder.add_node(NodeItemNameRecognition.name, NodeItemNameRecognition())
        self.builder.add_node(NodeBGEEmbedding.name, NodeBGEEmbedding())
        self.builder.add_node(NodeImportMilvus.name, NodeImportMilvus())

    def add_edges(self):
        self.builder.set_entry_point(NodeEntry.name)
        self.builder.add_conditional_edges(NodeEntry.name, self.after_entry_router)
        self.builder.add_edge(NodePDFToMD.name, NodeMDImg.name)
        self.builder.add_edge(NodeMDImg.name, NodeDocumentSplit.name)
        self.builder.add_edge(NodeDocumentSplit.name,NodeItemNameRecognition.name)
        self.builder.add_edge(NodeItemNameRecognition.name,NodeBGEEmbedding.name)
        self.builder.add_edge(NodeBGEEmbedding.name,NodeImportMilvus.name)
        self.builder.add_edge(NodeImportMilvus.name,END)



    def after_entry_router(self, state: ImportGraphState):
        is_md_read_enabled = state.get("is_md_read_enabled", False)
        is_pdf_read_enabled = state.get("is_pdf_read_enabled", False)

        if is_pdf_read_enabled:
            return NodePDFToMD.name
        elif is_md_read_enabled:
            return NodeMDImg.name
        else:
            return END


    def run(self, state: ImportGraphState):
        if self.graph is None:
            self.graph = self.builder.compile()
        res = self.graph.invoke(state)
        return res


    @classmethod
    def create_and_run(cls, state: ImportGraphState):
        return cls().run(state)



if __name__ == '__main__':
    init_state = {
        "task_id": "T1-hak180产品安全手册",
        "local_file_path":r"D:\资料\资料\掌柜智库\资料\05-设备手册汇总\doc\hak180产品安全手册.pdf",
        "local_dir":r"D:\Learn_AI\RAGProjectData"
    }
    result = ImportMainGraphRunner.create_and_run(init_state)
    logger.info(to_json(result))