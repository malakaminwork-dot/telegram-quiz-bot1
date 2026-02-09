import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from config import BOT_TOKEN, QUESTION_TYPES
from database import Database
import json

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
db = Database()

# حالة المستخدمين
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت وتحديد نوع المستخدم"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("👨‍🏫 معلم", callback_data='role_teacher')],
        [InlineKeyboardButton("👨‍🎓 طالب", callback_data='role_student')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"مرحباً {user.first_name}! 👋\n"
        "يرجى اختيار دورك:",
        reply_markup=reply_markup
    )

async def handle_role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار الدور"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    role = query.data.split('_')[1]
    
    if role == 'teacher':
        db.add_teacher(user_id, query.from_user.username, query.from_user.full_name)
        keyboard = [
            [InlineKeyboardButton("➕ إضافة سؤال", callback_data='add_question')],
            [InlineKeyboardButton("📋 عرض الأسئلة", callback_data='view_questions')],
            [InlineKeyboardButton("📊 إحصائيات", callback_data='teacher_stats')]
        ]
        text = "مرحباً أيها المعلم! 👨‍🏫\nماذا تريد أن تفعل؟"
    
    else:  # طالب
        db.add_student(user_id, query.from_user.username, query.from_user.full_name)
        keyboard = [
            [InlineKeyboardButton("📝 بدء الاختبار", callback_data='start_quiz')],
            [InlineKeyboardButton("📊 نتائجي", callback_data='my_results')]
        ]
        text = "مرحباً أيها الطالب! 👨‍🎓\nماذا تريد أن تفعل؟"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def add_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إضافة سؤال جديد"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("صح أو خطأ", callback_data='type_true_false')],
        [InlineKeyboardButton("اختيار من متعدد", callback_data='type_multiple_choice')],
        [InlineKeyboardButton("رجوع", callback_data='teacher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="اختر نوع السؤال:",
        reply_markup=reply_markup
    )

async def handle_question_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نوع السؤال"""
    query = update.callback_query
    await query.answer()
    
    question_type = query.data.split('_')[1]
    user_id = query.from_user.id
    
    # حفظ حالة المستخدم
    user_states[user_id] = {
        'action': 'adding_question',
        'type': question_type,
        'step': 'waiting_for_question'
    }
    
    await query.edit_message_text(
        text=f"تم اختيار: {QUESTION_TYPES.get(question_type, question_type)}\n"
             "الآن أرسل السؤال كصورة أو كرسالة نصية:"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور (للأسئلة)"""
    user_id = update.effective_user.id
    
    if user_id in user_states and user_states[user_id]['action'] == 'adding_question':
        # حفظ الصورة
        photo_file = await update.message.photo[-1].get_file()
        
        # إنشاء مجلد للصور إذا لم يكن موجوداً
        os.makedirs('questions', exist_ok=True)
        
        # حفظ الصورة
        photo_path = f"questions/{user_id}_{update.message.message_id}.jpg"
        await photo_file.download_to_drive(photo_path)
        
        # حفظ المسار في حالة المستخدم
        user_states[user_id]['photo_path'] = photo_path
        user_states[user_id]['step'] = 'waiting_for_answer'
        
        # طلب الإجابة بناءً على نوع السؤال
        question_type = user_states[user_id]['type']
        
        if question_type == 'true_false':
            keyboard = [
                [InlineKeyboardButton("صح", callback_data='answer_true'),
                 InlineKeyboardButton("خطأ", callback_data='answer_false')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "تم استلام الصورة!\n"
                "الآن اختر الإجابة الصحيحة:",
                reply_markup=reply_markup
            )
        
        elif question_type == 'multiple_choice':
            await update.message.reply_text(
                "تم استلام الصورة!\n"
                "الآن أرسل الخيارات في رسالة واحدة كل خيار في سطر:\n"
                "مثال:\n"
                "أ) الخيار الأول\n"
                "ب) الخيار الثاني\n"
                "ج) الخيار الثالث\n"
                "د) الخيار الرابع\n\n"
                "ثم أرسل الحرف الصحيح (مثل: أ)"
            )
            user_states[user_id]['step'] = 'waiting_for_options'

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['action'] == 'adding_question':
            if state['step'] == 'waiting_for_question':
                # حفظ السؤال النصي
                user_states[user_id]['question_text'] = text
                user_states[user_id]['step'] = 'waiting_for_answer'
                
                # طلب الإجابة بناءً على نوع السؤال
                question_type = state['type']
                
                if question_type == 'true_false':
                    keyboard = [
                        [InlineKeyboardButton("صح", callback_data='answer_true'),
                         InlineKeyboardButton("خطأ", callback_data='answer_false')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(
                        "تم حفظ السؤال!\n"
                        "الآن اختر الإجابة الصحيحة:",
                        reply_markup=reply_markup
                    )
                
                elif question_type == 'multiple_choice':
                    await update.message.reply_text(
                        "تم حفظ السؤال!\n"
                        "الآن أرسل الخيارات في رسالة واحدة كل خيار في سطر:\n"
                        "مثال:\n"
                        "أ) الخيار الأول\n"
                        "ب) الخيار الثاني\n"
                        "ج) الخيار الثالث\n"
                        "د) الخيار الرابع\n\n"
                        "ثم أرسل الحرف الصحيح (مثل: أ)"
                    )
                    user_states[user_id]['step'] = 'waiting_for_options'
            
            elif state['step'] == 'waiting_for_options':
                # حفظ الخيارات
                if 'options' not in user_states[user_id]:
                    user_states[user_id]['options'] = text
                    user_states[user_id]['step'] = 'waiting_for_correct_option'
                    await update.message.reply_text(
                        "تم حفظ الخيارات!\n"
                        "الآن أرسل الحرف الصحيح (مثل: أ):"
                    )
                else:
                    # حفظ الإجابة الصحيحة
                    user_states[user_id]['correct_answer'] = text.strip().lower()
                    
                    # حفظ السؤال في قاعدة البيانات
                    question_data = {
                        'type': state['type'],
                        'question': state.get('question_text', ''),
                        'photo': state.get('photo_path', ''),
                        'options': state.get('options', ''),
                        'correct_answer': state['correct_answer'],
                        'teacher_name': update.effective_user.full_name
                    }
                    
                    question_id = db.add_question(user_id, question_data)
                    
                    # تنظيف حالة المستخدم
                    del user_states[user_id]
                    
                    await update.message.reply_text(
                        f"✅ تم إضافة السؤال بنجاح!\n"
                        f"رقم السؤال: {question_id}\n"
                        f"يمكنك العودة للقائمة الرئيسية بـ /start"
                    )

async def handle_answer_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار الإجابة (صح/خطأ)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['action'] == 'adding_question' and state['step'] == 'waiting_for_answer':
            # حفظ الإجابة
            correct_answer = 'صح' if query.data == 'answer_true' else 'خطأ'
            user_states[user_id]['correct_answer'] = correct_answer
            
            # حفظ السؤال في قاعدة البيانات
            question_data = {
                'type': state['type'],
                'question': state.get('question_text', ''),
                'photo': state.get('photo_path', ''),
                'correct_answer': correct_answer,
                'teacher_name': query.from_user.full_name
            }
            
            question_id = db.add_question(user_id, question_data)
            
            # تنظيف حالة المستخدم
            del user_states[user_id]
            
            await query.edit_message_text(
                f"✅ تم إضافة السؤال بنجاح!\n"
                f"رقم السؤال: {question_id}\n"
                f"الإجابة الصحيحة: {correct_answer}"
            )

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء الاختبار للطالب"""
    query = update.callback_query
    await query.answer()
    
    # جلب جميع الأسئلة
    all_questions = list(db.get_all_questions().values())
    
    if not all_questions:
        await query.edit_message_text("⚠️ لا توجد أسئلة متاحة حالياً.")
        return
    
    # اختيار 5 أسئلة عشوائية
    import random
    quiz_questions = random.sample(all_questions, min(5, len(all_questions)))
    
    # حفظ الاختبار في حالة المستخدم
    user_id = query.from_user.id
    user_states[user_id] = {
        'action': 'taking_quiz',
        'questions': quiz_questions,
        'current_question': 0,
        'answers': [],
        'score': 0
    }
    
    # عرض السؤال الأول
    await show_next_question(update, context)

async def show_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض السؤال التالي"""
    query = update.callback_query
    user_id = query.from_user.id if query else update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['action'] != 'taking_quiz':
        return
    
    state = user_states[user_id]
    current_idx = state['current_question']
    
    if current_idx >= len(state['questions']):
        # انتهاء الاختبار
        await finish_quiz(update, context, user_id)
        return
    
    question = state['questions'][current_idx]
    
    # بناء نص السؤال
    text = f"السؤال {current_idx + 1} من {len(state['questions'])}\n\n"
    
    if question['question']:
        text += f"{question['question']}\n\n"
    
    # بناء الخيارات حسب نوع السؤال
    if question['type'] == 'true_false':
        keyboard = [
            [InlineKeyboardButton("صح", callback_data='ans_true'),
             InlineKeyboardButton("خطأ", callback_data='ans_false')]
        ]
        text += "اختر الإجابة الصحيحة:"
    
    elif question['type'] == 'multiple_choice' and question.get('options'):
        options = question['options'].split('\n')
        keyboard = []
        for option in options[:4]:  # الحد الأقصى 4 خيارات
            if option.strip():
                option_letter = option.split(')')[0] if ')' in option else option[0]
                keyboard.append([InlineKeyboardButton(option.strip(), callback_data=f'ans_{option_letter}')])
        
        text += "اختر الإجابة الصحيحة:"
    
    else:
        text += "أرسل إجابتك:"
        user_states[user_id]['waiting_for_text'] = True
    
    reply_markup = InlineKeyboardMarkup(keyboard) if 'keyboard' in locals() else None
    
    if query:
        if question.get('photo'):
            # إذا كان هناك صورة، أرسلها أولاً
            try:
                with open(question['photo'], 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=text,
                        reply_markup=reply_markup
                    )
                await query.delete_message()
            except:
                await query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        if question.get('photo'):
            try:
                with open(question['photo'], 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo,
                        caption=text,
                        reply_markup=reply_markup
                    )
            except:
                await update.message.reply_text(text=text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=text, reply_markup=reply_markup)

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إجابة الطالب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in user_states or user_states[user_id]['action'] != 'taking_quiz':
        return
    
    state = user_states[user_id]
    current_idx = state['current_question']
    question = state['questions'][current_idx]
    
    # استخراج الإجابة
    if query.data.startswith('ans_'):
        user_answer = query.data[4:]  # إزالة 'ans_'
    
    # التحقق من الإجابة
    correct_answer = question.get('correct_answer', '').lower()
    is_correct = False
    
    if question['type'] == 'true_false':
        correct_map = {'صح': 'true', 'خطأ': 'false'}
        user_map = {'صح': 'true', 'خطأ': 'false'}
        is_correct = user_map.get(user_answer, '') == correct_map.get(correct_answer, '')
    elif question['type'] == 'multiple_choice':
        is_correct = user_answer.lower() == correct_answer.lower()
    
    # حفظ النتيجة
    state['answers'].append({
        'question_id': question.get('id'),
        'user_answer': user_answer,
        'correct_answer': correct_answer,
        'is_correct': is_correct
    })
    
    if is_correct:
        state['score'] += 1
    
    # الانتقال للسؤال التالي
    state['current_question'] += 1
    
    # إعلام المستخدم بالإجابة
    feedback = "✅ إجابة صحيحة!" if is_correct else "❌ إجابة خاطئة!"
    await query.edit_message_text(feedback + "\n\nجاري تحميل السؤال التالي...")
    
    # عرض السؤال التالي بعد ثانية
    import asyncio
    await asyncio.sleep(1)
    await show_next_question(update, context)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """إنهاء الاختبار وعرض النتائج"""
    state = user_states[user_id]
    
    # حفظ النتيجة
    db.save_result(
        user_id,
        state['answers'],
        state['score'],
        len(state['questions'])
    )
    
    # بناء رسالة النتيجة
    text = f"🏁 انتهى الاختبار!\n\n"
    text += f"🎯 النتيجة: {state['score']}/{len(state['questions'])}\n"
    text += f"📊 النسبة: {state['score']/len(state['questions'])*100:.1f}%\n\n"
    
    if state['score'] == len(state['questions']):
        text += "🎉 ممتاز! إجابات صحيحة كلها!\n"
    elif state['score'] >= len(state['questions']) * 0.7:
        text += "👍 جيد جداً!\n"
    elif state['score'] >= len(state['questions']) * 0.5:
        text += "😊 ليس سيئاً!\n"
    else:
        text += "📚 تحتاج للمزيد من المذاكرة!\n"
    
    keyboard = [
        [InlineKeyboardButton("📝 اختبار جديد", callback_data='start_quiz'),
         InlineKeyboardButton("📊 نتائجي", callback_data='my_results')],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='student_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تنظيف حالة المستخدم
    del user_states[user_id]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup
        )

async def view_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الأسئلة للمعلم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    questions = db.get_questions_by_teacher(user_id)
    
    if not questions:
        await query.edit_message_text("📭 لم تقم بإضافة أي أسئلة بعد.")
        return
    
    text = f"📚 لديك {len(questions)} سؤال:\n\n"
    
    for i, q in enumerate(questions[:10], 1):  # عرض أول 10 أسئلة فقط
        text += f"{i}. {q.get('question', 'سؤال بصورة')[:30]}...\n"
        text += f"   النوع: {QUESTION_TYPES.get(q['type'], q['type'])}\n"
        text += f"   الإجابة: {q.get('correct_answer', 'غير محددة')}\n\n"
    
    keyboard = [[InlineKeyboardButton("رجوع", callback_data='teacher_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def my_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض نتائج الطالب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    results = db.get_student_results(user_id)
    
    if not results:
        await query.edit_message_text("📭 لم تأخذ أي اختبارات بعد.")
        return
    
    text = f"📊 نتائجك ({len(results)} اختبار):\n\n"
    
    total_score = 0
    total_possible = 0
    
    for i, r in enumerate(results[:10], 1):  # عرض أول 10 نتائج
        date = r['date'].split('T')[0]
        text += f"{i}. تاريخ: {date}\n"
        text += f"   النتيجة: {r['score']}/{r['total']}\n"
        text += f"   النسبة: {r['percentage']:.1f}%\n\n"
        
        total_score += r['score']
        total_possible += r['total']
    
    if total_possible > 0:
        avg_percentage = total_score / total_possible * 100
        text += f"📈 المعدل العام: {avg_percentage:.1f}%"
    
    keyboard = [[InlineKeyboardButton("رجوع", callback_data='student_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة لقائمة المعلم"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة سؤال", callback_data='add_question')],
        [InlineKeyboardButton("📋 عرض الأسئلة", callback_data='view_questions')],
        [InlineKeyboardButton("📊 إحصائيات", callback_data='teacher_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="👨‍🏫 قائمة المعلم:",
        reply_markup=reply_markup
    )

async def student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة لقائمة الطالب"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 بدء الاختبار", callback_data='start_quiz')],
        [InlineKeyboardButton("📊 نتائجي", callback_data='my_results')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="👨‍🎓 قائمة الطالب:",
        reply_markup=reply_markup
    )

async def teacher_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات المعلم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    questions = db.get_questions_by_teacher(user_id)
    
    text = f"📊 إحصائياتك:\n\n"
    text += f"📚 عدد الأسئلة: {len(questions)}\n"
    
    # عد الأسئلة حسب النوع
    type_count = {}
    for q in questions:
        q_type = q['type']
        type_count[q_type] = type_count.get(q_type, 0) + 1
    
    for t, count in type_count.items():
        text += f"   {QUESTION_TYPES.get(t, t)}: {count}\n"
    
    keyboard = [[InlineKeyboardButton("رجوع", callback_data='teacher_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة المساعدة"""
    help_text = """
    🤖 **بوت الاختبارات التعليمية**
    
    **كيفية الاستخدام:**
    
    👨‍🏫 **للمعلم:**
    1. اختر "معلم" عند بدء البوت
    2. استخدم "إضافة سؤال" لرفع أسئلة جديدة
    3. يمكنك رفع الصور أو كتابة الأسئلة نصياً
    4. اختر نوع السؤال (صح/خطأ أو اختيار من متعدد)
    
    👨‍🎓 **للطالب:**
    1. اختر "طالب" عند بدء البوت
    2. استخدم "بدء الاختبار" للإجابة على الأسئلة
    3. ستظهر لك النتيجة فور انتهاء الاختبار
    4. يمكنك مشاهدة نتائجك السابقة
    
    **أوامر عامة:**
    /start - إعادة بدء البوت
    /help - عرض هذه الرسالة
    
    **ملاحظة:** البوت يستخدم JSON للتخزين وللتجربة فقط.
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")
    
    if update and update.effective_user:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="❌ حدث خطأ ما. يرجى المحاولة مرة أخرى."
        )

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_role_selection, pattern='^role_'))
    application.add_handler(CallbackQueryHandler(add_question_start, pattern='^add_question$'))
    application.add_handler(CallbackQueryHandler(handle_question_type, pattern='^type_'))
    application.add_handler(CallbackQueryHandler(handle_answer_selection, pattern='^answer_'))
    application.add_handler(CallbackQueryHandler(start_quiz, pattern='^start_quiz$'))
    application.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern='^ans_'))
    application.add_handler(CallbackQueryHandler(view_questions, pattern='^view_questions$'))
    application.add_handler(CallbackQueryHandler(my_results, pattern='^my_results$'))
    application.add_handler(CallbackQueryHandler(teacher_menu, pattern='^teacher_menu$'))
    application.add_handler(CallbackQueryHandler(student_menu, pattern='^student_menu$'))
    application.add_handler(CallbackQueryHandler(teacher_stats, pattern='^teacher_stats$'))
    
    # معالجة الرسائل
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # معالجة الأخطاء
    application.add_error_handler(error_handler)
    
    # تشغيل البوت
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # التحقق من وجود التوكن
    if BOT_TOKEN == 'ضع_التوكن_هنا':
        print("❌ يرجى إضافة توكن البوت في ملف config.py")
        print("1. افتح ملف config.py")
        print("2. ضع التوكن الخاص بك بدلاً من 'ضع_التوكن_هنا'")
        print("3. أو أنشئ ملف .env وضع فيه: BOT_TOKEN=توكن_البوت")
    else:
        main()
