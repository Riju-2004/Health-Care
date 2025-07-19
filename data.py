import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash

# Database connection
def get_db_connection():
    conn = sqlite3.connect('data.db', timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

# Create necessary tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            phone_number TEXT,
            gender TEXT,
            blood_group TEXT,
            role TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            Select_Date TEXT NOT NULL,
            Time_Slot TEXT NOT NULL,
            Select_Blood TEXT NOT NULL,
            Select_doctor TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user (user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointment_details (
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            gender TEXT NOT NULL,
            FOREIGN KEY (appointment_id) REFERENCES appointment (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slot_availability (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Select_Date TEXT NOT NULL,
            Time_Slot TEXT NOT NULL,
            available_slots INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            phone_number TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manager (
            manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            phone_number TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            doctor_id INTEGER,
            patient_id INTEGER,
            patient_name TEXT,
            patient_email TEXT,
            patient_phone TEXT,
            patient_gender TEXT,
            patient_blood TEXT,
            patient_age INTEGER,
            disease_name TEXT,
            medication_name TEXT,
            dosage TEXT,
            frequency TEXT,
            duration TEXT,
            date_signed DATE,
            doctor_signature TEXT,
            prescription_text TEXT,
            pdf_path TEXT,
            FOREIGN KEY (appointment_id) REFERENCES appointment (id),
            FOREIGN KEY (patient_id) REFERENCES user (user_id),
            FOREIGN KEY (doctor_id) REFERENCES user (user_id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize default slots
def initialize_slots():
    conn = get_db_connection()
    cursor = conn.cursor()

    time_slots = [
        ('10:00 AM', 10),
        ('12:00 PM', 10),
        ('3:00 PM', 15),
    ]

    # Example date setup (modify or remove as needed)
    sample_date = '2025-03-20'
    for time_slot, available_slots in time_slots:
        cursor.execute('''
            INSERT OR IGNORE INTO slot_availability (Select_Date, Time_Slot, available_slots)
            VALUES (?, ?, ?)
        ''', (sample_date, time_slot, available_slots))

    conn.commit()
    conn.close()

# Decorators for role-based access
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated

def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'manager':
            flash('Access denied: Manager only.')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated

def doctor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'doctor':
            flash('Access denied: Doctor only.')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated
