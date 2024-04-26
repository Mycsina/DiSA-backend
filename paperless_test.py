import asyncio

from utils.paperless import create_correspondent, create_document, create_tag


async def main():
    tag = await create_tag(
        name="Test Tag",
    )
    print(tag)
    correspondent = await create_correspondent(
        name="Test Correspondent",
    )
    print(correspondent)
    document = await create_document(
        title="Test Document",
        document=b"Test Document",
        correspondent=correspondent,
        tags=tag,
    )
    print(document)


asyncio.run(main())
