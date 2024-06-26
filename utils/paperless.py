import asyncio

from pypaperless import Paperless
from pypaperless.models.common import MatchingAlgorithmType, TaskStatusType

from storage.main import PAPERLESS_TOKEN, PAPERLESS_URL


def spawn_paperless():
    # TODO: suppress warning during initialization
    return Paperless(PAPERLESS_URL, PAPERLESS_TOKEN)


async def create_document(**kwargs) -> str:
    """
    Create a document in Paperless-ngx.

    Args:
        title: str = The title of the document.
        document: bytes = The document to upload. Only required field.
        created: datetime = The date the document was created.
        correspondent: str = ID of the correspondent.
        document_type: str = ID of the document type.
        storage_path: str = ID of the storage.
        tags: str = Specify ID of the tag, specify multiple times for multiple tags.
        archive_serial_number: str = The archive serial number.
        custom_fields: list[str] = Array of custom field IDs.
    """
    paperless = spawn_paperless()
    async with paperless:
        draft = paperless.documents.draft(**kwargs)
        new_id = await draft.save()
        if type(new_id) is not str:
            raise ValueError("ID string wasn't returned")
        return new_id


async def verify_document(task_id: str) -> int:
    """
    Verify a document was consumed successfully.
    """

    paperless = spawn_paperless()
    async with paperless:
        task = await paperless.tasks(task_id)
        while task.status in [TaskStatusType.UNKNOWN, TaskStatusType.PENDING]:
            await asyncio.sleep(1)
            task = await paperless.tasks(task_id)
        if task.status == TaskStatusType.FAILURE:
            if task.result is not None:
                if "duplicate" in task.result:
                    raise ValueError("Document rejected due to being a duplicate")
        if task.status == TaskStatusType.SUCCESS:
            if task.related_document is None:
                print(task)
                raise ValueError("Document wasn't created, but we received a success")
            return task.related_document
        print(task)
        raise ValueError("Document verification failed")


async def create_correspondent(**kwargs) -> int:
    """
    Create a correspondent in Paperless-ngx.

    Args:
        name: str = The name of the correspondent.
        match: str | None = The match string, automatic doesn't accept one.
        matching_algorithm: MatchingAlgorithmType | None = The matching algorithm to use.
        is_insensitive: bool | None = Whether the match should be case insensitive.
        owner: field = The owner of the correspondent.
    """
    # Pypaperless demands us to pass missing fields, regardless if they are required
    data = kwargs
    if "match" not in data:
        data["match"] = ""
    if "matching_algorithm" not in data:
        data["matching_algorithm"] = MatchingAlgorithmType.NONE
    if "is_insensitive" not in data:
        data["is_insensitive"] = False

    paperless = spawn_paperless()
    async with paperless:
        draft = paperless.correspondents.draft(**data)
        new_id = await draft.save()
        if type(new_id) is not int:
            raise ValueError("ID wasn't returned")
        return new_id


async def create_tag(**kwargs) -> int:
    """
    Create a tag in Paperless-ngx.

    Args:
        name: str = The name of the tag.
        colour: str | None = The color of the tag in hex.
        match: str | None = The match string, automatic ignores this.
        matching_algorithm: MatchingAlgorithmType | None = The matching algorithm to use.
        is_insensitive: bool | None = Whether the match should be case insensitive.
        is_inbox_tag: bool | None = Whether the tag is an inbox tag.
        owner: field | None = The owner of the tag.
    """

    def random_color():
        import random

        r = lambda: random.randint(0, 255)  # noqa: E731
        return "#%02X%02X%02X" % (r(), r(), r())

    # Pypaperless demands us to pass missing fields, regardless if they are required
    data = kwargs
    if "color" not in data:
        data["color"] = random_color()
    if "text_color" not in data:
        data["text_color"] = random_color()
    if "match" not in data:
        data["match"] = ""
    if "matching_algorithm" not in data:
        data["matching_algorithm"] = MatchingAlgorithmType.NONE
    if "is_insensitive" not in data:
        data["is_insensitive"] = False
    if "is_inbox_tag" not in data:
        data["is_inbox_tag"] = False

    paperless = spawn_paperless()
    async with paperless:
        draft = paperless.tags.draft(**kwargs)
        new_id = await draft.save()
        if type(new_id) is not int:
            raise ValueError("ID wasn't returned")
        return new_id


async def download_document(document_id: int) -> tuple[bytes, str | None]:
    """
    Download a document from Paperless-ngx.

    Args:
        document_id: str = The ID of the document to download.
    """
    paperless = spawn_paperless()
    async with paperless:
        document = await paperless.documents.download(document_id)
        content = document.content
        if content is None:
            raise ValueError("Document content is empty")
        name = document.disposition_filename
        return content, name
