from typing import Any
from pypaperless import Paperless
from pypaperless.models.common import MatchingAlgorithmType
from pypaperless.exceptions import JsonResponseWithError

from storage.main import PAPERLESS_TOKEN, PAPERLESS_URL


def spawn_paperless():
    # TODO: suppress warning during initialization
    return Paperless(PAPERLESS_URL, PAPERLESS_TOKEN)


async def save_draft(name: str, draft: Any) -> str | int:
    try:
        new_id = await draft.save()
        print(new_id)
    except JsonResponseWithError as e:
        if "unique constraint" in str(e):
            raise ValueError(f"{name} with this name already exists")
    except Exception as e:
        raise ValueError(f"Failed to create {name}: {e}")
    finally:
        return new_id


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
        new_id = await save_draft("Document", draft)
        print(new_id)
        if type(new_id) is not str:
            raise ValueError("ID string wasn't returned")
        return new_id


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
        new_id = await save_draft("Correspondent", draft)
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
        new_id = await save_draft("Tag", draft)
        if type(new_id) is not int:
            raise ValueError("ID wasn't returned")
        return new_id
