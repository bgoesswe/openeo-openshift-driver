""" Processes Models """

import enum
from datetime import datetime
from typing import Any, Tuple

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, Float, ForeignKey, Integer, JSON, String,\
    TEXT, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base: Any = declarative_base()

data_type_enum = Enum(
    'array',
    'boolean',
    'integer',
    'null',
    'number',
    'object',
    'string',
    name='data_type',
)


class ProcessDefinitionEnum(enum.Enum):
    predefined = 'predefined'
    user_defined = 'user_defined'


process_definition_enum = Enum(
    ProcessDefinitionEnum,
    name='process_definition',
)


class ProcessGraph(Base):
    """ Base model for a process graph. """

    __tablename__ = 'process_graphs'

    id = Column(String, primary_key=True)
    id_openeo = Column(String, nullable=False)
    process_definition = Column(process_definition_enum, nullable=False)
    user_id = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    description = Column(TEXT, nullable=True)
    deprecated = Column(Boolean, default=False, nullable=True)
    experimental = Column(Boolean, default=False, nullable=True)
    process_graph = Column(JSON, default={})  # TODO also store as separate table!
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    categories = relationship('Category', cascade='all, delete, delete-orphan')
    parameters = relationship('Parameter', foreign_keys='Parameter.process_graph_id',
                              cascade='all, delete, delete-orphan')
    returns = relationship('Return', uselist=False, cascade='all, delete, delete-orphan')
    exceptions = relationship('ExceptionCode', cascade='all, delete, delete-orphan')
    links = relationship('Link', cascade='all, delete, delete-orphan')
    examples = relationship('Example', cascade='all, delete, delete-orphan')

    UniqueConstraint('id_openeo', 'user_id', name='uq_process_graph_user_id')


class Example(Base):

    __tablename__ = 'example'

    id = Column(Integer, primary_key=True)
    process_graph_id = Column(String, ForeignKey('process_graphs.id'))
    process_graph = Column(JSON, nullable=True)  # TODO also store as separate table!
    arguments = Column(JSON, nullable=True)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    returns = Column(String, nullable=True)
    return_type = Column(String, nullable=True)

    CheckConstraint('process_graph' != None or 'arguments' != None, name='check_process_graph_or_arguments')  # noqa


class Parameter(Base):

    __tablename__ = 'parameter'

    id = Column(Integer, primary_key=True)
    process_graph_id = Column(String, ForeignKey('process_graphs.id'))
    schema_id = Column(Integer, ForeignKey('schema.id'))
    name = Column(String, nullable=False)
    description = Column(TEXT, nullable=False)
    optional = Column(Boolean, default=False, nullable=True)
    deprecated = Column(Boolean, default=False, nullable=True)
    experimental = Column(Boolean, default=False, nullable=True)
    default = Column(TEXT, nullable=True)
    default_type = Column(String, nullable=True)

    schemas = relationship('Schema', foreign_keys='Schema.parameter_id', cascade='all, delete, delete-orphan')


class Return(Base):

    __tablename__ = 'return'

    id = Column(Integer, primary_key=True)
    process_graph_id = Column(String, ForeignKey('process_graphs.id'))
    description = Column(TEXT, nullable=True)

    schemas = relationship('Schema', foreign_keys='Schema.return_id', cascade='all, delete, delete-orphan')


class Category(Base):

    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    process_graph_id = Column(String, ForeignKey('process_graphs.id'))
    name = Column(String, nullable=False)


class Schema(Base):

    __tablename__ = 'schema'

    id = Column(Integer, primary_key=True)
    parameter_id = Column(Integer, ForeignKey('parameter.id'), nullable=True)
    return_id = Column(Integer, ForeignKey('return.id'), nullable=True)
    subtype = Column(String, nullable=True)
    pattern = Column(String, nullable=True)
    minimum = Column(Float, nullable=True)
    maximum = Column(Float, nullable=True)
    min_items = Column(Float, default=0, nullable=True)
    max_items = Column(Float, nullable=True)
    items = Column(JSON, nullable=True)
    additional = Column(JSON, nullable=True)

    types = relationship('SchemaType', cascade='all, delete, delete-orphan')
    enums = relationship('SchemaEnum', cascade='all, delete, delete-orphan')
    parameters = relationship('Parameter', foreign_keys='Parameter.schema_id', cascade='all, delete, delete-orphan')

    __table_args__: Tuple = (
        CheckConstraint(min_items >= 0, name='check_min_items_positive'),
        CheckConstraint(max_items >= 0, name='check_max_items_positive'),
        {})


class SchemaType(Base):

    __tablename__ = 'schema_type'

    id = Column(Integer, primary_key=True)
    schema_id = Column(Integer, ForeignKey('schema.id'))
    name = Column(data_type_enum, nullable=False)


class SchemaEnum(Base):

    __tablename__ = 'schema_enum'

    id = Column(Integer, primary_key=True)
    schema_id = Column(Integer, ForeignKey('schema.id'))
    name = Column(TEXT, nullable=False)


class ExceptionCode(Base):

    __tablename__ = 'exception'

    id = Column(Integer, primary_key=True)
    process_graph_id = Column(String, ForeignKey('process_graphs.id'))
    description = Column(TEXT, nullable=True)
    message = Column(TEXT, nullable=False)
    http = Column(Integer, default=400)
    error_code = Column(String, nullable=False)


class Link(Base):

    __tablename__ = 'link'

    id = Column(Integer, primary_key=True)
    process_graph_id = Column(String, ForeignKey('process_graphs.id'))
    rel = Column(String, nullable=False)
    href = Column(String, nullable=False)  # should be uri!
    type = Column(String, nullable=True)
    title = Column(String, nullable=True)
