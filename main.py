import os
import dotenv
import json
import sqlalchemy as sq
from telebot import TeleBot, types
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from database_utils import DBUtils
from random import shuffle


class EnvReader:
    def __init__(self, path=None):
        if path:
            dotenv_path = path
        else:
            dotenv_path = os.path.dirname(__file__)
        dotenv.load_dotenv(dotenv_path)
        self.DSN = os.getenv("DSN")
        self.token = os.getenv("TOKEN")
        self.remove_tables = os.getenv('REMOVE_TABLES').lower().strip() in ('true', 't', 'yes', 'y', '1',)
        self.create_db = os.getenv('CREATE_DB').lower().strip() in ('true', 't', 'yes', 'y', '1',)
        self.fill_data = os.getenv('FILL_DATE').lower().strip() in ('true', 't', 'yes', 'y', '1',)
        self.data_file_path = os.getenv('DATA_FILE_PATH')


class Content:
    @classmethod
    def initialize(cls):
        with open('content.json') as f:
                content = json.load(f)
        cls.ADD_WORD = content['add_word']
        cls.REMOVE_WORD = content['remove_word']
        cls.NEXT_WORD = content['next_word']
        cls.GREETING = content['greeting']
        cls.GUESS_WORD = content['guess_word']
        cls.CORRECT = content['correct']
        cls.NOT_CORRECT = content['not_correct']
        cls.ADD_WORD_REQUEST = content['add_word_request']
        cls.ADD_WORD_EXAMPLE = content['add_word_example']
        cls.ADD_WORD_SUCCESS = content['add_word_success']
        cls.REMOVE_WORD_REQUEST = content['remove_word_request']
        cls.REMOVE_WORD_EXAMPLE = content['remove_word_example']
        cls.REMOVE_WORD_SUCCESS = content['remove_word_success']
        cls.REMOVE_WORD_ABSENT = content['remove_word_absent']
        cls.TRY_AGAIN = content['try_again']
        cls.BOT_RUNNING = content['bot_running']
        cls.BOT_STOPPED = content['bot_stopped']

Content.initialize()


class ReplyButton:
    add_word = Content.ADD_WORD
    remove_word = Content.REMOVE_WORD
    next_word = Content.NEXT_WORD


class UserState:
    add_word = 'ADD'
    remove_word = 'REMOVE'
    guess_word = 'GUESS'
    check_answer = 'CHECK'


class Question(StatesGroup):
    question = State()


class LangUtility:
    @classmethod
    def is_latin(cls, word: str) -> bool:
            return all('a' <= char <= 'z' or 'A' <= char <= 'Z' for char in word)

    @classmethod
    def is_cyrillic(cls, word: str) -> bool:
        return all('\u0400' <= char <= '\u04FF' for char in word)

    @classmethod
    def word_number_as_string(cls, word_number: int) -> str:
        if word_number % 100 in range(10, 20):
            words = 'слов'
        else:
            ending = word_number % 10
            match ending:
                case 1:
                    words = 'слово'
                case 2 | 3 | 4:
                    words = 'слова'
                case _:
                    words = 'слов'
        return f'{word_number} {words}'


def create_handlers(db: DBUtils, user_state: dict) -> list:
    
    @bot.message_handler(commands=['start'])
    def greeting(message):
        greeting = Content.GREETING.format(name=message.from_user.first_name)
        bot.send_message(message.chat.id, greeting)
        user_sate[message.chat.id] = UserState.guess_word
        guess_word(message)
        
    @bot.message_handler(func = lambda message: user_sate.get(message.chat.id) == UserState.guess_word)
    def guess_word(message):
        question = db.next_word(message.chat.id)
        bot.set_state(message.from_user.id, Question.question, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as stored:
            stored['en_meaning'] = question['en_meaning']
        options = [question['en_meaning']] + question['other_words']
        shuffle(options)
        buttons = [
            ReplyButton.add_word,
            ReplyButton.remove_word,
            ReplyButton.next_word
        ]
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*(options + buttons))
        bot.send_message(message.chat.id, Content.GUESS_WORD.format(word=question['ru_meaning']), reply_markup=markup)
        user_sate[message.chat.id] = UserState.check_answer

    @bot.message_handler(func = lambda message: message.text == ReplyButton.add_word)
    def add_word(message):
        bot.send_message(message.chat.id, Content.ADD_WORD_REQUEST.format(add_word_example=Content.ADD_WORD_EXAMPLE))
        user_state[message.chat.id] = UserState.add_word
        
    @bot.message_handler(func = lambda message: user_sate.get(message.chat.id) == UserState.add_word)
    def adding_word(message):
        text = message.text
        if len(text.split(' ')) == 2:
            ru_meaning = message.text.split(' ')[0].lower().strip()
            en_meaning = message.text.split(' ')[1].lower().strip()
        else:
            bot.send_message(message.chat.id, Content.TRY_AGAIN)
            add_word(message)
        is_cyrillic = LangUtility.is_cyrillic(ru_meaning)
        is_latin = LangUtility.is_latin(en_meaning)
        if  is_cyrillic and is_latin:
            word = {"ru_meaning": ru_meaning, "en_meaning": en_meaning}
            words_number = db.add_word(message.from_user.id, word)
            words_number_as_string = LangUtility.word_number_as_string(words_number)
            bot.send_message(message.chat.id, Content.ADD_WORD_SUCCESS.format(words_number=words_number_as_string))
        else:
            bot.send_message(message.chat.id, Content.TRY_AGAIN)
            add_word(message)
        user_state[message.chat.id] = UserState.guess_word
        guess_word(message)

    @bot.message_handler(func = lambda message: message.text == ReplyButton.remove_word)
    def remove_word(message):
        bot.send_message(message.chat.id, Content.REMOVE_WORD_REQUEST.format(remove_word_example=Content.REMOVE_WORD_EXAMPLE))
        user_state[message.chat.id] = UserState.remove_word
    
    @bot.message_handler(func = lambda message: user_state.get(message.chat.id) == UserState.remove_word)
    def removing_word(message):
        result = db.remove_word(message.from_user.id, message.text)
        if result:
            bot.send_message(message.chat.id, Content.REMOVE_WORD_SUCCESS)
        else:
            bot.send_message(message.chat.id, Content.REMOVE_WORD_ABSENT)
        user_state[message.chat.id] = UserState.guess_word
        guess_word(message)

    @bot.message_handler(func = lambda message: message.text == ReplyButton.next_word)
    def next_word(message):
        user_state[message.chat.id] = UserState.add_word
        guess_word(message)

    @bot.message_handler(func = lambda message: user_state.get(message.chat.id) == UserState.check_answer)
    def check_answer(message):
        answer = message.text
        correct_answer = ''
        with bot.retrieve_data(message.from_user.id, message.chat.id) as stored:
            correct_answer = stored['en_meaning']
        if answer == correct_answer:
            bot.send_message(message.chat.id, Content.CORRECT)
            user_state[message.chat.id] = UserState.guess_word
            guess_word(message)
        else:
            bot.send_message(message.chat.id, Content.NOT_CORRECT)

    return greeting, guess_word, add_word, adding_word, remove_word, removing_word, next_word, check_answer


if __name__ == "__main__":
    env_reader = EnvReader()
    state_storage = StateMemoryStorage()
    bot = TeleBot(env_reader.token, state_storage=state_storage)
    engine = sq.create_engine(env_reader.DSN)
    db = DBUtils(engine)
    handlers = []
    user_sate = dict()
    try:
        DBUtils.make_database(engine=engine, remove_tables=env_reader.remove_tables, create_db=env_reader.create_db)
        if env_reader.fill_data:
            db.fill_data(env_reader.data_file_path)
        handlers = create_handlers(db, user_sate)
        print(Content.BOT_RUNNING)
        bot.polling()
    except Exception as e:
        print(Content.BOT_STOPPED, e)
    finally:
        db.close()