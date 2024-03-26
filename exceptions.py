from fastapi import HTTPException, status

BearerException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)

CMDFailure = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Couldn't validate the CMD session",
)
