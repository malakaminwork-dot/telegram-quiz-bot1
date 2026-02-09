import os
from dotenv import load_dotenv

load_dotenv()

# توكن البوت
BOT_TOKEN = os.getenv('BOT_TOKEN', '8572415537:AAFM-WBWBa0kSG3SxFXWfTa07sBvvdGNjdM')

# معرف المطور (اختياري)
DEVELOPER_ID = os.getenv('DEVELOPER_ID', '')

# أنواع الأسئلة
QUESTION_TYPES = {
    'true_false': 'صح أو خطأ',
    'multiple_choice': 'اختيار من متعدد',
    'short_answer': 'إجابة قصيرة'
}
