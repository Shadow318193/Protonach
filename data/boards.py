import sqlalchemy
from .db_session import SqlAlchemyBase


class Boards(SqlAlchemyBase):
    __tablename__ = 'boards'

    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True, nullable=True)
    full_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
