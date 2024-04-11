from fastapi import HTTPException, status


def BearerException(detail: str = "Incorrect username or password"):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def CMDFailure(detail: str = "Couldn't validate the CMD session"):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def IntegrityBreach(detail: str = "Integrity Error"):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )
