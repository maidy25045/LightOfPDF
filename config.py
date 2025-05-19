import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'devkey')
    MONGO_URI = os.getenv('MONGO_URI')
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
