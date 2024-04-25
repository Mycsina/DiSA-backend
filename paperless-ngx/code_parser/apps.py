from django.apps import AppConfig

from c.signals import code_consumer_declaration


class PaperlessTesseractConfig(AppConfig):
    name = "paperless_tesseract"

    def ready(self):
        from documents.signals import document_consumer_declaration

        document_consumer_declaration.connect(code_consumer_declaration)

        AppConfig.ready(self)
