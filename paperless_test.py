import asyncio
from pypaperless import Paperless
from pypaperless.models.common import MatchingAlgorithmType


paperless = Paperless("http://localhost:8001", "3e80c1eec3a65b72e3a4c86292301fde363ffd7a")


async def main():
    async with paperless:

        draft = paperless.documents.draft(
            document=b"1010",
        )
        new_pk = await draft.save()
        print(new_pk)


asyncio.run(main())
