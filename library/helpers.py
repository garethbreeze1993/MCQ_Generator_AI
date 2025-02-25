import logging
from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger("django_mcq")


def upload_document_to_library(file_path):
    # embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=settings.OPEN_API_KEY)

    loader = PyPDFLoader(file_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    all_splits = text_splitter.split_documents(docs)

    for split in all_splits:
        logger.debug(split)