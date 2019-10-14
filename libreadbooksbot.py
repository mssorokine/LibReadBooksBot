import logging

from datetime import datetime

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler)

import settings
from db import db, get_or_create_user

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING_MAIN, TYPING_REPLY, ADD_NAME, ADD_AUTHOR, MY_BOOK, END_BOOK_DATE = range(6)

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
        'Напиши сколько книг ты сможешь осилить, я буду следить за твои прогрессом\n')
    
    return TYPING_REPLY

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
    
    user_text = int(user_text)

    db.users.update_one(
        {'user_id': user_id},
        {'$set': {'books_count': user_text}}
    )
        
    if user_text <= 30:
        update.message.reply_text('Ты собрался прочитать {} книг, для начала неплохо, желаю удачи!'.format(user_text))
    elif user_text > 30:
        update.message.reply_text('Ты собрался прочитать {} книг, ну ты просто книжный монстр!'.format(user_text))

def my_books(update, context):

    user = get_or_create_user(db, update.message)

    update.message.reply_text('Выбери категорию своих книг', reply_markup=markup_my_books)

    return MY_BOOK

def my_book_information(update, context):

    user = get_or_create_user(db, update.message)
    user_id = user['user_id']
    user_text = update.message.text

    if user_text == 'Все книги':

        user_books = db.users.find_one({'user_id': user_id})['books']
        
        if user_books == []:
            update.message.reply_text('У вас нет добавленных книг')
            
        else:
            for books in user_books:
                update.message.reply_text(f'{books["name"]} - {books["author"]}', reply_markup=inline_markup)
    
    elif user_text == 'Избранные':
        
        query_favorites = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
        "cond": {"$eq": ['$$item.favorite', True]}}}}}])
        result_favorites = query_favorites.next()
        user_books = result_favorites['books']

        if user_books == []:
            update.message.reply_text('У вас нет избранных книг')
        else:
            for books in user_books:
                update.message.reply_text(f'{books["name"]} - {books["author"]}', reply_markup=del_favorits_markup)


    elif user_text == 'Отслеживаемые':

        query_in_progress = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
        "cond": {"$eq": ['$$item.in_progress', True]}}}}}])
        result_in_progress = query_in_progress.next()
        user_books = result_in_progress['books']

        if user_books == []:
            update.message.reply_text('У вас нет отслеживаемых книг')
        else:
            for books in user_books:
                update.message.reply_text(f'{books["name"]} - {books["author"]}', reply_markup=del_progress_markup)         

    elif user_text == 'Прочитанные':

        query_read_by = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
        "cond": {"$eq": ['$$item.read_by', True]}}}}}])
        result_read_by = query_read_by.next()
        user_books = result_read_by['books']

        if user_books == []:
            update.message.reply_text('У вас нет прочитанных книг')
        else:
            for books in user_books:
                update.message.reply_text(f'{books["name"]} - {books["author"]}', reply_markup=del_read_by_markup)

    else:
        
        update.message.reply_text('Возврат в главное меню', reply_markup=markup_main)
        
        return CHOOSING_MAIN
    

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

    if query_data == 'Слежу':

        db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.in_progress': True}})
        query.edit_message_text(text='Книга "{}" добавлена в отслеживаемые.'.format(user_book_name_strip))

    elif query_data == 'Избранное':

        db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.favorite': True}})
        query.edit_message_text(text='Книга "{}" добавлена в избранное.'.format(user_book_name_strip))

    elif query_data == 'Читаю':

        db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.start_date': now_date}})
        query.edit_message_text(text='Ты начал читать книгу "{}".'.format(user_book_name_strip))

    elif query_data == 'Прочитал':

        user_book_read_by_query = db.users.aggregate([{ "$match": {"user_id": user_id}}, { "$project": { "books": { "$filter": { "input": "$books", "as": "item", 
        "cond": {"$eq": ['$$item.name', user_book_name_strip]}}}}}])

        user_book_read_by = user_book_read_by_query.next()
        book_read_by = user_book_read_by['books']
        

        for readed_book in book_read_by:

            start_date_book_str = readed_book.get('start_date')
            start_date_book = datetime.strptime(start_date_book_str, '%Y-%m-%d')
            book_days = date_now - start_date_book
            book_days = book_days.days


            if 'start_date' in readed_book:
                db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.end_date': now_date, 
                'books.$.start_date': now_date, 'books.$.book_days': book_days, 'books.$.read_by': True}})
                query.edit_message_text(text='Книга "{}" добавлена в прочитанные.'.format(user_book_name_strip))
            else:
                db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$set': {'books.$.end_date': now_date, 
                'books.$.start_date': now_date, 'books.$.book_days': 1, 'books.$.read_by': True}})
                query.edit_message_text(text='Книга "{}" добавлена в прочитанные.'.format(user_book_name_strip))

    
    elif query_data == 'Удалить из избранного':
        
        db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$unset': {'books.$.favorite': True}})
        query.edit_message_text(text='Книга "{}" удалена из избранного.'.format(user_book_name_strip))

    elif query_data == 'Удалить из отслеживаемого':

        db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$unset': {'books.$.in_progress': True}})
        query.edit_message_text(text='Книга "{}" удалена из отслеживаемых.'.format(user_book_name_strip))

    elif query_data == 'Удалить из прочитанного':

        db.users.update({'user_id' : user_id , 'books.name': user_book_name_strip} , {'$unset': {'books.$.end_date': now_date, 
        'books.$.read_by': True}})
        query.edit_message_text(text='Книга "{}" удалена из прочитанного.'.format(user_book_name_strip))


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

                            MessageHandler(Filters.regex('^(Главное меню)$'), start_conversation),

                            MessageHandler(Filters.regex('^(Мои книги)$'), my_books)

                            ],

            ADD_AUTHOR: [MessageHandler(Filters.text, add_book_author)],
            ADD_NAME: [MessageHandler(Filters.text, add_book_name)],
            MY_BOOK: [MessageHandler(Filters.text, my_book_information)],
            TYPING_REPLY: [MessageHandler(Filters.text, received_book_information)
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
