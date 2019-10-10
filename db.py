from pymongo import MongoClient
import settings

db = MongoClient(settings.MONGO_LINK)[settings.MONGO_DB]

def get_or_create_user(db, message):
    user = db.users.find_one({"user_id": message.from_user.id})
    if not user:
        user = {
            "user_id": message.from_user.id,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "username": message.from_user.username,
            "books_count": 0,
            "chat_id": message.chat_id,
            "books": []
        }
        db.users.insert_one(user)
    return user
