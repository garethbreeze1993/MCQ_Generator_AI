import os

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

import logging

# Configure logging
logging.basicConfig(
    filename='pinecone.log',          # Log file name
    level=logging.INFO,          # Log level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    filemode='a'                 # Append mode (use 'w' for overwrite)
)


def main():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY"))
    vector_store = PineconeVectorStore(index_name="lyl-pdf", embedding=embeddings,
                                           pinecone_api_key=os.getenv("PINECONE_API_KEY"))

    results = vector_store.similarity_search(
        "What is the History Of Charcoal",
        k=4,
    )
    logging.info('--------------similarity search --------------------')
    for res in results:
        logging.info(res)


    model = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

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
        search_kwargs={"k": 3, "score_threshold": 0.5},
    )

    question = "What is the History Of Charcoal"
    doc_content = retriever.invoke(question)

    logging.info(doc_content)

    # And a query intended to prompt a language model to populate the data structure.
    chain = prompt | model

    output = chain.invoke({"content": doc_content[0].page_content, "question": question})
    logging.info('-------------OUTPUT-------------------')
    logging.info(output)

if __name__ == "__main__":
    main()
