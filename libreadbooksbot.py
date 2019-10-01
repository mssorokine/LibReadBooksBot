import logging

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)

import settings
from db import db, get_or_create_user

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING_MAIN, TYPING_REPLY = range(2)

keyboard_main = [['Избранное', 'Прочитал', 'Слежу'],
                    ['Добавить книгу', 'Моя цель']]

keyboard_add_book = [['Из каталога', 'Вручную'],
                        ['Главное меню']]

keyboard_user_addition = [['В избранное', 'Прочитал'],
                            ['Главное меню']]

keyboard_search_book = [['По названию', 'По автору'],
                            ['Главное меню']]

markup_main = ReplyKeyboardMarkup(keyboard_main, one_time_keyboard=True, resize_keyboard=True)
markup_add_book = ReplyKeyboardMarkup(keyboard_add_book, one_time_keyboard=True, resize_keyboard=True)
markup_user_addition = ReplyKeyboardMarkup(keyboard_user_addition, one_time_keyboard=True, resize_keyboard=True)
markup_search_book = ReplyKeyboardMarkup(keyboard_search_book, one_time_keyboard=True, resize_keyboard=True)

def start_conversation(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    logger.info('Start messaging with user %s, open MAIN MENU', username)
    update.message.reply_text(
        'Привет {}! Я книжный бот.\n' 
        'Мне очень нравится когда люди много читают.\n'
        'Выбери, пожалуйста, необходимое действие.'.format(username), reply_markup=markup_main)
    
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
    
    user = get_or_create_user(db, update.message)
    username = user['username']

    logger.info('Open ADD BOOK MENU with user %s', username)
    update.message.reply_text(
        'Специально для читающих запоем (да-да, есть такая фраза) мы придумали варианты поиска книги, сделай свой выбор', 
        reply_markup=markup_add_book)
    
def my_book_goal(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    user_text = update.message.text
    context.user_data['choice'] = user_text

    logger.info('Add books goal with username %s', username)
    update.message.reply_text(
        'Кажется ты планируешь прочитать больше чем одну книгу. Уверен что справишься?\n'
        'Если да, то напиши сколько книг ты сможешь осилить, я буду следить за твои прогрессом\n')
    
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
        {'$set': {"books_count": user_text}}
    )
        
    if user_text <= 30:
        update.message.reply_text('Ты собрался прочитать {} книг, для начала неплохо, желаю удачи!'.format(user_text))
    elif user_text > 30:
        update.message.reply_text('Ты собрался прочитать {} книг, ну ты просто книжный монстр!'.format(user_text))

def book_from_catalog(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']

    logger.info('Сhoosing search options FOR CATALOG books with username %s', username)
    update.message.reply_text(
        'Кажется ты заядлый книголюб, как будем искать книгу?', reply_markup=markup_search_book)

def book_user_addition(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    logger.info('Add book NOT FROM CATALOG for username %s', username)
    update.message.reply_text(
        'Дружище, введи название книги в формате "Название - автор" и выбери действие', 
        reply_markup=markup_user_addition)

def echo(update, context):

    update.message.reply_text(update.message.text)

def stop_conversation(update, context):

    user = get_or_create_user(db, update.message)
    username = user['username']
    
    logger.info('User %s canceled the conversation', username)
    update.message.reply_text('Пока, {}! Надеюсь, что мы скоро увидимся вновь. Душевное общение получилось'.format(username),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

def main():

    readbooksbot = Updater(settings.API_KEY, use_context=True)

    dp = readbooksbot.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_conversation)],

        states={
            CHOOSING_MAIN: [MessageHandler(Filters.regex('^(Избранное|Прочитал|Слежу)$'),
                                      echo),

                            MessageHandler(Filters.regex('^(Добавить книгу)$'), add_book),

                            MessageHandler(Filters.regex('^(Моя цель)$'), my_book_goal),

                            MessageHandler(Filters.regex('^(Вручную)$'), book_user_addition),
                            
                            MessageHandler(Filters.regex('^(Из каталога)$'), book_from_catalog),

                            MessageHandler(Filters.regex('^(Главное меню)$'), start_conversation)

                            ],
            TYPING_REPLY: [MessageHandler(Filters.text, received_book_information),
                           ],
        
        },

        fallbacks=[CommandHandler('stop', stop_conversation)]
    )
    
    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('help', help_conversation))

    readbooksbot.start_polling()

    readbooksbot.idle()

if __name__ == '__main__':
    main()
