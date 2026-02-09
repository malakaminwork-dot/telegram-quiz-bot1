import json
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.teachers_file = 'teachers.json'
        self.students_file = 'students.json'
        self.questions_file = 'questions.json'
        self.results_file = 'results.json'
        self.init_files()
    
    def init_files(self):
        """تهيئة ملفات JSON إذا لم تكن موجودة"""
        files = [
            (self.teachers_file, {}),
            (self.students_file, {}),
            (self.questions_file, {}),
            (self.results_file, {})
        ]
        
        for file_name, default_data in files:
            if not os.path.exists(file_name):
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)
    
    # === إدارة المعلمين ===
    def add_teacher(self, user_id, username, name):
        with open(self.teachers_file, 'r', encoding='utf-8') as f:
            teachers = json.load(f)
        
        teachers[str(user_id)] = {
            'username': username,
            'name': name,
            'created_at': datetime.now().isoformat()
        }
        
        with open(self.teachers_file, 'w', encoding='utf-8') as f:
            json.dump(teachers, f, ensure_ascii=False, indent=2)
    
    def is_teacher(self, user_id):
        with open(self.teachers_file, 'r', encoding='utf-8') as f:
            teachers = json.load(f)
        return str(user_id) in teachers
    
    # === إدارة الطلاب ===
    def add_student(self, user_id, username, name):
        with open(self.students_file, 'r', encoding='utf-8') as f:
            students = json.load(f)
        
        students[str(user_id)] = {
            'username': username,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'quizzes_taken': 0,
            'total_score': 0
        }
        
        with open(self.students_file, 'w', encoding='utf-8') as f:
            json.dump(students, f, ensure_ascii=False, indent=2)
    
    def is_student(self, user_id):
        with open(self.students_file, 'r', encoding='utf-8') as f:
            students = json.load(f)
        return str(user_id) in students
    
    # === إدارة الأسئلة ===
    def add_question(self, teacher_id, question_data):
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        question_id = f"q{len(questions) + 1}_{teacher_id}"
        questions[question_id] = {
            **question_data,
            'id': question_id,
            'teacher_id': str(teacher_id),
            'created_at': datetime.now().isoformat()
        }
        
        with open(self.questions_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        return question_id
    
    def get_questions_by_teacher(self, teacher_id):
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        return [q for q in questions.values() if q['teacher_id'] == str(teacher_id)]
    
    def get_all_questions(self):
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # === إدارة النتائج ===
    def save_result(self, student_id, quiz_data, score, total):
        with open(self.results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        result_id = f"r{len(results) + 1}_{student_id}"
        results[result_id] = {
            'student_id': str(student_id),
            'quiz_data': quiz_data,
            'score': score,
            'total': total,
            'percentage': (score / total * 100) if total > 0 else 0,
            'date': datetime.now().isoformat()
        }
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # تحديث إحصائيات الطالب
        with open(self.students_file, 'r', encoding='utf-8') as f:
            students = json.load(f)
        
        if str(student_id) in students:
            students[str(student_id)]['quizzes_taken'] += 1
            students[str(student_id)]['total_score'] += score
        
        with open(self.students_file, 'w', encoding='utf-8') as f:
            json.dump(students, f, ensure_ascii=False, indent=2)
        
        return result_id
    
    def get_student_results(self, student_id):
        with open(self.results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return [r for r in results.values() if r['student_id'] == str(student_id)]
