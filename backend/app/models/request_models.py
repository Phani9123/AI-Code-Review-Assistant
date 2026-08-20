from pydantic import BaseModel


class CodeRequest(BaseModel):
    language: str
    filename: str
    code: str