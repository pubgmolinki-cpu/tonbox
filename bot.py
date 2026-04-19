import os
import logging
import asyncio
import psycopg2
import json
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
# Вписываем ключ БЕЗ использования os.environ, чтобы точно сработало
GEMINI_KEY = "AIzaSyBTfuFyYRnZBjm9WLJUpQuqOZ7fbNk-70o"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

# Явная настройка ключа
genai.configure(api_key=GEMINI_KEY)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Проверка модели при запуске
model = genai.GenerativeModel('gemini-1.5-flash')
