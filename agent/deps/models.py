from enum import StrEnum, auto


class EmbeddingModel(StrEnum):
    AZURE_OPENAI = auto()


class TextSplitterModel(StrEnum):
    LANGCHAIN = auto()


class ExtractorModel(StrEnum):
    PDF = auto()


class VectorDBModel(StrEnum):
    MILVUS = auto()


class ProgramsModel(StrEnum):
    NAME_SUGGESTION = auto()
