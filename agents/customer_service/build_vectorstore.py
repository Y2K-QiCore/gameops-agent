"""
运行一次即可，生成向量库到 data/vectorstore/
命令：python agents/customer_service/build_vectorstore.py
"""
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

FAQ_PATH        = Path(__file__).parent.parent.parent / "knowledge_base" / "game_faq.md"
VECTORSTORE_DIR = Path(__file__).parent.parent.parent / "data" / "vectorstore"

def build():
    # 1. 读取 FAQ 文档
    raw_text = FAQ_PATH.read_text(encoding="utf-8")

    # 2. 按 Markdown 标题切分，保留层级结构
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#",  "category"),   # 一级标题：充值问题/账号问题...
            ("##", "question"),   # 二级标题：具体问题
        ],
        strip_headers=False,
    )
    docs = splitter.split_text(raw_text)

    print(f"切分后共 {len(docs)} 个文档片段")
    for i, doc in enumerate(docs):
        print(f"  [{i}] {doc.metadata} | {doc.page_content[:40]}...")

    # 3. 向量化并持久化
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
        collection_name="game_faq",
    )

    print(f"\n向量库已保存至 {VECTORSTORE_DIR}")
    print(f"共写入 {vectorstore._collection.count()} 条向量")

    # 4. 验证一条检索
    test_query = "充值了没收到钻石"
    results = vectorstore.similarity_search(test_query, k=2)
    print(f"\n测试检索：'{test_query}'")
    for r in results:
        print(f"  → {r.metadata} | {r.page_content[:60]}...")

if __name__ == "__main__":
    build()