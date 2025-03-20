import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    user_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    chat_id = sq.Column(sq.BigInteger, unique=True, nullable=False)


class Word(Base):
    __tablename__ = 'word'
    word_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    ru_meaning = sq.Column(sq.String, nullable=False)
    en_meaning = sq.Column(sq.String, nullable=False)
    is_general = sq.Column(sq.SmallInteger, nullable=False, default=0)


class User_Word(Base):
    __tablename__ = 'user_word'
    user_id = sq.Column(sq.Integer, sq.ForeignKey('user.user_id'), primary_key=True)
    word_id = sq.Column(sq.Integer, sq.ForeignKey('word.word_id'), primary_key=True)
    user = relationship(User, backref='user_word')
    word = relationship(Word, backref='user_word')