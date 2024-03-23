import uuid

from storage.main import Base
from sqlalchemy import UUID, Column, Enum, ForeignKey, String, Integer
from sqlalchemy.orm import relationship, attribute_keyed_dict

from classes.user import UserRole

# TODO -  Look into SQLModel for a more concise way to define models


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    id_token = Column(String)
    token = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner = Column(UUID(as_uuid=True), index=True)
    name = Column(String)
    description = Column(String)
    root = Column(UUID(as_uuid=True), ForeignKey("folder.id"))

    root_folder = relationship("Folder", back_populates="root")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    size = Column(Integer)
    history = Column(UUID(as_uuid=True), index=True)


class Folder(Base):
    __tablename__ = "folder"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("folder.id"))

    parent = relationship("Children", back_populates="children", remote_side=[id])
    children = relationship(
        "Parent",
        back_populates="parent",
        cascade="all, delete-orphan",
        collection_class=attribute_keyed_dict("name"),
    )
