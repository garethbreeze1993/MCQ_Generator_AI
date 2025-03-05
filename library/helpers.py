import os
import logging
from django.conf import settings

import chromadb
import chromadb.utils.embedding_functions as embedding_functions


from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from library.models import LibDocumentEmbeddings

logger = logging.getLogger("django_mcq")


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
        "n_results": 10
    }


    if filter_docs:

        query_params["where"] = {
            "source": {"$in": filter_docs}
        }

    results = collection.query(**query_params)


    logger.info('results messy')
    logger.info(results)
    return f'AI MESSAGE answering {user_message}'




