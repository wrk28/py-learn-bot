import json
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from models import Base, User, Word, User_Word


class DBUtils:
    def __init__(self, engine: sq.Engine):
        self.Session = sessionmaker(engine)
        self.session = None

    def _start_session(self):
        self.session = self.Session()

    def _close_session(self):
        if self.session:
            self.session.close()
        self.session = None

    def close(self):
        self._close_session()

    def _add_general_words(self, user_id):
        self._start_session()
        result = self.session.query(Word.word_id).filter(Word.is_general == 1)
        for word in result.all():
            user_word = User_Word(user_id=user_id, word_id=word[0])
            self.session.add(user_word)
        self.session.commit()
        self._close_session()

    def _add_new_user(self, chat_id) -> int:
        self._start_session()
        new_user = User(chat_id=chat_id)
        self.session.add(new_user)
        self.session.commit()
        user_id = new_user.user_id
        self._close_session()
        self._add_general_words(user_id)
        return user_id

    def check_user(self, chat_id: int) -> int:
        self._start_session()
        result = self.session.query(User).filter(User.chat_id == chat_id).one_or_none()
        self._close_session()
        if result:
            user_id = result.user_id
        else:
            user_id = self._add_new_user(chat_id)
        return user_id
    
    def next_word(self, chat_id: int) -> list:
        other_words = []
        user_id = self.check_user(chat_id)
        self._start_session()
        result = self.session.query(Word).join(User_Word, Word.word_id == User_Word.word_id)\
            .filter(User_Word.user_id == user_id).order_by(sq.func.random()).limit(4).all()
        self._close_session()
        first_word = result.pop()
        for item in result:
            other_words.append(item.en_meaning)
        question = {"ru_meaning": first_word.ru_meaning, "en_meaning": first_word.en_meaning, "other_words": other_words}
        return question
    
    def add_word(self, chat_id: int, word: dict) -> int:
        user_id = self.check_user(chat_id)
        self._start_session()
        word_id = self.session.query(sq.func.max(Word.word_id)).scalar() + 1
        new_word = Word(word_id=word_id, ru_meaning=word['ru_meaning'], en_meaning=word['en_meaning'])
        self.session.merge(new_word)
        self.session.commit()
        word_id = self.session.query(Word)\
            .filter((Word.ru_meaning == word['ru_meaning']) & (Word.en_meaning == word['en_meaning'])).limit(1).first().word_id
        new_user_word = User_Word(user_id=user_id, word_id=word_id)
        self.session.merge(new_user_word)
        self.session.commit()
        words_number = self.session.query(User_Word).filter(User_Word.user_id == user_id).count()
        self._close_session()
        return words_number

    def remove_word(self, chat_id :int, word: str) -> int:
        user_id = self.check_user(chat_id)
        self._start_session()
        list_word_id = self.session.query(Word.word_id).filter(Word.ru_meaning == word).one_or_none()
        result = None
        if list_word_id:
            self.session.query(User_Word).filter((User_Word.user_id==user_id) & (User_Word.word_id.in_(list_word_id))).delete()
            self.session.commit()
            result = len(list_word_id)
        self._close_session()
        return result
    
    @classmethod
    def make_database(cls, engine: sq.Engine, remove_tables: bool = False, create_db: bool = False):
        if remove_tables:
            Base.metadata.drop_all(engine)
        if create_db:
            Base.metadata.create_all(engine) 
    
    def fill_data(self, path: str):
        self._start_session()
        with open(path) as f:
            data = json.load(f)
        for item in data:
            model = {
                "user": User,
                "word": Word,
                "user_word": User_Word
            }[item.get('model')]
            self.session.add(model(**item.get('fields')))
        self.session.commit()
        self._close_session() 