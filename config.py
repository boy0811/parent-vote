import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey123'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///voting_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
