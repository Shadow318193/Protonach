import sqlalchemy
import datetime
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Posts(SqlAlchemyBase):
    __tablename__ = 'posts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, unique=True)
    topic = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    text = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    media = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    board_name = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("boards.name"))
    parent_post = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    time = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())

    board = orm.relation("Boards")
