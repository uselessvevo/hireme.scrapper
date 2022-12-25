import dataclasses as dt


@dt.dataclass
class User:
    id: int
    curator_id: int
    firstname: str
    middlename: str
    patronymic: str
    resumeUrl: str
    email: str
    password: str
    is_employee: bool
    resume_url: str
