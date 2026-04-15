# MongoDB integration sample for your Flask app
from pymongo import MongoClient
import os

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB = os.environ.get('MONGO_DB', 'vuln_ecommerce')

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Example usage: insert a user
def insert_user(user_data):
    return db.users.insert_one(user_data)

# Example usage: find a user by email
def find_user_by_email(email):
    return db.users.find_one({'email': email})

# Add more helper functions as needed
