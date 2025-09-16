from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from config import GEMINI_API_KEY
import bcrypt
import joblib
import google.generativeai as genai
import re
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.config.from_pyfile('config.py')
mysql = MySQL(app)

model = joblib.load('models/trained_model.joblib')
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                        (username, hashed_password.decode('utf-8'), role))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            return f"Error: {str(e)}"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND role=%s", (username, role))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['username'] = username
            session['role'] = role
            if role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif role == 'patient':
                return redirect(url_for('patient_dashboard'))
    return render_template('login.html', error="Invalid Credentials")

@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'username' in session and session['role'] == 'doctor':
        if request.method == 'POST':
            patient_name = request.form['patient_name']
            feature_names = ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 
                             'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal']
            
            features = pd.DataFrame([[float(request.form[key]) for key in feature_names]], columns=feature_names)

           # features = [float(request.form[key]) for key in ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal']]
            
            prediction = model.predict(features)[0]
            diagnosis = 'Heart Disease Detected' if prediction == 1 else 'No Heart Disease'
            
            raw_diet_plan = generate_diet_plan(diagnosis)
            diet_plan = clean_text(raw_diet_plan)
            raw_medication_plan = generate_medication_plan(diagnosis)
            medication_plan = clean_text(raw_medication_plan)

            return render_template('doctor_dashboard.html', patient_name=patient_name,
                                   diagnosis=diagnosis, diet_plan=diet_plan,
                                   medication_plan=medication_plan)

    return render_template('doctor_dashboard.html')

@app.route('/send_report', methods=['POST'])
def send_report():
    patient_name = request.form['patient_name']
    diagnosis = request.form['diagnosis']
    diet_plan = request.form['diet_plan']
    medication_plan = request.form['medication_plan']

    cur = mysql.connection.cursor()
    sql = "INSERT INTO reports (patient_name, diagnosis, diet_plan, medication_plan) VALUES (%s, %s, %s, %s)"
    values = (patient_name, diagnosis, diet_plan, medication_plan)
    cur.execute(sql, values)

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('doctor_dashboard'))

@app.route('/cancel_report', methods=['POST'])
def cancel_report():
    patient_name = redirect(url_for('doctor_dashbaord'))

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'username' in session and session['role'] == 'patient':
        cur = mysql.connection.cursor()
        cur.execute("SELECT patient_name, diagnosis, diet_plan, medication_plan FROM reports WHERE patient_name = %s", (session['username'],))
        report = cur.fetchone()
        cur.close()
        return render_template('patient_dashboard.html', report=report)
    return redirect(url_for('login'))

def clean_text(text):
    text = re.sub(r'[#*]+', '', text)
    text = text.strip()
    text = re.sub(r'\n\n+', '</p><p>', text)
    text = text.replace("\n", "<br>")
    return f"<p>{text}<p>"

def generate_diet_plan(diagnosis):
    prompt = f"Generate a diet plan for a patient diagnosed with {diagnosis}."
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_medication_plan(diagnosis):
    prompt = f"Generate a medication plan for a patient diagnosed with {diagnosis}."
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

if __name__ == '__main__':
    app.run(debug=True)