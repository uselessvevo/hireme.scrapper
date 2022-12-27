import dataclasses as dt


@dt.dataclass
class User:
    id: int
    curator_id: int
    firstname: str
    middlename: str
    patronymic: str
    email: str
    password: str
    is_employee: bool
    resume_url: str
    filter_url: str
    filter_data: dict = dt.field(default_factory=dict)
