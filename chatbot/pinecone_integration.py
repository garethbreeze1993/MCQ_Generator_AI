import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader




def main():

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY"))

    vector_store = PineconeVectorStore(index_name="lyl-pdf", embedding=embeddings,
                                       pinecone_api_key=os.getenv("PINECONE_API_KEY"))

    path = '/home/gareth/Documents/lyl'

    loader = DirectoryLoader(path=path, glob="*.pdf")
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    all_splits = text_splitter.split_documents(docs)
    page_content_list = [x.page_content for x in all_splits]
    _ = vector_store.add_texts(texts=page_content_list)

if __name__ == '__main__':
    main()

