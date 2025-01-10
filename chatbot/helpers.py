import logging

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from django.conf import settings

logger = logging.getLogger("django_mcq")

def chatbot_response(user_msg: str):

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=settings.OPEN_API_KEY)
    vector_store = PineconeVectorStore(index_name="lyl-pdf", embedding=embeddings,
                                       pinecone_api_key=settings.PINECONE_API_KEY)

    model = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPEN_API_KEY)

    prompt_template = """
        Use the following pieces of information to answer the users question. If you don't know the answer just say you don't know.
        Don't try and make up an answer.
        Content : {content}
        Question: {question}

        Only return the helpful answer below and nothing else
        Helpful Answer: 
        """

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["content", "question"],
    )

    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 1, "score_threshold": 0.5},
    )

    doc_content = retriever.invoke(user_msg)

    # And a query intended to prompt a language model to populate the data structure.
    chain = prompt | model

    output = chain.invoke({"content": doc_content[0].page_content, "question": user_msg})

    return output