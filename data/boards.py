import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Boards(SqlAlchemyBase):
    __tablename__ = 'boards'

    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True, unique=True)
    full_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    about = sqlalchemy.Column(sqlalchemy.Text, nullable=False)

    posts = orm.relation("Posts", back_populates='board')
