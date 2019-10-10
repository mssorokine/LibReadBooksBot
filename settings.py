import os, sys

PROXY = {
    'proxy_url': 'socks5://t2.learn.python.ru:1080',
    'urllib3_proxy_kwargs': {
        'username': 'learn', 
        'password': 'python'
    }
}

MONGO_LINK = "mongodb+srv://readbooksbot:RK1AezPsXwuCEa2x@booksbotcluster-y09mz.mongodb.net/books"

MONGO_DB = "books"

API_KEY = os.environ["BOT_TOKEN"]
