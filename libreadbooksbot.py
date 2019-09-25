import logging

from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import settings

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    filename='bot.log'
)

logger = logging.getLogger(__name__)

def start_dialog(bot, update, user_data):

    user_firstname = update.effective_user["first_name"]
    user_username = update.effective_user["username"]
    user_lastname = update.effective_user["last_name"]

    if user_username == None:
        update.message.reply_text("Привет, {} {}."
        " Мне очень нравится, когда люди много читают." 
        " Выбери, пожалуйста, необходимое действие.".format(user_firstname, user_lastname))
    else:
        update.message.reply_text("Привет, {}."
        " Мне очень нравится, когда люди много читают." 
        " Выбери, пожалуйста, необходимое действие.".format(user_username))

def echo(bot, update, user_data):
    
    update.message.reply_text(update.message.text)

def error(bot, update):

    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():

    readbooksbot = Updater(settings.API_KEY)

    dp = readbooksbot.dispatcher
    dp.add_handler(CommandHandler("start", start_dialog, pass_user_data=True))
    dp.add_handler(MessageHandler(Filters.text, echo, pass_user_data=True))

    readbooksbot.start_polling()

    readbooksbot.idle()

if __name__ == '__main__':
    main()
