import dataclasses as dt


@dt.dataclass
class User:
    id: int
    curatorId: int
    firstname: str
    middlename: str
    patronymic: str
    resumeUrl: str
    email: str
    password: str
    isEmployee: bool
    resumeFilter: str
