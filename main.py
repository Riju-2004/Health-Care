# MIT License
# 
# Copyright (c) 2025 Riju Mandal
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash, g
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import Color
import pandas as pd
import numpy as np
import pickle
from sklearn.metrics import classification_report
import sqlite3
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from twilio.rest import Client
import re
import dns.resolver
import random
import hashlib
from functools import wraps
from flask_login import current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Add a secret key for session management

# Load datasets
sym_des = pd.read_csv("./symtoms_df.csv")
precautions = pd.read_csv("./precautions_df.csv")
workout = pd.read_csv("./workout_df.csv")
description = pd.read_csv("./description.csv")
medications = pd.read_csv("./medications.csv")
diets = pd.read_csv("./diets.csv")

# Load the SVC model
try:
    with open('./svc.pkl', 'rb') as model_file:
        svc = pickle.load(model_file)
    # Check if the model is fitted
    if not hasattr(svc, 'support_vectors_'):
        raise ValueError("The SVC model is not fitted. Please refit the model before saving.")
    else:
        print("Model is fitted and ready for use.")
except Exception as e:
    print(f"Error loading the model: {e}")
    svc = None  # Ensure svc is defined even if loading fails

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# Create tables if they don't exist
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
        CREATE TABLE IF NOT EXISTS user_appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            appointment_details TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user (user_id)
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
            FOREIGN KEY (doctor_id) REFERENCES user (user_id),
            FOREIGN KEY (patient_id) REFERENCES user (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_gender_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the gender column already exists
    cursor.execute("PRAGMA table_info(user)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'gender' not in columns:
        cursor.execute('''
            ALTER TABLE user ADD COLUMN gender TEXT
        ''')
        conn.commit()
    conn.close()

def add_blood_group_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the blood_group column already exists
    cursor.execute("PRAGMA table_info(user)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'blood_group' not in columns:
        cursor.execute('''
            ALTER TABLE user ADD COLUMN blood_group TEXT
        ''')
        conn.commit()
    conn.close()

def add_patient_name_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the patient_name column already exists
    cursor.execute("PRAGMA table_info(prescriptions)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'patient_name' not in columns:
        cursor.execute('''
            ALTER TABLE prescriptions ADD COLUMN patient_name TEXT
        ''')
        conn.commit()
    conn.close()

def add_prescription_columns_if_missing():
    # Ensures all required columns exist in the prescriptions table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(prescriptions)")
    columns = [column[1] for column in cursor.fetchall()]
    required_columns = [
        ('patient_name', 'TEXT'),
        ('patient_email', 'TEXT'),
        ('patient_phone', 'TEXT'),
        ('patient_gender', 'TEXT'),
        ('patient_blood', 'TEXT'),
        ('patient_age', 'INTEGER'),
        ('prescription_text', 'TEXT'),
        ('pdf_path', 'TEXT')
    ]
    for col, col_type in required_columns:
        if col not in columns:
            cursor.execute(f"ALTER TABLE prescriptions ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()

def initialize_slots():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Define the initial slot availability
    initial_slots = [
        ('2025-03-20', '10:00 AM', 10),
        ('2025-03-20', '12:00 PM', 10),
        ('2025-03-20', '3:00 PM', 15),
        # Add more dates and slots as needed
    ]
    
    # Insert the initial slot availability into the database
    cursor.executemany('''
        INSERT INTO slot_availability (Select_Date, Time_Slot, available_slots)
        VALUES (?, ?, ?)
    ''', initial_slots)
    
    conn.commit()
    conn.close()

# Call the function to create tables when the application starts
create_tables()
add_prescription_columns_if_missing()
add_gender_column()
add_blood_group_column()
add_patient_name_column()
initialize_slots()

# Helper function
def helper(dis):
    try:
        # Disease Description
        desc_series = description[description['Disease'] == dis]['Description']
        desc = " ".join(desc_series.values) if not desc_series.empty else "No description available."

        # Precautions
        pre_df = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
        pre = [list(row) for row in pre_df.values] if not pre_df.empty else [["No precautions available."]]

        # Medications
        med_series = medications[medications['Disease'] == dis]['Medication']
        med = list(med_series.values) if not med_series.empty else ["No medications available."]

        # Diets
        die_series = diets[diets['Disease'] == dis]['Diet']
        die = list(die_series.values) if not die_series.empty else ["No diet recommendations available."]

        # Workout Recommendations
        wrkout_series = workout[workout['disease'] == dis]['workout']
        wrkout = list(wrkout_series.values) if not wrkout_series.empty else ["No workout recommendations available."]

        return desc, pre, med, die, wrkout

    except KeyError as e:
        print(f"Error: Column not found in DataFrame: {e}")
        return "No description available.", [["No precautions available."]], ["No medications available."], ["No diet recommendations available."], ["No workout recommendations available."]
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "No description available.", [["No precautions available."]], ["No medications available."], ["No diet recommendations available."], ["No workout recommendations available."]

# Symptoms and diseases dictionaries
symptoms_dict = {'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4, 'chills': 5, 'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9, 'muscle_wasting': 10, 'vomiting': 11, 'burning_micturition': 12, 'spotting_ urination': 13, 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 'cold_hands_and_feets': 17, 'mood_swings': 18, 'weight_loss': 19, 'restlessness': 20, 'lethargy': 21, 'patches_in_throat': 22, 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 'breathlessness': 27, 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish_skin': 32, 'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35, 'pain_behind_the_eyes': 36, 'back_pain': 37, 'constipation': 38, 'abdominal_pain': 39, 'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42, 'yellowing_of_eyes': 43, 'acute_liver_failure': 44, 'fluid_overload': 45, 'swelling_of_stomach': 46, 'swelled_lymph_nodes': 47, 'malaise': 48, 'blurred_and_distorted_vision': 49, 'phlegm': 50, 'throat_irritation': 51, 'redness_of_eyes': 52, 'sinus_pressure': 53, 'runny_nose': 54, 'congestion': 55, 'chest_pain': 56, 'weakness_in_limbs': 57, 'fast_heart_rate': 58, 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 'bloody_stool': 61, 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70, 'enlarged_thyroid': 71, 'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74, 'extra_marital_contacts': 75, 'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78, 'hip_joint_pain': 79, 'muscle_weakness': 80, 'stiff_neck': 81, 'swelling_joints': 82, 'movement_stiffness': 83, 'spinning_movements': 84, 'loss_of_balance': 85, 'unsteadiness': 86, 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89, 'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92, 'internal_itching': 93, 'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle_pain': 97, 'altered_sensorium': 98, 'red_spots_over_body': 99, 'belly_pain': 100, 'abnormal_menstruation': 101, 'dischromic _patches': 102, 'watering_from_eyes': 103, 'increased_appetite': 104, 'polyuria': 105, 'family_history': 106, 'mucoid_sputum': 107, 'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110, 'receiving_blood_transfusion': 111, 'receiving_unsterile_injections': 112, 'coma': 113, 'stomach_bleeding': 114, 'distention_of_abdomen': 115, 'history_of_alcohol_consumption': 116, 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 'palpitations': 120, 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124, 'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127, 'inflammatory_nails': 128, 'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction', 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 35: 'Psoriasis', 27: 'Impetigo'}

# Model Prediction function
def get_predicted_value(patient_symptoms):
    if svc is None:
        return "Model not loaded. Please check the model file."
    
    input_vector = np.zeros(len(symptoms_dict))  # This requires numpy
    for item in patient_symptoms:
        if item in symptoms_dict:
            input_vector[symptoms_dict[item]] = 1
    
    # Ensure the input vector has the correct shape
    if input_vector.shape[0] != len(symptoms_dict):
        return "Input vector has incorrect number of features."

    predicted_index = svc.predict([input_vector])[0]
    return diseases_list[predicted_index]

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Frame

# PDF Generation Function for Appointment
def generate_pdf(name, email, phone, gender, Select_Date, Time_Slot, Select_Blood, Select_doctor, filename, current_slot, appointment_id):
    # Define the path to the static directory
    static_dir = os.path.join(app.root_path, 'static')
    
    # Ensure the static directory exists
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Define the full path to the PDF file
    pdf_path = os.path.join(static_dir, filename)
    
    # Path to the logo image
    logo_path = os.path.join(static_dir, 'H.jpg')

    # Create the PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    # Add logo
    logo = Image(logo_path, width=1.5 * inch, height=1.5 * inch)
    logo.hAlign = 'CENTER'
    elements.append(logo)
    elements.append(Spacer(1, 12))

    # Add header
    header_style = ParagraphStyle(name='Header', fontSize=24, leading=28, alignment=1, textColor=colors.HexColor("#023e8a"))
    elements.append(Paragraph("Appointment Confirmation", header_style))
    elements.append(Spacer(1, 12))

    # Add the appointment details in a table
    data = [
        ["Field", "Details"],
        ["Appointment ID", appointment_id],  # Include the appointment ID
        ["Name", name],
        ["Email", email],
        ["Phone", phone],
        ["Gender", gender],
        ["Date", Select_Date],
        ["Time", Time_Slot],
        ["Blood Group", Select_Blood],
        ["Doctor", Select_doctor],
        ["Current Slot", current_slot]  # Include the current slot availability
    ]

    table = Table(data, colWidths=[2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023e8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#caf0f8")),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Add a footer
    footer_style = ParagraphStyle(name='Footer', fontSize=10, leading=12, alignment=1, textColor=colors.gray)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Thank you for scheduling your appointment with us.", footer_style))

    # Create a frame with a border
    frame = Frame(inch, inch - 0.5 * inch, 6.5 * inch, 10 * inch, showBoundary=1, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.build(elements, onFirstPage=draw_appointment_frame, onLaterPages=draw_appointment_frame)

    return pdf_path

def draw_appointment_frame(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#023e8a"))
    canvas.setLineWidth(2)
    canvas.rect(inch, inch - 0.5 * inch, 6.5 * inch, 10 * inch)
    
    # Add watermark
    logo_path = os.path.join(app.root_path, 'static', 'H.jpg')
    logo_width = 1.5 * inch
    logo_height = 1.5 * inch
    x_center = (doc.pagesize[0] - logo_width) / 2
    y_center = (doc.pagesize[1] - logo_height) / 2 + 2 * inch
    canvas.drawImage(logo_path, x_center, y_center, width=logo_width, height=logo_height, mask='auto')
    
    canvas.restoreState()

def is_valid_email(email):
    """
    Validate the email address format.
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

otp_storage = {}

def generate_otp():
    return str(random.randint(100000, 999999))

def send_email(to_email, subject, body, attachment_path=None):
    from_email = 'healthcare.code.red.2025@gmail.com'  # Replace with your email
    from_password = 'jgge ztyz snxf hydr'  # Replace with your email password

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Fix: Check if pdf_path is not None and file exists before attaching
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
            msg.attach(part)
    else:
        print(f"Warning: PDF path is invalid or file does not exist: {attachment_path}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Replace with your SMTP server and port
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("Email sent successfully")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    if not is_valid_email(email):
        return jsonify({"message": "Invalid email address."}), 400
    otp = generate_otp()
    otp_storage[email] = otp
    session['otp_verified'] = False  # Reset OTP verification status
    subject = "Your OTP Code"
    body = f"Your OTP code is {otp}. Please enter this code to verify your email."
    try:
        send_email(email, subject, body)
        print("Email sent successfully")  # Log message to confirm email sent
        return jsonify({"message": "OTP sent to your email."})
    except Exception as e:
        print(f"Failed to send OTP: {e}")  # Log error message
        return jsonify({"message": f"Failed to send OTP: {e}"}), 500

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    if not email or not otp:
        return jsonify({"message": "Email and OTP are required."}), 400
    if otp_storage.get(email) == otp:
        del otp_storage[email]  # Remove OTP after successful verification
        session['otp_verified'] = True  # Set OTP verification status
        return jsonify({"message": "OTP verified successfully."})
    else:
        session['otp_verified'] = False  # Ensure OTP verification status is reset
        return jsonify({"message": "Incorrect OTP."}), 400

@app.route('/set_message', methods=['POST'])
def set_message():
    message = request.form.get('message')
    session['manager_message'] = message
    flash('Message set successfully!', 'success')
    return redirect(url_for('manager_dashboard'))

@app.route('/')
def index():
    manager_message = session.get('manager_message', None)
    return render_template('index.html', manager_message=manager_message)

@app.route('/predict', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        symptoms = request.form.get('symptoms')
        if symptoms == "Symptoms":
            message = "Please either write symptoms or you have written misspelled symptoms"
            return render_template('index.html', message=message)
        else:
            user_symptoms = [s.strip() for s in symptoms.split(',')]
            user_symptoms = [symptom.strip("[]' ") for symptom in user_symptoms]
            predicted_disease = get_predicted_value(user_symptoms)
            dis_des, precautions, medications, rec_diet, workout = helper(predicted_disease)
            my_precautions = []
            if precautions:  # Check if precautions is not empty
                for i in precautions[0]:
                    my_precautions.append(i)
            return render_template('index.html', predicted_disease=predicted_disease, dis_des=dis_des,
                                   my_precautions=my_precautions, medications=medications, my_diet=rec_diet,
                                    workout=workout)
        return render_template('index.html')

@app.route('/about_page')
def about_page():
    return render_template("about.html")

@app.route('/contact_page')
def contact_page():
    return render_template("contact.html")

@app.route('/developer_page')
def developer_page():
    return render_template("developer.html")

@app.route('/medi_consult_page')
def medi_consult_page():
    return render_template("medi_consult.html")

@app.route('/doctor_availability_page')
def doctor_availability_page():
    return render_template("doctor_availability.html")

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST': 
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        gender = request.form.get('gender')  # Get the gender from the form
        Select_Date = request.form.get('Select_Date')
        Select_Blood = request.form.get('Select_Blood')

        if not is_valid_email(email):
            return render_template('appointment.html', message="Invalid email address format or domain does not exist.", current_date=datetime.datetime.now().strftime('%Y-%m-%d'))

        Select_doctor = get_doctor_for_date(datetime.datetime.strptime(Select_Date, '%Y-%m-%d'))  # Get the doctor for the selected date

        # Redirect to the time slot selection page
        return redirect(url_for('select_time_slot', name=name, email=email, phone=phone, gender=gender, Select_Date=Select_Date, Select_Blood=Select_Blood, Select_doctor=Select_doctor))
    else:
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        return render_template('appointment.html', current_date=current_date)

@app.route('/select_time_slot', methods=['GET', 'POST'])
def select_time_slot():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        gender = request.form.get('gender')  # Get the gender from the form
        Select_Date = request.form.get('Select_Date')
        Select_Blood = request.form.get('Select_Blood')
        Select_doctor = request.form.get('Select_doctor')

        # Debug: Print the selected date
        print(f"Selected Date: {Select_Date}")

        # Fetch or create slots for the selected date
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if slots exist for the selected date
        cursor.execute('''
            SELECT Time_Slot, available_slots FROM slot_availability
            WHERE Select_Date = ?
        ''', (Select_Date,))
        slots = cursor.fetchall()

        # If no slots exist, create them
        if not slots:
            time_slots = [
                ('10:00 AM', 10),
                ('12:00 PM', 10),
                ('3:00 PM', 15),
            ]
            for time_slot, available_slots in time_slots:
                cursor.execute('''
                    INSERT INTO slot_availability (Select_Date, Time_Slot, available_slots)
                    VALUES (?, ?, ?)
                ''', (Select_Date, time_slot, available_slots))
            conn.commit()

            # Fetch the newly created slots
            cursor.execute('''
                SELECT Time_Slot, available_slots FROM slot_availability
                WHERE Select_Date = ?
            ''', (Select_Date,))
            slots = cursor.fetchall()

        conn.close()

        # Debug: Print the fetched slots
        print(f"Fetched Slots: {slots}")

        return render_template('select_time_slot.html', name=name, email=email, phone=phone, gender=gender, Select_Date=Select_Date, Select_Blood=Select_Blood, Select_doctor=Select_doctor, slots=slots)

@app.route('/confirm_appointment', methods=['POST'])
def confirm_appointment():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    gender = request.form.get('gender')  # Get the gender from the form
    Select_Date = request.form.get('Select_Date')
    Time_Slot = request.form.get('Time_Slot')
    Select_Blood = request.form.get('Select_Blood')
    Select_doctor = request.form.get('Select_doctor')

    # Debug: Print the selected time slot
    print(f"Selected Time Slot: {Time_Slot}")

    # Validate email address format
    if not is_valid_email(email):
        return render_template('appointment.html', message="This mail is not existing.", current_date=datetime.datetime.now().strftime('%Y-%m-%d'))

    # Check slot availability
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT available_slots FROM slot_availability
        WHERE Select_Date = ? AND Time_Slot = ?
    ''', (Select_Date, Time_Slot))
    slot = cursor.fetchone()

    if slot and slot['available_slots'] > 0:
        try:
            # Insert appointment into the appointment table
            cursor.execute('''
                INSERT INTO appointment (user_id, Select_Date, Time_Slot, Select_Blood, Select_doctor)
                VALUES (?, ?, ?, ?, ?)
            ''', (1, Select_Date, Time_Slot, Select_Blood, Select_doctor))

            # Get the last inserted appointment ID
            appointment_id = cursor.lastrowid

            # Insert appointment details into the appointment_details table
            cursor.execute('''
                INSERT INTO appointment_details (appointment_id, name, email, phone, gender)
                VALUES (?, ?, ?, ?, ?)
            ''', (appointment_id, name, email, phone, gender))

            # Update slot availability
            cursor.execute('''
                UPDATE slot_availability
                SET available_slots = available_slots - 1
                WHERE Select_Date = ? AND Time_Slot = ?
            ''', (Select_Date, Time_Slot))

            # Calculate the current slot (initial slots - remaining slots)
            initial_slots = 10 if Time_Slot in ['10:00 AM', '12:00 PM'] else 15  # Adjust based on your initial slot setup
            current_slot = initial_slots - (slot['available_slots'] - 1)

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error during appointment confirmation: {e}")
            return "An error occurred while confirming the appointment.", 500
        finally:
            conn.close()

        # Generate PDF
        pdf_filename = f"appointment_{name.replace(' ', '_')}.pdf"
        pdf_path = generate_pdf(name, email, phone, gender, Select_Date, Time_Slot, Select_Blood, Select_doctor, pdf_filename, current_slot, appointment_id)
        
        # Send Email
        email_subject = "Appointment Confirmation"
        email_body = f"Your appointment on {Select_Date} at {Time_Slot} has been confirmed. Please find the attached confirmation PDF."
        send_email(email, email_subject, email_body, pdf_path)

        return render_template('appointment_success.html', pdf_filename=pdf_filename, appointment_id=appointment_id)
    else:
        conn.close()
        return "No slots available for the selected time.", 400

@app.route('/user_appointments')
def user_appointments():
    user_id = 1  # Replace with the logged-in user's ID (e.g., from session)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, ad.name, ad.email, ad.phone, ad.gender
        FROM appointment a
        JOIN appointment_details ad ON a.id = ad.appointment_id
        WHERE a.user_id = ?
    ''', (user_id,))
    appointments = cursor.fetchall()
    conn.close()

    return render_template('user_appointments.html', appointments=appointments)

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'doctor':
            flash('You do not have permission to access this page.')
            return redirect(url_for('login_admin'))
        return f(*args, **kwargs)
    return decorated_function

def send_prescription_email(to_email, pdf_path):
    from_email = 'healthcare.code.red.2025@gmail.com'  # Replace with your email
    from_password = 'jgge ztyz snxf hydr'  # Replace with your email password

    subject = "Your Prescription"
    body = "Please find attached your prescription."

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Fix: Check if pdf_path is not None, is a string, and file exists before attaching
    if pdf_path and isinstance(pdf_path, str) and os.path.exists(pdf_path):
        try:
            with open(pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(pdf_path)}')
                msg.attach(part)
        except Exception as e:
            print(f"Failed to attach PDF: {e}")
    else:
        print(f"Warning: PDF path is invalid or file does not exist: {pdf_path}")

    try:
        # Ensure to_email is not None and is a string
        if not to_email or not isinstance(to_email, str) or to_email.strip() == "":
            print("Error: Recipient email is missing or invalid.")
            return
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Replace with your SMTP server and port
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, [to_email], text)  # sendmail expects a list for recipients
        server.quit()
        print("Email sent successfully")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/developer')
def developer():
    return render_template("developer.html")

@app.route('/medi_consult')
def medi_consult():
    return render_template("medi_consult.html")

@app.route('/doctor_availability')
def doctor_availability():
    return render_template("doctor_availability.html")

@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST': 
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        gender = request.form.get('gender')  # Get the gender from the form
        Select_Date = request.form.get('Select_Date')
        Select_Blood = request.form.get('Select_Blood')

        if not is_valid_email(email):
            return render_template('appointment.html', message="Invalid email address format or domain does not exist.", current_date=datetime.datetime.now().strftime('%Y-%m-%d'))

        Select_doctor = get_doctor_for_date(datetime.datetime.strptime(Select_Date, '%Y-%m-%d'))  # Get the doctor for the selected date

        # Redirect to the time slot selection page
        return redirect(url_for('select_time_slot', name=name, email=email, phone=phone, gender=gender, Select_Date=Select_Date, Select_Blood=Select_Blood, Select_doctor=Select_doctor))
    else:
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        return render_template('appointment.html', current_date=current_date)

def get_doctor_for_date(selected_date):
    # List of doctors for each day of the week (Monday to Saturday)
    doctors = {
        0: "Dr. John Doe, MBBS",       # Monday
        1: "Dr. Jane Smith, MD",       # Tuesday
        2: "Dr. Michael Brown, MS",    # Wednesday
        3: "Dr. Emily White, DM",      # Thursday
        4: "Dr. William Green, MBBS, MS", # Friday
        5: "Dr. Sarah Johnson, MBBS"   # Saturday
    }
    # Get the day of the week (0=Monday, 1=Tuesday, ..., 5=Saturday)
    day_of_week = selected_date.weekday()
    return doctors.get(day_of_week, "No doctor available")  # Return "No doctor available" for Sunday

@app.route('/admin')
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM user')
    user_count = cursor.fetchone()['count']
    conn.close()

    # Check if all 6 doctors and 1 manager have registered
    sign_in_disabled = user_count >= 7
    return render_template("admin.html", sign_in_disabled=sign_in_disabled)

@app.route('/register_admin', methods=['POST'])
def register_admin():
    if not session.get('otp_verified'):
        flash("OTP verification is required.")
        return redirect(url_for('admin'))
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        role = request.form.get('role')

        if not is_valid_email(email):
            flash("This mail is not existing.")
            return redirect(url_for('admin'))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute('SELECT * FROM user WHERE username = ? OR email = ?', (username, email))
        existing_user = cursor.fetchone()
        if (existing_user):
            flash("User already registered.")
            conn.close()
            return redirect(url_for('admin'))

        # Check if the role is already registered
        cursor.execute('SELECT COUNT(*) as count FROM user WHERE role = ?', (role,))
        role_count = cursor.fetchone()['count']
        if (role == 'manager' and role_count >= 1) or (role == 'doctor' and role_count >= 6):
            flash(f"{role.capitalize()} registration is closed.")
            conn.close()
            return redirect(url_for('admin'))

        cursor.execute('''
            INSERT INTO user (username, password, email, full_name, phone_number, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password, email, full_name, phone_number, role))
        conn.commit()
        conn.close()
        flash("Registration successful.")
        session['otp_verified'] = False  # Reset OTP verification status after successful registration
        return redirect(url_for('admin_success'))
    except Exception as e:
        print(f"Error in register_admin: {e}")
        flash("An error occurred during registration. Please try again.")
        return redirect(url_for('admin'))

@app.route('/admin_success')
def admin_success():
    return render_template('admin_success.html')

@app.route('/login_admin', methods=['POST'])
def login_admin():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE username = ? AND password = ? AND role = ?', (username, password, role))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user_id'] = user['user_id']  # Store user ID in session
        session['username'] = user['username']  # Store username in session
        session['role'] = user['role']
        if role == 'doctor':
            return redirect(url_for('doctor_dashboard', username=username))
        elif role == 'manager':
            return redirect(url_for('manager_dashboard'))
        else:
            return redirect(url_for('admin_dashboard'))
    else:
        flash("Invalid credentials.")
        return redirect(url_for('admin'))

@app.route('/forgot_credentials', methods=['POST'])
def forgot_credentials():
    email = request.form.get('email')
    if not is_valid_email(email):
        flash("This mail is not existing.")
        return redirect(url_for('admin'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    if user:
        # Send email with credentials
        subject = "Your Account Credentials"
        body = f"Username: {user['username']}\nPassword: {user['password']}\nRole: {user['role']}"
        send_email(user['email'], subject, body)
        flash("Credentials have been sent to your email.")
        return redirect(url_for('admin'))
    else:
        flash("Email not found.")
        return redirect(url_for('admin'))

@app.route('/doctor_dashboard/<username>')
def doctor_dashboard(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch the doctor's details
    cursor.execute('SELECT * FROM user WHERE username = ?', (username,))
    doctor = cursor.fetchone()
    
    # Fetch all appointments
    cursor.execute('''
        SELECT a.*, ad.name, ad.email, ad.phone, ad.gender
        FROM appointment a
        JOIN appointment_details ad ON a.id = ad.appointment_id
    ''')
    appointments = cursor.fetchall()
    
    conn.close()
    return render_template('doctor_dashboard.html', doctor=doctor, appointments=appointments)

@app.route('/manager_dashboard')
def manager_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch all users
    cursor.execute('SELECT * FROM user')
    users = cursor.fetchall()
    users = [dict(user) for user in users]  # Convert rows to dictionaries

    # Fetch all appointments
    cursor.execute('SELECT a.*, ad.name, ad.email, ad.phone, ad.gender FROM appointment a JOIN appointment_details ad ON a.id = ad.appointment_id')
    appointments = cursor.fetchall()
    appointments = [dict(appointment) for appointment in appointments]  # Convert rows to dictionaries
    
    conn.close()

    if g.user:  # Assuming g.user is set to the current user
        return render_template('manager_dashboard.html', current_user=g.user, users=users, appointments=appointments)
    else:
        return render_template('manager_dashboard.html', message="You need to log in first.")

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
        g.user = cursor.fetchone()
        conn.close()

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            phone_number = request.form.get('phone_number')
            role = request.form.get('role')

            if not is_valid_email(email):
                return render_template('edit_user.html', user={'user_id': user_id, 'username': username, 'password': password, 'email': email, 'full_name': full_name, 'phone_number': phone_number, 'role': role}, message="This mail is not existing.")
            
            cursor.execute('''
                UPDATE user
                SET username = ?, password = ?, email = ?, full_name = ?, phone_number = ?, role = ?
                WHERE user_id = ?
            ''', (username, password, email, full_name, phone_number, role, user_id))
            
            # Update doctor table if role is doctor
            if (role == 'doctor'):
                cursor.execute('''
                    UPDATE doctors
                    SET username = ?, password = ?, email = ?, full_name = ?, phone_number = ?
                    WHERE doctor_id = ?
                ''', (username, password, email, full_name, phone_number, user_id))
            
            conn.commit()
            conn.close()
            return redirect(url_for('manager_dashboard'))
        cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return render_template('edit_user.html', user=user)
    except Exception as e:
        print(f"Error in edit_user: {e}")
        return render_template('edit_user.html', message="An error occurred while editing the user.")

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete from user table
    cursor.execute('DELETE FROM user WHERE user_id = ?', (user_id,))
    
    # Delete from doctor table if role is doctor
    cursor.execute('DELETE FROM doctors WHERE doctor_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manager_dashboard'))

@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            gender = request.form.get('gender')
            Select_Date = request.form.get('Select_Date')
            Time_Slot = request.form.get('Time_Slot')
            Select_Blood = request.form.get('Select_Blood')
            Select_doctor = request.form.get('Select_doctor')

            if not is_valid_email(email):
                return render_template('edit_appointment.html', appointment={'id': appointment_id, 'name': name, 'email': email, 'phone': phone, 'gender': gender, 'Select_Date': Select_Date, 'Time_Slot': Time_Slot, 'Select_Blood': Select_Blood, 'Select_doctor': Select_doctor}, message="This mail is not existing.")
            
            cursor.execute('''
                UPDATE appointment
                SET Select_Date = ?, Time_Slot = ?, Select_Blood = ?, Select_doctor = ?
                WHERE id = ?
            ''', (Select_Date, Time_Slot, Select_Blood, Select_doctor, appointment_id))
            
            cursor.execute('''
                UPDATE appointment_details
                SET name = ?, email = ?, phone = ?, gender = ?
                WHERE appointment_id = ?
            ''', (name, email, phone, gender, appointment_id))
            
            conn.commit()
            conn.close()
            return redirect(url_for('manager_dashboard'))
        cursor.execute('SELECT * FROM appointment WHERE id = ?', (appointment_id,))
        appointment = cursor.fetchone()
        cursor.execute('SELECT * FROM appointment_details WHERE appointment_id = ?', (appointment_id,))
        appointment_details = cursor.fetchone()
        conn.close()
        return render_template('edit_appointment.html', appointment={**appointment, **appointment_details})
    except Exception as e:
        print(f"Error in edit_appointment: {e}")
        return render_template('edit_appointment.html', message="An error occurred while editing the appointment.")

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM appointment WHERE id = ?', (appointment_id,))
    cursor.execute('DELETE FROM appointment_details WHERE appointment_id = ?', (appointment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manager_dashboard'))

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        flash("You need to log in first.")
        return redirect(url_for('admin'))
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user['role'] == 'doctor':
        return redirect(url_for('doctor_dashboard', username=user['username']))
    elif user['role'] == 'manager':
        return redirect(url_for('manager_dashboard'))
    else:
        flash("Unauthorized access.")
        return redirect(url_for('admin'))

def generatePrescriptionPDF(data):
    # Define the path to the static directory
    static_dir = os.path.join(app.root_path, 'static')
    
    # Ensure the static directory exists
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Define the full path to the PDF file
    pdf_path = os.path.join(static_dir, f"prescription_{data['appointment_id']}.pdf")
    
    # Path to the logo image
    logo_path = os.path.join(static_dir, 'H.jpg')

    # Create the PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    # Add logo
    logo = Image(logo_path, width=1.5 * inch, height=1.5 * inch)
    logo.hAlign = 'CENTER'
    elements.append(logo)
    elements.append(Spacer(1, 12))

    # Add header
    header_style = ParagraphStyle(name='Header', fontSize=24, leading=28, alignment=1, textColor=colors.HexColor("#023e8a"))
    elements.append(Paragraph("Prescription", header_style))
    elements.append(Spacer(1, 12))

    # Add the prescription details in a table
    table_data = [
        ["Field", "Details"],
        ["Appointment ID", data['appointment_id']],
        ["Patient Name", data['patient_name']],
        ["Email", data['patient_email']],
        ["Phone", data['patient_phone']],
        ["Gender", data['patient_gender']],
        ["Blood Group", data['patient_blood']],
        ["Age", data['patient_age']],
        ["Disease Name", data['disease_name']],
        ["Medication Name", data['medication_name']],
        ["Dosage", data['dosage']],
        ["Frequency", data['frequency']],
        ["Duration", data['duration']],
        # Add these rows to the PDF
        ["Date Signed", data.get('date_signed', '')],
        ["Doctor Signature", data.get('doctor_signature', '')],
        ["Prescription Text", data.get('prescription_text', '')]
    ]

    table = Table(table_data, colWidths=[2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023e8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#caf0f8")),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Add a footer
    footer_style = ParagraphStyle(name='Footer', fontSize=10, leading=12, alignment=1, textColor=colors.gray)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Thank you for using our service.", footer_style))

    # Create a frame with a border
    frame = Frame(inch, inch - 0.5 * inch, 6.5 * inch, 10 * inch, showBoundary=1, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.build(elements, onFirstPage=draw_prescription_frame, onLaterPages=draw_prescription_frame)

    return pdf_path

def draw_prescription_frame(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#023e8a"))
    canvas.setLineWidth(2)
    canvas.rect(inch, inch - 0.5 * inch, 6.5 * inch, 10 * inch)
    
    # Add watermark
    logo_path = os.path.join(app.root_path, 'static', 'H.jpg')
    logo_width = 1.5 * inch
    logo_height = 1.5 * inch
    x_center = (doc.pagesize[0] - logo_width) / 2
    y_center = (doc.pagesize[1] - logo_height) / 2 + 2 * inch
    canvas.drawImage(logo_path, x_center, y_center, width=logo_width, height=logo_height, mask='auto')
    
    canvas.restoreState()

@app.route('/write-prescription/<int:appointment_id>', methods=['GET', 'POST'])
@doctor_required
def write_prescription(appointment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, ad.name AS patient_name, ad.email AS patient_email, ad.phone AS patient_phone, ad.gender AS patient_gender, a.Select_Blood AS patient_blood
        FROM appointment a
        JOIN appointment_details ad ON a.id = ad.appointment_id
        WHERE a.id = ?
    ''', (appointment_id,))
    appointment = cursor.fetchone()
    conn.close()

    # Prepare patient dict for template rendering
    patient = {
        "name": appointment["patient_name"] if appointment else "",
        "email": appointment["patient_email"] if appointment else "",
        "phone": appointment["patient_phone"] if appointment else "",
        "gender": appointment["patient_gender"] if appointment else ""
    }

    if request.method == 'POST':
        # Use request.form for HTML form POST, request.json for JS fetch POST
        if request.is_json:
            data = request.get_json()
            patient_name = data.get('patient_name')
            patient_email = data.get('patient_email')
            patient_phone = data.get('patient_phone')
            patient_gender = data.get('patient_gender')
            patient_blood = data.get('patient_blood')
            patient_age = data.get('patient_age')
            disease_name = data.get('disease_name')
            medication_name = data.get('medication_name')
            dosage = data.get('dosage')
            frequency = data.get('frequency')
            duration = data.get('duration')
            date_signed = data.get('date_signed')
            doctor_signature = data.get('doctor_signature')
            prescription_text = data.get('prescription_text')
            action = data.get('action')
        else:
            patient_name = request.form.get('patient_name')
            patient_email = request.form.get('patient_email')
            patient_phone = request.form.get('patient_phone')
            patient_gender = request.form.get('patient_gender')
            patient_blood = request.form.get('patient_blood')
            patient_age = request.form.get('patient_age')
            disease_name = request.form.get('disease_name')
            medication_name = request.form.get('medication_name')
            dosage = request.form.get('dosage')
            frequency = request.form.get('frequency')
            duration = request.form.get('duration')
            date_signed = request.form.get('date_signed')
            doctor_signature = request.form.get('doctor_signature')
            prescription_text = request.form.get('prescription_text')
            action = request.form.get('action')

        # Set default values if any of these are missing or empty
        if not date_signed or str(date_signed).strip() == '':
            date_signed = datetime.datetime.now().strftime('%Y-%m-%d')
        if not doctor_signature or str(doctor_signature).strip() == '':
            doctor_signature = "Signed by Doctor"
        if not prescription_text or str(prescription_text).strip() == '':
            prescription_text = f"Prescription for {patient_name}: {disease_name}, {medication_name}, {dosage}, {frequency}, {duration}"

        # Convert patient_age to int if not empty
        if patient_age is not None and str(patient_age).strip() != '':
            try:
                patient_age = int(patient_age)
            except ValueError:
                patient_age = None
        else:
            patient_age = None

        # Debug: Print all field values to diagnose missing/empty fields
        print("Prescription POST fields:")
        print("patient_name:", patient_name)
        print("patient_email:", patient_email)
        print("patient_phone:", patient_phone)
        print("patient_gender:", patient_gender)
        print("patient_blood:", patient_blood)
        print("patient_age:", patient_age)
        print("disease_name:", disease_name)
        print("medication_name:", medication_name)
        print("dosage:", dosage)
        print("frequency:", frequency)
        print("duration:", duration)

        required_fields = [
            patient_name, patient_email, patient_phone, patient_gender, patient_blood,
            disease_name, medication_name, dosage, frequency, duration
        ]
        if any(field is None or str(field).strip() == '' for field in required_fields) or patient_age is None:
            print("Prescription save failed: missing or empty field(s).")
            flash('All fields are required. Please fill in all fields before saving the prescription.')
            return jsonify({'success': False, 'error': 'All fields are required.'}), 400

        # Insert prescription data into the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO prescriptions (
                    appointment_id, doctor_id, patient_id, patient_name, patient_email, patient_phone, patient_gender, patient_blood, patient_age,
                    disease_name, medication_name, dosage, frequency, duration, date_signed, doctor_signature, prescription_text, pdf_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                appointment_id,
                session['user_id'],
                appointment['user_id'],
                patient_name,
                patient_email,
                patient_phone,
                patient_gender,
                patient_blood,
                patient_age,
                disease_name,
                medication_name,
                dosage,
                frequency,
                duration,
                date_signed,
                doctor_signature,
                prescription_text,
                None  # Placeholder for pdf_path, will update after PDF generation
            ))
            prescription_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Generate PDF
            prescription_data = {
                "appointment_id": appointment_id,
                "patient_name": patient_name,
                "patient_email": patient_email,
                "patient_phone": patient_phone,
                "patient_gender": patient_gender,
                "patient_blood": patient_blood,
                "patient_age": patient_age,
                "disease_name": disease_name,
                "medication_name": medication_name,
                "dosage": dosage,
                "frequency": frequency,
                "duration": duration,
                "date_signed": date_signed,
                "doctor_signature": doctor_signature,
                "prescription_text": prescription_text
            }
            pdf_path = generatePrescriptionPDF(prescription_data)

            # Update the prescription row with the correct pdf_path
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE prescriptions SET pdf_path = ? WHERE id = ?', (pdf_path, prescription_id))
            conn.commit()
            conn.close()

            # Send email if required
            if action == 'send':
                send_prescription_email(patient_email, pdf_path)
                flash('Prescription saved and sent successfully.')
            else:
                flash('Prescription saved successfully.')

            return jsonify({'success': True, 'pdf_path': pdf_path})

        except Exception as e:
            print(f"Error saving prescription: {e}")
            return jsonify({'success': False, 'error': 'An error occurred while saving the prescription.'}), 500

    return render_template('write-prescription.html', appointment=appointment, patient=patient)

@app.route('/send-prescription', methods=['POST'])
@doctor_required
def send_prescription():
    data = request.get_json()
    pdf_path = data.get('pdf_path')
    if not pdf_path:
        return jsonify({'success': False, 'error': 'No PDF path provided'}), 400

    print("Received pdf_path for sending prescription:", pdf_path)

    # Find the prescription by pdf_path
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM prescriptions WHERE pdf_path = ?', (pdf_path,))
    prescription = cursor.fetchone()
    conn.close()

    print("Prescription found in DB:", prescription)

    if not prescription:
        return jsonify({'success': False, 'error': 'Prescription not found'}), 404

    # Check if patient_email is present and not None
    patient_email = prescription['patient_email'] if 'patient_email' in prescription.keys() else None

    # If patient_email is None, fetch from appointment_details as fallback
    if not patient_email:
        appointment_id = prescription['appointment_id']
        print(f"patient_email is None, trying to fetch from appointment_details for appointment_id={appointment_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM appointment_details WHERE appointment_id = ?', (appointment_id,))
        details = cursor.fetchone()
        conn.close()
        if details and 'email' in details.keys():
            patient_email = details['email']
            print(f"Found patient_email from appointment_details: {patient_email}")
        else:
            print("Could not find patient_email in appointment_details.")

    print("Patient email for sending prescription:", patient_email)

    if not patient_email or not isinstance(patient_email, str) or patient_email.strip() == "":
        return jsonify({'success': False, 'error': 'Patient email not found in prescription or appointment details.'}), 400

    try:
        send_prescription_email(patient_email, pdf_path)
        return jsonify({'success': True, 'message': 'Prescription sent successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/view-prescription/<int:appointment_id>', methods=['GET'])
@doctor_required
def view_prescription(appointment_id):
    # Find the latest valid prescription by appointment_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM prescriptions
        WHERE appointment_id = ? AND pdf_path IS NOT NULL AND disease_name IS NOT NULL AND medication_name IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
    ''', (appointment_id,))
    prescription = cursor.fetchone()
    conn.close()

    if not prescription:
        return "Prescription not found or not generated yet. Please save the prescription first.", 404

    pdf_path = prescription['pdf_path']

    # Ensure the PDF path is absolute and exists
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(app.root_path, pdf_path)
    if not os.path.exists(pdf_path):
        return "Prescription PDF not found.", 404

    from flask import send_file, make_response
    response = make_response(send_file(pdf_path, mimetype='application/pdf', as_attachment=False))
    # Disable caching to always serve the latest PDF
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Content-Disposition"] = f'inline; filename="{os.path.basename(pdf_path)}"'
    return response

if __name__ == "__main__":
    app.run(debug=True)

if __name__ == "__main__":
    app.run(debug=True)
if __name__ == "__main__":
    app.run(debug=True)
    app.run(debug=True)
if __name__ == "__main__":
    app.run(debug=True)
if __name__ == "__main__":
    app.run(debug=True)

