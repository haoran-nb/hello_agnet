import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

def ingest_docs():
    # 1. 读取本地知识库文本
    knowledge_file = "knowledge/company_policy.txt"
    if not os.path.exists(knowledge_file):
        os.makedirs("knowledge")
        with open(knowledge_file, "w", encoding="utf-8") as f:
            f.write("中安质环分发合规规定：财务类文件必须抄送至 cw@zhzh.com；合规指南3.0版属于业务部，必须发给 3483903590@qq.com。")

    loader = TextLoader(knowledge_file, encoding="utf-8")
    documents = loader.load()

    # 2. 文本切块 (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
    chunks = text_splitter.split_documents(documents)
    
    # 3. 初始化本地向量数据库 ChromaDB (持久化在本地 ./chroma_db 路径)
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    # 使用 Chroma 自带的默认轻量级 Embedding 函数（无需联网和 API Key，最适合演示）
    collection = chroma_client.get_or_create_collection(name="company_knowledge")

    # 4. 批量写入数据库
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk.page_content],
            ids=[f"id_{i}"]
        )
    print("🏆 内部知识库向量化成功！已持久化至本地 ./chroma_db")

if __name__ == "__main__":
    ingest_docs()