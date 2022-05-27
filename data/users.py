import sqlalchemy

from .db_session import SqlAlchemyBase


class Users(SqlAlchemyBase):
    __tablename__ = 'users'

    ip = sqlalchemy.Column(sqlalchemy.String, primary_key=True, nullable=False, unique=True)
    admin_level = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    is_banned = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)