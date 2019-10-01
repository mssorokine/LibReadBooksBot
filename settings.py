import os

PROXY = {
    'proxy_url': 'socks5://t3.learn.python.ru:1080',
    'urllib3_proxy_kwargs': {
        'username': 'learn', 
        'password': 'python'
    }
}

MONGO_LINK = "mongodb+srv://readbooksbot:rnG4QQU4GZ7gvTGT@booksbotcluster-y09mz.mongodb.net/books"

MONGO_DB = "books"

API_KEY = os.environ["BOT_TOKEN"]
