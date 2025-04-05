from celery import shared_task

import os
import logging
from typing import Optional
from django.conf import settings
from django.db import transaction

import chromadb
import chromadb.utils.embedding_functions as embedding_functions

from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyPDFLoader

from library.utils import get_final_id, get_lists_for_chroma_upsert, get_list_of_ids_for_chroma_deletion

logger = logging.getLogger("django_mcq")


@shared_task
def upload_document_to_library(file_path, unique_user, new_id, document_pk):

    from library import models

    try:

        document = models.LibDocuments.objects.get(pk=document_pk)
        document_embeddings = models.LibDocumentEmbeddings.objects.get(document=document)

    except (models.LibDocuments.DoesNotExist, models.LibDocumentEmbeddings.DoesNotExist):
        raise Exception("Document not found.")

    try:
        need_delete = False
        with transaction.atomic():

            document.status = "processing"
            document.save()

            chroma_path = os.path.join(settings.BASE_DIR, "chroma_db_storage")
            chroma_client = chromadb.PersistentClient(path=chroma_path)

            openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.OPEN_API_KEY,
                model_name="text-embedding-3-large"
            )


            collection = chroma_client.get_or_create_collection(name=unique_user, embedding_function=openai_ef)

            loader = PyPDFLoader(file_path)
            # docs = loader.lazy_load()
            # text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,  # Maximum number of characters in each chunk
                chunk_overlap=20,  # Number of characters to overlap between chunks
                length_function=len,  # Use standard Python len() function to measure chunk size
                separators=["\n\n", "\n", " ", ""]  # Progressively try these separators
            )

            last_id = None
            logger.debug('DOCSSSS')

            for doc in loader.lazy_load():

                page_content = doc.page_content

                if not page_content:
                    continue

                page_chunks = text_splitter.split_text(page_content)

                logger.debug(page_chunks)

                if last_id:
                    new_id = last_id + 1

                id_list, metadata_list = get_lists_for_chroma_upsert(all_splits=page_chunks, new_id=new_id,
                                                                     metadata=doc.metadata)

                logger.info(id_list)
                logger.info(metadata_list)
                logger.info(page_chunks)
                #
                collection.upsert(
                    ids=id_list,
                    metadatas=metadata_list,
                    documents=page_chunks,
                )
                last_id = get_final_id(num=id_list[-1])
                need_delete = True
            #
            logger.info(collection.count())

            logger.info(id_list[-1])
            final_id = get_final_id(num=id_list[-1])

            document.status = "completed"
            document_embeddings.end_id = final_id

            document.save()
            document_embeddings.save()

    except Exception as e:
        logger.error(e)
        document.status = "error"
        document.save()
        document_embeddings.delete()
        if need_delete:
            number_of_documents = models.LibDocuments.objects.filter(user=document.user).count()
            cleanup_failed_document_upload(number_of_documents=number_of_documents,
                                           new_id=new_id, collection=collection, unique_user=unique_user,
                                           chroma_client=chroma_client, last_id=last_id)
        raise Exception(e)

    else:
        return "Success"


@shared_task
def delete_document_from_library(number_of_documents: int, list_of_ids: Optional[list], unique_user: str):

    try:

        chroma_path = os.path.join(settings.BASE_DIR, "chroma_db_storage")
        chroma_client = chromadb.PersistentClient(path=chroma_path)

        if number_of_documents == 1:
            chroma_client.delete_collection(name=unique_user)
            return

        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.OPEN_API_KEY,
            model_name="text-embedding-3-large"
        )

        collection = chroma_client.get_or_create_collection(name=unique_user, embedding_function=openai_ef)

        collection.delete(
            ids=list_of_ids
        )

    except Exception as e:
        logger.error(e)
        raise Exception(e)

    return "Success Delete"


def cleanup_failed_document_upload(number_of_documents: int, new_id: int, collection, unique_user: str, chroma_client,
                                   last_id: int):

    if number_of_documents == 1:
        chroma_client.delete_collection(name=unique_user)
        return

    try:
        # end_id = collection.count()

        end_id = last_id

        list_of_ids = get_list_of_ids_for_chroma_deletion(start_id=new_id, end_id=end_id)

        collection.delete(
            ids=list_of_ids
        )

    except Exception as e:
        logger.error(e)
        return
