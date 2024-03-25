from datetime import datetime
import uuid

from classes.event import Event
from storage.main import Base
# from sqlalchemy import UUID, Column, Enum, ForeignKey, String, Integer
# from sqlalchemy.orm import relationship, attribute_keyed_dict
from typing import List, Optional
from sqlmodel import Field, SQLModel, ForeignKey, Relationship

from classes.user import UserRole
from classes.collection import ShareState

# Look into SQLModel for a more concise way to define models


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
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    token: str = Field(unique=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
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
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    owner: uuid.UUID = Field(index=True, nullable=False, ForeignKey="user.id")
    submission_date: datetime = Field(default_factory=datetime.now, nullable=False)
    last_update: Optional[datetime] = Field(default=None)
    share_state: ShareState = Field(default=ShareState.PRIVATE, nullable=False)
    access_from_date: Optional[datetime] = Field(default=None)
    description: Optional[str] = Field(default=None)
    root = Field(nullable=False, ForeignKey="folder.id")
    root_folder: Relationship = Relationship("Folder", back_populates="root")


# class Document(Base):
#     __tablename__ = "documents"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String)
#     size = Column(Integer)
#     history = Column(UUID(as_uuid=True), index=True)
class Document(SQLModel, table=True):
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    folder: uuid.UUID = Field(index=True, nullable=False, ForeignKey="folder.id")
    name: str = Field(nullable=False)
    content: bytes = Field(nullable=False)
    size: int = Field(nullable=False)
    submission_date: datetime = Field(default_factory=datetime.now, nullable=False)
    last_updated: Optional[datetime] = Field(default=None)
    access_from_date: Optional[datetime] = Field(default=None)
    history: List[Event] = Field(default_factory=list)


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
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, nullable=False)
    access_from_date: Optional[datetime] = Field(default=None)
    parent_id: Optional[uuid.UUID] = Field(default=None, ForeignKey="folder.id")
    parent: Relationship = Relationship("Children", back_populates="children", remote_side=[id])
    children: Relationship = Relationship("Parent", back_populates="parent", cascade="all, delete-orphan", collection_class=attribute_keyed_dict("name"))

