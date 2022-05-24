import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Posts(SqlAlchemyBase):
    __tablename__ = 'posts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, unique=True)
    topic = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    text = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    media = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    media_type = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    media_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    poster = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    likes = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    dislikes = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    raters_like = sqlalchemy.Column(sqlalchemy.String, nullable=True, default="")
    raters_dislike = sqlalchemy.Column(sqlalchemy.String, nullable=True, default="")
    board_name = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("boards.name"), nullable=False)
    parent_post = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    time = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)

    board = orm.relation("Boards")
