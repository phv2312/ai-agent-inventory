from pydantic import BaseModel


class GeneratedQA(BaseModel):
    query: str
    answer: str


class GeneratedQAs(BaseModel):
    pairs: list[GeneratedQA]
