from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import (
    ClassVar as _ClassVar,
)

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class SeniorityRequestBatch(_message.Message):
    __slots__ = ("batch",)
    BATCH_FIELD_NUMBER: _ClassVar[int]
    batch: _containers.RepeatedCompositeFieldContainer[SeniorityRequest]
    def __init__(self, batch: _Iterable[SeniorityRequest | _Mapping] | None = ...) -> None: ...

class SeniorityRequest(_message.Message):
    __slots__ = ("company", "title", "uuid")
    UUID_FIELD_NUMBER: _ClassVar[int]
    COMPANY_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    uuid: int
    company: str
    title: str
    def __init__(
        self,
        uuid: int | None = ...,
        company: str | None = ...,
        title: str | None = ...,
    ) -> None: ...

class SeniorityResponseBatch(_message.Message):
    __slots__ = ("batch",)
    BATCH_FIELD_NUMBER: _ClassVar[int]
    batch: _containers.RepeatedCompositeFieldContainer[SeniorityResponse]
    def __init__(self, batch: _Iterable[SeniorityResponse | _Mapping] | None = ...) -> None: ...

class SeniorityResponse(_message.Message):
    __slots__ = ("seniority", "uuid")
    UUID_FIELD_NUMBER: _ClassVar[int]
    SENIORITY_FIELD_NUMBER: _ClassVar[int]
    uuid: int
    seniority: int
    def __init__(self, uuid: int | None = ..., seniority: int | None = ...) -> None: ...
