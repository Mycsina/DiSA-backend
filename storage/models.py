from datetime import datetime
import uuid

from storage.main import Base
# from sqlalchemy import UUID, Column, Enum, ForeignKey, String, Integer
# from sqlalchemy.orm import relationship, attribute_keyed_dict
from typing import Optional
from sqlmodel import Field, SQLModel, ForeignKey, Relationship

from classes.user import UserRole
from classes.collection import ShareState

# TODO -  Look into SQLModel for a more concise way to define models


# class User(Base):
#     __tablename__ = "users"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     username = Column(String, unique=True, index=True)
#     email = Column(String, unique=True, index=True)
#     password = Column(String)
#     id_token = Column(String)
#     token = Column(String)
#     role = Column(Enum(UserRole), default=UserRole.USER)
class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    token: Optional[str] = Field(default=None)
    email: str = Field(index=True, unique=True, nullable=False)
    mobile_key: str = Field(unique=True, nullable=False)
    role: UserRole = Field(default=UserRole.USER)


# class Collection(Base):
#     __tablename__ = "collections"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     owner = Column(UUID(as_uuid=True), index=True)
#     name = Column(String)
#     description = Column(String)
#     root = Column(UUID(as_uuid=True), ForeignKey("folder.id"))

#     root_folder = relationship("Folder", back_populates="root")
class Collection(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    num_documents: int = Field(default=0)
    submission_date: datetime = Field(default_factory=datetime.now, nullable=False)
    last_updated: Optional[datetime] = Field(default=None)
    share_state: ShareState = Field(default=ShareState.PRIVATE, nullable=False)
    owner: uuid.UUID = Field(nullable=False, ForeignKey="user.id")
    access_from_date: Optional[datetime] = Field(default=None)


# class Document(Base):
#     __tablename__ = "documents"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String)
#     size = Column(Integer)
#     history = Column(UUID(as_uuid=True), index=True)
class Document(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    set: str = Field(nullable=False, ForeignKey="collection.id")
    name: str = Field(nullable=False)
    content: bytes = Field(nullable=False)
    size: int = Field(nullable=False)
    submission_date: datetime = Field(default_factory=datetime.now, nullable=False)
    last_updated: Optional[datetime] = Field(default=None)
    access_from_date: Optional[datetime] = Field(default=None)


# class Folder(Base):
#     __tablename__ = "folder"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String)
#     parent_id = Column(UUID(as_uuid=True), ForeignKey("folder.id"))

#     parent = relationship("Children", back_populates="children", remote_side=[id])
#     children = relationship(
#         "Parent",
#         back_populates="parent",
#         cascade="all, delete-orphan",
#         collection_class=attribute_keyed_dict("name"),
#     )
class Folder(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    parent_id: Optional[uuid.UUID] = Field(default=None, ForeignKey="folder.id")
    parent: Relationship = Relationship("Children", back_populates="children", remote_side=[id])
    children: Relationship = Relationship("Parent", back_populates="parent", cascade="all, delete-orphan", collection_class=attribute_keyed_dict("name"))

