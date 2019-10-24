import logging

from datetime import datetime

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler)

import settings
from db import db, get_or_create_user

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING_MAIN, ADD_MY_GOAL, ADD_NAME, ADD_AUTHOR, MY_BOOK, END_BOOK_DATE = range(6)

keyboard_main = [['Мои книги', 'Мои цели', 'Статистика'],
                    ['Добавить книгу']]

keyboard_add_book = [['Из каталога', 'Вручную'],
                        ['Главное меню']]

keyboard_user_addition = [['В избранное', 'Прочитал'],
                            ['Главное меню']]

keyboard_search_book = [['По названию', 'По автору'],
                            ['Главное меню']]

keyboard_my_books = [['Избранные', 'Отслеживаемые', 'Прочитанные'],
                        ['Все книги'],
                        ['Главное меню']]

keyboard_goal_variables = [['Создать цель', 'Изменить цель'], 

                            ['Удалить цель', 'Посмотреть цель'],

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

markup_main = ReplyKeyboardMarkup(keyboard_main, one_time_keyboard=True, resize_keyboard=True)
markup_add_book = ReplyKeyboardMarkup(keyboard_add_book, one_time_keyboard=True, resize_keyboard=True)
markup_my_books = ReplyKeyboardMarkup(keyboard_my_books, resize_keyboard=True)
markup_goal_variables = ReplyKeyboardMarkup(keyboard_goal_variables, resize_keyboard=True)
inline_markup = InlineKeyboardMarkup(keyboard_my_books_inline)
del_favorits_markup = InlineKeyboardMarkup(keyboard_del_from_favorits)
del_progress_markup = InlineKeyboardMarkup(keyboard_del_from_progress)
del_read_by_markup = InlineKeyboardMarkup(keyboard_del_from_readby)

def start_conversation(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    logger.info('Start messaging with user %s, open MAIN MENU', username)
    update.message.reply_text(
        'Привет {}! Я книжный бот.\n' 
        'Выбери, пожалуйста, необходимое действие c книгой.'.format(username), reply_markup=markup_main)

    return CHOOSING_MAIN

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

def add_book(update, context):
    update.message.reply_text('Введите название книги')
    user = get_or_create_user(db, update.message)
    return ADD_NAME

def add_book_name(update, context):
    book_name = update.message.text 
    context.user_data['book_name'] = book_name
    update.message.reply_text('Введите имя автора')
    return ADD_AUTHOR

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
    
def my_book_goal(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    user_text = update.message.text
    context.user_data['choice'] = user_text

    logger.info('Add books goal with username %s', username)
    update.message.reply_text(
        'Создай себе книжную цель', reply_markup=markup_goal_variables)
    

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


def my_books(update, context):

    user = get_or_create_user(db, update.message)

    update.message.reply_text('Выбери категорию своих книг', reply_markup=markup_my_books)

    return MY_BOOK

def query_user_book(user_id, update, **kwargs):
    query_books = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
    "cond": kwargs['user_filter_query']}}}}])
    result_books = query_books.next()
    user_books = result_books['books']
    if user_books == []:
        update.message.reply_text(kwargs['bot_message_query'])
    else:
        get_keyboard = kwargs['user_keyboard']
        for books in user_books:
            update.message.reply_text(f'{books["name"]} - {books["author"]}', reply_markup=get_keyboard)

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
        }
    }
    
    if user_text == 'Все книги':

        user_books = db.users.find_one({'user_id': user_id})['books']
        
        if user_books == []:
            update.message.reply_text('У вас нет добавленных книг')
            
        else:
            for books in user_books:
                update.message.reply_text(f'{books["name"]} - {books["author"]}', reply_markup=inline_markup)
    
    elif user_text in query_book_information:
        query_user_book(user_id, update, **query_book_information[user_text])

    else:
        
        update.message.reply_text('Возврат в главное меню', reply_markup=markup_main)
        
        return CHOOSING_MAIN
    

def delete_books_data(user_id, user_book_name_strip, query, **kwargs):

    db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$unset': kwargs['user_filter']})
    query.edit_message_text(text=kwargs['bot_message'])

def query_books_data(user_id, user_book_name_strip, query, **kwargs):

    db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': kwargs['user_filter']})
    query.edit_message_text(text=kwargs['bot_message'])

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

                            MessageHandler(Filters.regex('^(Добавить книгу)$'), add_book),

                            MessageHandler(Filters.regex('^(Мои цели)$'), my_book_goal),

                            MessageHandler(Filters.regex('^(Создать цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Изменить цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Удалить цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Посмотреть цель)$'), add_my_book_goal),

                            MessageHandler(Filters.regex('^(Главное меню)$'), start_conversation),

                            MessageHandler(Filters.regex('^(Мои книги)$'), my_books)

                            ],

            ADD_AUTHOR: [MessageHandler(Filters.text, add_book_author)],
            ADD_NAME: [MessageHandler(Filters.text, add_book_name)],
            MY_BOOK: [MessageHandler(Filters.text, my_book_information)],
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
