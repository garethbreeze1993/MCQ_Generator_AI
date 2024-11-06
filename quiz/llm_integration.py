import logging
from tempfile import NamedTemporaryFile
from typing import List

from openai import OpenAI
from django.conf import settings
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate


logger = logging.getLogger("django_mcq")


class MultiChoiceQuestion(BaseModel):
    question: str
    answers: List[str]
    question_number: int
    correct_answer: str

class MultiChoiceQuizFormat(BaseModel):
    quiz_name: str
    items: List[MultiChoiceQuestion]


example_response_json = """{
  "quiz_name": "Example Quiz Name",
  "items":
[
{"question":  "What is the capital of France?",
  "answers": ["London", "Paris", "New York", "Toulouse"],
  "question_number": 1,
  "correct_answer": "Paris"
},
  {
      "question": "What is the official currency of Germany",
      "answers": ["Euro", "Dollar", "Deutschmark", "Pound"
      ],
      "correct_answer": "Euro",
    "question_number": 2
  }
]
}"""


test_input = """
        You are an expert Multiple Choice Quiz Generator. It is your job to create a quiz of 
        {number_of_questions} questions. 
        
        Use the following content to generate the questions:
        {file_content}
        
        Each question should have four available options with only one being the correct answer.
        Make sure the questions are not repeated and check that all the questions relate to the text above.
        Ensure that there is {number_of_questions}
        Can you format the response like the RESPONSE JSON below.
        The quiz name is based on user input and should be called {quiz_name}.
        RESPONSE JSON = {response_json}
    """


input_template = """
    Text : {quiz_text}
        You are an expert Multiple Choice Quiz Generator. Given the above text it is your job to create a quiz of 
        {number} questions about the above text. Each question should have four available  
        options with only one being the correct answer.
        Make sure the questions are not repeated and check that all the questions relate to the text above.
        Can you format the response like the RESPONSE JSON below. 
        Ensure that there is {number of questions}

        RESPONSE JSON = {response_json}
    """

system_template = """
        You are an expert Multiple Choice Quiz Generator. Each question should have four available  
        options with only one being the correct answer.
        Make sure the questions are not repeated.
        Can you format the response like the RESPONSE JSON below.        
        RESPONSE JSON = {response_json}
    """

user_template = """
    Text : {quiz_text}
    Given the above text it is your job to create a quiz of 
        {number} questions about the above text.
        Ensure that there is {number of questions} and check that all the questions relate to the text above
        """

def execute_llm_prompt_open_ai(temperature):
    model = OpenAI(api_key=settings.OPEN_API_KEY)



def execute_llm_prompt_langchain(number_of_questions: int, quiz_name: str, file):
    model = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPEN_API_KEY)

    with NamedTemporaryFile() as tempfile:

        tempfile.write(file.read())
        tempfile.seek(0)

        loader = TextLoader(tempfile.name)
        documents = loader.load()

    file_content = documents[0].page_content


    # Set up a parser + inject instructions into the prompt template.
    parser = PydanticOutputParser(pydantic_object=MultiChoiceQuizFormat)

    prompt = PromptTemplate(
        template=test_input,
        input_variables=["number_of_questions", "response_json", "quiz_name", "file_content"],
    )

    # And a query intended to prompt a language model to populate the data structure.
    chain = prompt | model | parser
    output = chain.invoke({"number_of_questions": number_of_questions, "response_json": example_response_json,
                           "quiz_name": quiz_name, "file_content": file_content})

    return output.model_dump()

