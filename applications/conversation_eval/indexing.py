from pathlib import Path
import time
import logging
import asyncio
import yaml
import aiofiles
from uuid import uuid4

from agent.container import Container
from agent.models.document import Chunk, DocumentMetadata, Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConstantIngestor:
    async def validate(self, file_path: Path) -> None:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
            content = await file.read()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")

        return

    async def ingest(self, filepath: Path) -> list[Chunk]:
        await self.validate(filepath)

        async with aiofiles.open(filepath, "r", encoding="utf-8") as file:
            rulebooks = yaml.safe_load(await file.read())

        chunks = []
        for rule_name, rule_constant in rulebooks.items():
            rule_constants = (
                rule_constant if isinstance(rule_constant, list) else [rule_constant]
            )

            chunks.extend(
                [
                    Chunk(
                        chunk_id=uuid4(),
                        text=str(value),
                        metadata=DocumentMetadata(
                            source=Source.DOCUMENT,
                            group_name=rule_name,
                        ),
                    )
                    for idx, value in enumerate(rule_constants, start=1)
                ]
            )

        return chunks


async def main():
    container = Container()
    ingestor = ConstantIngestor()

    chunks = await ingestor.ingest(
        filepath=Path("datas/conversation-eval/constants.yaml")
    )
    logger.info("Created %d chunks from constants", len(chunks))

    # Embed the chunks
    embed_start_time = time.perf_counter()
    embeddings = await container.embeddings.get("azure_openai").aembedding(
        [chunk.text for chunk in chunks]
    )
    logger.info("Embedding time: %.3f", time.perf_counter() - embed_start_time)

    # Insert to Milvus
    milvus_start_time = time.perf_counter()
    await container.vectordbs.get("milvus").add(chunks, embeddings)
    logger.info("Milvus indexing time: %.3f", time.perf_counter() - milvus_start_time)


if __name__ == "__main__":
    asyncio.run(main())
