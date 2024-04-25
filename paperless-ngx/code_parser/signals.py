def get_parser(*args, **kwargs):
    from c.parsers import CodeDocumentParser

    return CodeDocumentParser(*args, **kwargs)


def code_consumer_declaration(sender, **kwargs):
    return {
        "parser": get_parser,
        "weight": 0,
        "mime_types": {
            "text/x-python": ".py",
            "text/x-c": ".c",
            "text/x-c++": ".cpp",
            "text/x-java-source": ".java",
            "application/x-javascript": ".js",
        },
    }
