from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.tools.retriever import create_retriever_tool
from langchain_openai import OpenAIEmbeddings


# 문서 로더 생성
loader = PyPDFLoader("app/data/rag_introduction.pdf")

# 텍스트 스플리터 생성
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# 문서 스플리트
split_docs = loader.load_and_split(text_splitter)

# 벡터스토어 생성
vectorstore = InMemoryVectorStore.from_documents(
    documents=split_docs,
    embedding=OpenAIEmbeddings()
    )

# 리트리버 생성
retriever = vectorstore.as_retriever()

# 리트리버 툴 생성
retriever_tool = create_retriever_tool(
    retriever,
    name="rag_introduction_retriever",
    description="A tool that can be used to retrieve information from the rag_introduction.pdf file"`
)