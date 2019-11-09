import logging

from datetime import datetime

import math
import random
import time

from emoji import emojize
from functools import wraps
from telegram import (ReplyKeyboardMarkup, ChatAction, ParseMode, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler)

import settings
from db import db, get_or_create_user
from api_query_book import *

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING_MAIN, ADD_MY_GOAL, ADD_NAME, ADD_AUTHOR, MY_BOOK, END_BOOK_DATE, CHANGE_PAGE, SEND_FEEDBACK, ADD_NAME_CATALOG = range(9)

BOOKS_API_META = 'https://www.bgoperator.ru/bgmarket/item.shtml?itemId='

PAGE_LENGTH=5

FEEDBACK_CHAT_ID=-1001307804947

READ_BY_BOOK_ICON = emojize(":closed_book:", use_aliases=True)
FAVORITE_BOOK_ICON = emojize(":star:", use_aliases=True)
IN_PROGRESS_BOOK_ICON = emojize(":eyes:", use_aliases=True)
CAT_FACE_ICON = emojize(":cat_face:", use_aliases=True)

keyboard_main = [['Мои книги', 'Мои цели', 'Статистика'],
                    ['Добавить книгу'],
                    ['Обратная связь']]

keyboard_add_book = [['Из каталога', 'Вручную'],
                        ['Главное меню']]

keyboard_user_addition = [['В избранное', 'Прочитал'],
                            ['Главное меню']]


keyboard_statistic = [['Среднее время', 'Количество книг'],
                            ['Главное меню']]

keyboard_book_pagination = [['Предыдущие', 'Cледующие'],
                            ['Главное меню']]

keyboard_next_page = [['Cледующие'],
                        ['Главное меню']]


keyboard_my_books = [['Избранные', 'Отслеживаемые', 'Прочитанные'],
                        ['Все книги'],
                        ['Главное меню']]

keyboard_goal_variables = [['Изменить цель', 'Удалить цель', 'Посмотреть цель'],

                            ['Главное меню']]

keyboard_my_books_inline = [[
            InlineKeyboardButton('Читаю', callback_data='Читаю'),
            InlineKeyboardButton('Избранное', callback_data='Избранное'),
            InlineKeyboardButton('Слежу', callback_data='Слежу'),
            InlineKeyboardButton('Прочитал', callback_data='Прочитал')
            ]]

keyboard_del_from_favorits = [[InlineKeyboardButton('Удалить', callback_data='Удалить из избранного')]]
keyboard_del_from_progress = [[InlineKeyboardButton('Удалить', callback_data='Удалить из отслеживаемого')]]
keyboard_del_from_readby = [[InlineKeyboardButton('Удалить', callback_data='Удалить из прочитанного')]]

markup_statistic = ReplyKeyboardMarkup(keyboard_statistic, one_time_keyboard=True, resize_keyboard=True)
markup_main = ReplyKeyboardMarkup(keyboard_main, one_time_keyboard=True, resize_keyboard=True)
markup_add_book = ReplyKeyboardMarkup(keyboard_add_book, one_time_keyboard=True, resize_keyboard=True)
markup_my_books = ReplyKeyboardMarkup(keyboard_my_books, resize_keyboard=True)
markup_goal_variables = ReplyKeyboardMarkup(keyboard_goal_variables, resize_keyboard=True)
markup_book_pagination = ReplyKeyboardMarkup(keyboard_book_pagination, resize_keyboard=True)
markup_next_page = ReplyKeyboardMarkup(keyboard_next_page, resize_keyboard=True)
inline_markup = InlineKeyboardMarkup(keyboard_my_books_inline)
del_favorits_markup = InlineKeyboardMarkup(keyboard_del_from_favorits)
del_progress_markup = InlineKeyboardMarkup(keyboard_del_from_progress)
del_read_by_markup = InlineKeyboardMarkup(keyboard_del_from_readby)

def send_typing_action(func):

    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        time.sleep(random.uniform(0,2))
        return func(update, context,  *args, **kwargs)
    return command_func

@send_typing_action
def start_conversation(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    logger.info('Start messaging with user %s, open MAIN MENU', username)
    update.message.reply_text(
        'Привет {}! Я книжный бот.\n' 
        'Выбери, пожалуйста, необходимое действие c книгой.'.format(username), reply_markup=markup_main)

    return CHOOSING_MAIN

@send_typing_action
def help_conversation(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']

    logger.info('Show user %s list of commands', username)
    update.message.reply_text(
        'Привет, мой маленький любитель книг {}!\n'
        'Наверное, ты хочешь узнать что я умею?\n' 
        'Вот список доступных команд:\n'
        '/help - команда просмотра списка команд\n'
        '/start - команда вызова главного меню\n'
        '/stop - команда окончания работы с ботом'.format(username), reply_markup=ReplyKeyboardRemove())

@send_typing_action
def add_book_variables(update, context):

    user_text = update.message.text
    context.user_data['choice'] = user_text
    update.message.reply_text('Выберите вариант добавления книги', reply_markup=markup_add_book)
    user = get_or_create_user(db, update.message)
    
@send_typing_action
def add_book(update, context):
    text = update.message.text
    context.user_data['choice'] = text
    user_choice = context.user_data['choice']
    if user_choice == 'Вручную':
        update.message.reply_text('Введите название книги')
        return ADD_NAME
    elif user_choice == 'Из каталога':
        update.message.reply_text('Введите точное название книги')
        return ADD_NAME_CATALOG
    else:
        update.message.reply_text('Возвращаюсь в главное меню', reply_markup=markup_main)
        return CHOOSING_MAIN

@send_typing_action
def add_book_name_catalog(update, context):
    user = get_or_create_user(db, update.message)
    book_name_catalog = update.message.text
    book_name_catalog = book_name_catalog.strip()
    request_data = {'query': query, 'variables': {'cond': [{'attr': 'name', 'ct': 'EQ', 'val': book_name_catalog}]}}
    search_request = requests.post(URL, headers=HEADERS, json=request_data)
    response_content = json.loads(search_request.content.decode('utf-8'))
    books = response_content.get('data', {}).get('meta', {}).get('getSrcObs').get('edges', {})
    if books:
        for book in books:
            book_name = book['node']['name']
            book_author = book['node']['author']
            book_id = book['node']['id']
            book_url = BOOKS_API_META + book_id
            db.users.update_one({'_id': user['_id']}, {'$addToSet': {'books': {'name': book_name, 'author': book_author, 'url': book_url}}})
            update.message.reply_text(f'Вы добавили книгу "{book_name}" автора "{book_author}"', reply_markup=markup_main)
            return CHOOSING_MAIN
    else:
        update.message.reply_text('Нет такой книги. Попробуй еще раз.', reply_markup=markup_main)
        return CHOOSING_MAIN


@send_typing_action
def add_book_name(update, context):
    book_name = update.message.text 
    context.user_data['book_name'] = book_name
    update.message.reply_text('Введите имя автора')
    return ADD_AUTHOR

@send_typing_action
def add_book_author(update, context):
    book_author = update.message.text
    context.user_data['book_author'] = book_author
    user = get_or_create_user(db, update.message)
    db.users.update_one(
        {'_id': user['_id']},
        {'$addToSet': {'books': {'name': context.user_data["book_name"], 'author': context.user_data["book_author"]}}}
    )

    update.message.reply_text(f'Вы добавили книгу "{context.user_data["book_name"]}" автора "{context.user_data["book_author"]}"', reply_markup=markup_main)

    return CHOOSING_MAIN
    
@send_typing_action
def user_feedback(update, context):
    update.message.reply_text('Оставь свой отзыв, я буду ему рад и постараюсь стать лучше.')
    return SEND_FEEDBACK

@send_typing_action
def send_user_feedback(update, context):
    user_feedback = update.message.text
    user = get_or_create_user(db, update.message)
    username = user['username']
    first_name = user['first_name']
    last_name = user['last_name']
    context.bot.send_message(
        chat_id=FEEDBACK_CHAT_ID, text=f'*username*: {username}\n*first_name*: {first_name}\n*last_name*: {last_name}\n*feedback*: {user_feedback}', 
        parse_mode=ParseMode.MARKDOWN)
    update.message.reply_text(f'Спасибо тебе за отзыв, котан {CAT_FACE_ICON}', reply_markup=markup_main)
    return CHOOSING_MAIN

@send_typing_action
def my_book_statistic(update, context):
    user = get_or_create_user(db, update.message)
    user_id = user['user_id']

    update.message.reply_text(
        'Узнай свою статистику', reply_markup=markup_statistic)

@send_typing_action
def my_book_avg_time(update, context):
    user = get_or_create_user(db, update.message)
    user_id = user['user_id']
    text = update.message.text
    query_to_db = db.users.aggregate([
    { "$match": {"user_id": user_id}},
    { "$project": {
        "books": {"$filter": {
            "input": "$books",
            "as": "item",
            "cond": {"$eq": ['$$item.read_by', True]}
        }}
    }}
])
    books_read_user = query_to_db.next()
    read_books_user = books_read_user.get('books')
    
    if read_books_user:
        books_days_total = 0
        for books in read_books_user:
            user_start_date_str = books.get('start_date')
            user_end_date_str = books.get('end_date')
            user_start_date = datetime.strptime(user_start_date_str, '%Y-%m-%d')
            user_end_date = datetime.strptime(user_end_date_str, '%Y-%m-%d')
            user_book_delta = user_end_date - user_start_date
            user_book_delta_days = user_book_delta.days
            user_book_delta_days = abs(user_book_delta_days)
            books_days_total += user_book_delta_days
    
        lenght_read_books_user = len(read_books_user)
        avg_time_book_read = books_days_total / lenght_read_books_user
        avg_time_book_read = int(avg_time_book_read)
        
        if text == 'Среднее время':
            update.message.reply_text(
            f'Среднее время на чтение одной книги - {avg_time_book_read} дня(ей)', reply_markup=markup_main)
        else:
            update.message.reply_text(
            f'Ты прочитал {lenght_read_books_user} книг(и)', reply_markup=markup_main)
        return CHOOSING_MAIN
    
    else:
        update.message.reply_text('Кажется, что у тебя нет прочитанных книг. Возвращаюсь в главное меню.', reply_markup=markup_main)
        return CHOOSING_MAIN


@send_typing_action
def my_book_goal(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    user_text = update.message.text
    context.user_data['choice'] = user_text

    logger.info('Add books goal with username %s', username)
    update.message.reply_text(
        'Создай себе книжную цель', reply_markup=markup_goal_variables)
    

@send_typing_action
def add_my_book_goal(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    user_id = user['user_id']
    user_books_count = user['books_count']

    text = update.message.text
    context.user_data['choice'] = text
    user_choice = context.user_data['choice']
        
    if user_choice == 'Удалить цель':
        db.users.update_one({'user_id': user_id}, {'$set': {'books_count': 0}})
        update.message.reply_text('Кажется у тебя больше нет цели. Это очень грустно.', reply_markup=markup_main)
        return CHOOSING_MAIN
            
    elif user_choice == 'Посмотреть цель':
        update.message.reply_text(f'Твоя цель - {user_books_count} книг(и)', reply_markup=markup_main)
        return CHOOSING_MAIN

    else:
        update.message.reply_text('Укажи количество книг, которые ты хочешь прочитать')
        return ADD_MY_GOAL


@send_typing_action
def received_book_information(update, context):
    
    user = get_or_create_user(db, update.message)
    username = user['username']
    user_books_count = user['books_count']
    user_id = user['user_id']

    user_data = context.user_data
    user_text = update.message.text
    goal_choice = user_data['choice']
    user_data[goal_choice] = user_text
    del user_data['choice']

    logger.info('Updating books count in MONGO by user %s', username)

    try: 
        user_text = int(user_text)
        db.users.update_one({'user_id': user_id}, {'$set': {'books_count': user_text}})
        update.message.reply_text('Ты собрался прочитать {} книг, желаю удачи!'.format(user_text), reply_markup=markup_main)
    
    except ValueError:
        update.message.reply_text('Кажется ты ввел не число, попробуй еще раз', reply_markup=markup_main)
    
    return CHOOSING_MAIN


@send_typing_action
def my_books(update, context):

    user = get_or_create_user(db, update.message)

    update.message.reply_text('Выбери категорию своих книг', reply_markup=markup_my_books)

    return MY_BOOK

def query_user_book(user_id, update, context, current_page=1, **kwargs):
    
    user_filter = kwargs['user_filter_query']
    show_book_status = False
    
    if not user_filter:
        show_book_status = True
        user_books = db.users.find_one({'user_id': user_id})['books']

    else: 
        query_books = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
        "cond": kwargs['user_filter_query']}}}}])
        result_books = query_books.next()
        user_books = result_books['books']
    
    len_books = len(user_books)
    pages_count = math.ceil(len_books / PAGE_LENGTH)
    context.user_data['current_page'] = current_page
    context.user_data['list_params'] = kwargs
    context.user_data['pages_count'] = pages_count
    kwargs['len_books'] = len_books
    

    if not user_books:
        update.message.reply_text(kwargs['bot_message_query'])
    else:
        get_keyboard = kwargs['user_keyboard']
        if current_page == 1:
            user_books = user_books[0:PAGE_LENGTH]
        elif current_page == pages_count:
            user_books = user_books[(current_page-1)*PAGE_LENGTH: len_books]
        else:
            user_books = user_books[(current_page-1)*PAGE_LENGTH: current_page*PAGE_LENGTH]
        
        for books in user_books:
            books_status = []
            if show_book_status:
                if books.get("favorite"):
                    books_status.append(FAVORITE_BOOK_ICON)
                if books.get("read_by"):
                    books_status.append(READ_BY_BOOK_ICON)
                if books.get("in_progress"):
                    books_status.append(IN_PROGRESS_BOOK_ICON)

            if books.get("url"):
                update.message.reply_text(f'{books["name"]} - {books["author"]} {" ".join(books_status)}\nСсылка: {books["url"]}', reply_markup=get_keyboard)
            else:
                update.message.reply_text(f'{books["name"]} - {books["author"]} {" ".join(books_status)}', reply_markup=get_keyboard)

@send_typing_action
def change_page(update, context):

    user = get_or_create_user(db, update.message)
    user_id = user['user_id']

    user_text = update.message.text
    user_text = user_text.strip()
    list_params = context.user_data['list_params']
    pages_count = context.user_data['pages_count']


    if user_text == 'Cледующие':
        next_page = context.user_data['current_page'] + 1
        if next_page > pages_count:
            update.message.reply_text('Книг больше нет, возвращаюсь в главное меню', reply_markup=markup_main)
            return CHOOSING_MAIN
        else:
            context.user_data['current_page'] = next_page
            query_user_book(user_id, update, context, current_page=next_page, **list_params)
    elif user_text == 'Предыдущие':
        previous_page = context.user_data['current_page'] - 1
        if previous_page == 0:
            update.message.reply_text('Книг больше нет, возвращаюсь в главное меню', reply_markup=markup_main)
            return CHOOSING_MAIN
        else:
            context.user_data['current_page'] = previous_page
            query_user_book(user_id, update, context, current_page=previous_page, **list_params)
    else:
        update.message.reply_text('Возврат в главное меню', reply_markup=markup_main)
        return CHOOSING_MAIN

@send_typing_action
def my_book_information(update, context):

    user = get_or_create_user(db, update.message)
    user_id = user['user_id']
    user_text = update.message.text

    query_book_information = {
        "Избранные": {
            "bot_message_query": "У вас нет избранных книг",
            "user_filter_query": {"$eq": ['$$item.favorite', True]},
            "user_keyboard": del_favorits_markup,
        },
        "Отслеживаемые": {
            "bot_message_query": "У вас нет отслеживаемых книг",
            "user_filter_query": {"$eq": ['$$item.in_progress', True]},
            "user_keyboard": del_progress_markup,
        },
        "Прочитанные": {
            
            "bot_message_query": "У вас нет прочитанных книг",
            "user_filter_query": {"$eq": ['$$item.read_by', True]},
            "user_keyboard": del_read_by_markup,
        },

        "Все книги": {
            "bot_message_query": "У вас нет добавленных книг",
            "user_filter_query": "",
            "user_keyboard": inline_markup,
        }
    }
    
    if user_text in query_book_information:
        books_query_result = query_user_book(user_id, update, context, **query_book_information[user_text])
        update.message.reply_text('Выберите действие', reply_markup=markup_book_pagination)
        return CHANGE_PAGE
    
    else: 
        update.message.reply_text('Возврат в главное меню', reply_markup=markup_main)
        return CHOOSING_MAIN
    

def delete_books_data(user_id, user_book_name_strip, query, **kwargs):

    db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$unset': kwargs['user_filter']})
    query.edit_message_text(text=kwargs['bot_message'])

def query_books_data(user_id, user_book_name_strip, query, **kwargs):

    db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': kwargs['user_filter']})
    query.edit_message_text(text=kwargs['bot_message'])

@send_typing_action
def books_button(update, context):

    query = update.callback_query
    query_message = query.message
    query_data = query.data
    query_text = query_message.text
    query_text_split = query_text.split('-')
    user_book_name = query_text_split[0]
    user_book_author = query_text_split[-1]
    user_book_name_strip = user_book_name.strip()
    user_book_author_strip = user_book_author.strip()
    
    user_id = query_message.chat_id
    context.user_data['query_data'] = query_data

    date_now = datetime.now()
    now_date = date_now.strftime('%Y-%m-%d')

    user_delete_options = {
        "Удалить из избранного": {
            "bot_message": "Книга удалена из избранного",
            "user_filter": {'books.$.favorite': True},
            },
        "Удалить из отслеживаемого": {
            "bot_message": "Книга удалена из отслеживаемого",
            "user_filter": {'books.$.in_progress': True},
            },
        "Удалить из прочитанного": {
            "bot_message": "Книга удалена из прочитанного",
            "user_filter": {'books.$.end_date': now_date, 'books.$.read_by': True},
        } 
    }

    user_query_options = {
        "Слежу": {
            "bot_message": "Книга добавлена в отслеживаемые",
            "user_filter": {'books.$.in_progress': True},
        },
        "Избранное": {
            "bot_message": "Книга добавлена в избранное",
            "user_filter": {'books.$.favorite': True},
        },
        "Читаю": {
            "bot_message": "Ты начал читать книгу",
            "user_filter": {'books.$.start_date': now_date},
        }
    }

    if query_data in user_query_options:
        query_books_data(user_id, user_book_name_strip, query, **user_query_options[query_data])
    
    elif query_data in user_delete_options:
        delete_books_data(user_id, user_book_name_strip, query, **user_delete_options[query_data])

    elif query_data == 'Прочитал':
        user_book_read_by_query = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
        "cond": {"$eq": ['$$item.name', user_book_name_strip]}}}}}])

        user_book_read_by = user_book_read_by_query.next()
        book_read_by = user_book_read_by['books']
        readed_book = book_read_by[0]

        start_date_book_str = readed_book.get('start_date')
        
        if start_date_book_str is not None:
            start_date_book = datetime.strptime(start_date_book_str, '%Y-%m-%d')
            book_days = date_now - start_date_book
            book_days = book_days.days
            db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.end_date': now_date, 'books.$.book_days': book_days, 'books.$.read_by': True}})
            query.edit_message_text(text='Книга добавлена в прочитанные')
        else:
            db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.end_date': now_date, 
            'books.$.start_date': now_date, 'books.$.book_days': 1, 'books.$.read_by': True}})
            query.edit_message_text(text='Книга добавлена в прочитанные')        

@send_typing_action
def stop_conversation(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    logger.info('User %s canceled the conversation', username)
    update.message.reply_text('Пока, {}! Надеюсь, что мы скоро увидимся вновь'.format(username),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

def main():

    readbooksbot = Updater(settings.API_KEY, request_kwargs=settings.PROXY, use_context=True)

    dp = readbooksbot.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_conversation)],

        states={
            CHOOSING_MAIN: [

                            MessageHandler(Filters.regex('^(Добавить книгу)$'), add_book_variables),

                            MessageHandler(Filters.regex('^(Мои цели)$'), my_book_goal),

                            MessageHandler(Filters.regex('^(Статистика)$'), my_book_statistic),

                            MessageHandler(Filters.regex('^(Среднее время)$'), my_book_avg_time),

                            MessageHandler(Filters.regex('^(Количество книг)$'), my_book_avg_time),

                            MessageHandler(Filters.regex('^(Изменить цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Удалить цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Посмотреть цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Из каталога)$'), add_book),

                            MessageHandler(Filters.regex('^(Вручную)$'), add_book),

                            MessageHandler(Filters.regex('^(Главное меню)$'), start_conversation),

                            MessageHandler(Filters.regex('^(Мои книги)$'), my_books),

                            MessageHandler(Filters.regex('^(Обратная связь)$'), user_feedback),

                            ],

            CHANGE_PAGE: [MessageHandler(Filters.text, change_page)],
            ADD_AUTHOR: [MessageHandler(Filters.text, add_book_author)],
            ADD_NAME_CATALOG: [MessageHandler(Filters.text, add_book_name_catalog)],
            ADD_NAME: [MessageHandler(Filters.text, add_book_name)],
            MY_BOOK: [MessageHandler(Filters.text, my_book_information)],
            SEND_FEEDBACK: [MessageHandler(Filters.text, send_user_feedback)],
            ADD_MY_GOAL: [MessageHandler(Filters.text, received_book_information)
                           ],
        
        },

        fallbacks=[CommandHandler('stop', stop_conversation)]
    )
    
    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(books_button))
    dp.add_handler(CommandHandler('help', help_conversation))

    readbooksbot.start_polling()

    readbooksbot.idle()

if __name__ == '__main__':
    main()
