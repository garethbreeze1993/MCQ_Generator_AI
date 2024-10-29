from typing import List

from openai import OpenAI
from django.conf import settings
from pydantic import BaseModel

from langchain_openai import ChatOpenAI

class MultiChoiceQuestion(BaseModel):
    pass

class MultiChoiceQuizFormat(BaseModel):
    quiz_name: str
    items: List[dict]




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

def execute_llm_prompt_open_ai(temperature):
    model = OpenAI(api_key=settings.OPEN_API_KEY)

    input_template = """
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


def execute_llm_prompt_langchain(temperature):
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPEN_API_KEY)