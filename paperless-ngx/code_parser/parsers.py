import os
from pathlib import Path

from documents.parsers import DocumentParser


class CodeDocumentParser(DocumentParser):
    logging_name = "disa.parsing.code"

    def get_created_from_metadata(self, document_path: Path) -> float:
        # Get the creation date from the metadata of the document
        return os.path.getctime(document_path)

    def parse(self, document_path: Path, mime_type):
        self.content = document_path.read_text()
        self.date = self.get_created_from_metadata(document_path)

    def get_thumbnail(self, document_path: Path, mime_type: str):
        # Get the thumbnail of the document
        return ""
