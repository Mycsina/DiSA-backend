import uuid

from main import Base
from sqlalchemy import UUID, Column, Enum, String

from classes.user import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    id_token = Column(String)
    token = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    owner = Column(UUID(as_uuid=True), index=True)
    name = Column(String)
    description = Column(String)
    documents = Column(UUID(as_uuid=True), index=True)
