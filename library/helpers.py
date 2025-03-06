import os
import logging
from django.conf import settings

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from langchain_openai import ChatOpenAI

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader

from library.models import LibDocumentEmbeddings

logger = logging.getLogger("django_mcq")


library_chat_prompt = """
"You are an AI assistant designed to provide accurate and helpful responses. 
Below is a user query along with relevant retrieved context from a knowledge base. 
Your task is to answer the query as accurately as possible using only the provided context. 
If the context does not contain the required information, 
indicate that you don't have enough data instead of making up an answer.

User Query:

{user_query}

Retrieved Context:

{retrieved_context}

Instructions:

    Use the retrieved context to answer the query.
    Do not add information that is not present in the context.
    If the context is insufficient, state: 'I don’t have enough information to answer this query based on the provided data.'
    Keep the response concise and informative."
"""


def upload_document_to_library(file_path, unique_user, new_id):
    chroma_path = os.path.join(settings.BASE_DIR, "chroma_db_storage")
    chroma_client = chromadb.PersistentClient(path=chroma_path)

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPEN_API_KEY,
        model_name="text-embedding-3-large"
    )


    collection = chroma_client.get_or_create_collection(name=unique_user, embedding_function=openai_ef)

    loader = PyPDFLoader(file_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    all_splits = text_splitter.split_documents(docs)

    id_list = []
    page_content_list = []
    metadata_list = []

    for split in all_splits:
        id_list.append(f'id{new_id}')
        page_content_list.append(split.page_content)
        metadata_list.append(split.metadata)
        new_id += 1


    collection.upsert(
        ids=id_list,
        metadatas=metadata_list,
        documents=page_content_list,
    )

    logger.info(collection.count())

    logger.info(id_list[-1])
    final_id = get_final_id(id_list[-1])

    return final_id

def get_final_id(num: str):
    n = num.split('id')
    try:
        x = n[-1]
        fin = int(x)
    except Exception:
        return False
    else:
        return fin

def delete_document_from_library(number_of_documents: int, document_pk: int, unique_user: str):

    chroma_path = os.path.join(settings.BASE_DIR, "chroma_db_storage")
    chroma_client = chromadb.PersistentClient(path=chroma_path)

    if number_of_documents == 1:
        chroma_client.delete_collection(name=unique_user)
        return

    lib_doc = LibDocumentEmbeddings.objects.get(document_id=document_pk)

    start_id = lib_doc.start_id

    end_id = lib_doc.end_id

    list_of_ids = [f"id{i}" for i in range(start_id, end_id + 1)]

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPEN_API_KEY,
        model_name="text-embedding-3-large"
    )

    collection = chroma_client.get_or_create_collection(name=unique_user, embedding_function=openai_ef)

    collection.delete(
        ids=list_of_ids
    )

    return

def answer_user_message_library(user_message, unique_user, filter_docs):
    chroma_path = os.path.join(settings.BASE_DIR, "chroma_db_storage")
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPEN_API_KEY,
        model_name="text-embedding-3-large"
    )
    collection = chroma_client.get_or_create_collection(name=unique_user, embedding_function=openai_ef)

    query_params = {
        "query_texts": [user_message],
        "n_results": 3
    }


    if filter_docs:

        query_params["where"] = {
            "source": {"$in": filter_docs}
        }

    results = collection.query(**query_params)

    page_content_str = ""

    for document in results["documents"]:
        for doc in document:
            page_content_str += doc

    model = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPEN_API_KEY)

    prompt = PromptTemplate(
        template=library_chat_prompt,
        input_variables=["retrieved_context", "user_query"],
    )

    # And a query intended to prompt a language model to populate the data structure.
    chain = prompt | model

    output = chain.invoke({"retrieved_context": page_content_str, "user_query": user_message})

    return output





