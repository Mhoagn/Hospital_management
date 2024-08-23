from flask import Blueprint, render_template, redirect, url_for, session, json, jsonify
from flask_login import login_required, current_user
from .models import Doctor, db, Patient, Examination, Department
from sqlalchemy import text, func, extract
import datetime
from datetime import date, datetime

views = Blueprint('views', __name__)

#------------------------------- Home Page -------------------------------
@views.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

@views.route('/', methods=['GET'])
def homepage():
    return render_template('homepage.html')

@views.route('/home1/<int:user_id>', methods=['GET'])
@login_required
def home1(user_id):
    if current_user.role == 1:
        return render_template("home1.html", user=current_user)
    else:
        return redirect(url_for('views.home'))

@views.route('/home2/<int:user_id>', methods=['GET'])
@login_required
def home2(user_id):
    if current_user.role == 2:
        doctor = Doctor.query.filter_by(user_id=user_id).first()
        department_name = doctor.department.department_name if doctor and doctor.department else 'Không có thông tin'
        return render_template("home2.html", user=current_user, department_name=department_name)
    else:
        return redirect(url_for('views.home'))

#------------------------------- Patient -------------------------------    
@views.route('/examination_history/<int:user_id>', methods=['GET'])
@login_required
def examination_history(user_id):
    if current_user.user_id != user_id:
        return redirect(url_for('views.home'))
    
    if current_user.role == 1:
        query = text('SELECT * FROM examination WHERE user_id = :user_id')
    elif current_user.role == 2:
        query = text('SELECT * FROM examination WHERE doctor_id = :user_id')
    else:
        return redirect(url_for('views.home'))
    
    examinations = db.session.execute(query, {'user_id': user_id}).fetchall()

    examination_objects = []
    for exam in examinations:
        examination = {
            'examination_id': exam[0],
            'user_id': exam[1],
            'date': exam[2],
            'doctor_id': exam[3],
            'age': exam[4],
            'height': exam[5],
            'weight': exam[6],
            'blood_pressure_S': exam[7],
            'blood_pressure_D': exam[8],
            'heart_rate': exam[9],
            'fee': round(exam[10], 2) if isinstance(exam[10], float) else exam[10],
            'conclusion': exam[11],
            'time_arranged': exam[12]
        }
        examination_objects.append(examination)

    return render_template('examination_history.html', user=current_user, examinations=examination_objects)

#------------------------------- Doctors -------------------------------
@views.route('/calendar/', methods=['GET'])
@login_required
def calendar():
    if current_user.role != 2:
        return redirect(url_for('views.home'))
    
    today = datetime.date.today()
    month = today.strftime('%m')
    year = today.strftime('%Y')

    query = text('''
        SELECT examination_id, user_id AS patient_id, date, doctor_id
        FROM examination
        WHERE strftime('%m', date) = :month
        AND strftime('%Y', date) = :year
        AND doctor_id = :doctor_id
    ''')

    appointments = db.session.execute(query, {'month': month, 'year': year, 'doctor_id': current_user.user_id}).fetchall()

    appointment_objects = []
    for appt in appointments:
        appointment = {
            'examination_id': appt[0],
            'patient_id': appt[1],
            'date': appt[2],
            'doctor_id': appt[3]
        }
        appointment_objects.append(appointment)

    return render_template('lichkham.html', appointments=appointment_objects, user=current_user)

#------------------------------- Admin -------------------------------
@views.route('/admin/<int:user_id>', methods=['GET'])
@login_required
def admin(user_id):
    # Query for total counts
    total_doctors = db.session.query(func.count(Doctor.user_id)).scalar()
    total_patients = db.session.query(func.count(Patient.user_id)).scalar()
    total_examinations = db.session.query(func.count(Examination.examination_id)).scalar()

    today = date.today()
    active_patients = db.session.query(func.count(func.distinct(Examination.user_id))).filter(
        Examination.date == today
    ).scalar()

    # Monthly examinations data
    current_year = today.year
    examinations_by_month = db.session.query(
        extract('month', Examination.date).label('month'),
        func.count(Examination.examination_id).label('count')
    ).filter(
        extract('year', Examination.date) == current_year
    ).group_by(
        extract('month', Examination.date)
    ).order_by(extract('month', Examination.date)).all()

    monthly_examinations_data = {int(month): float(count) for month, count in examinations_by_month}

    # Query for examinations data
    query = text('SELECT * FROM examination')
    result = db.session.execute(query)
    examinations = result.fetchall()

    return render_template(
        "admin.html",
        user=current_user,
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_examinations=total_examinations,
        active_patients=active_patients,
        examinations=examinations,
        monthly_examinations_data=monthly_examinations_data,
        today=today
    )

@views.route('/check-doc', methods=['GET'])
@login_required
def check_doc():
    result = db.session.execute(text(
        """
        SELECT 
            "user"."user_id", 
            "user"."name", 
            "user"."dob", 
            "user"."sex", 
            "user"."phone", 
            "user"."address", 
            "doctor"."department_id", 
            "department"."department_name"
        FROM 
            "user"
        JOIN 
            "doctor" ON "user"."user_id" = "doctor"."user_id"
        JOIN 
            "department" ON "doctor"."department_id" = "department"."department_id"
        """
    ))

    columns = result.keys()
    rows = result.fetchall()
    doctors = [dict(zip(columns, row)) for row in rows]

    return render_template(
        "checkDoc.html",
        doctors=doctors,
        today=date.today()
    )

@views.route('/check-patient', methods=['GET'])
@login_required
def check_patient():
    result = db.session.execute(text(
        """
        SELECT 
            "user"."user_id", 
            "user"."name", 
            "user"."dob", 
            "user"."sex", 
            "user"."phone", 
            "user"."address"
        FROM 
            "user"
        JOIN 
            "patient" ON "user"."user_id" = "patient"."user_id"
        """
    ))

    columns = result.keys()
    rows = result.fetchall()
    patients = [dict(zip(columns, row)) for row in rows]

    return render_template(
        "checkPatient.html",
        patients=patients,
        today=date.today()
    )

@views.route('/payment', methods=['GET'])
@login_required
def payment():
    target_year = 2022
    months = [f"{i:02d}" for i in range(1, 13)]

    salary_dict = {month: 0 for month in months}
    revenue_dict = {month: 0 for month in months}

    for month in months:
        # Lấy danh sách các bác sĩ trong tháng
        doctors_in_month = db.session.query(Examination.doctor_id).filter(
            func.to_char(Examination.date, 'YYYY-MM') == f'{target_year}-{month}'
        ).distinct().subquery()

        # Tính lương của bác sĩ trong tháng
        monthly_salary = db.session.query(
            func.sum(Doctor.salary).label('monthly_salary')
        ).filter(
            Doctor.user_id.in_(doctors_in_month)
        ).scalar() or 0

        salary_dict[month] = monthly_salary / 10

        # Tính doanh thu trong tháng
        monthly_revenue = db.session.query(
            func.sum(Examination.fee).label('monthly_revenue')
        ).filter(
            func.to_char(Examination.date, 'YYYY-MM') == f'{target_year}-{month}'
        ).scalar() or 0

        revenue_dict[month] = monthly_revenue

    profit_loss_data = [
        revenue_dict[month] - salary_dict[month] for month in months
    ]

    return render_template(
        "payment.html",
        today=date.today(),
        total_salary=sum(salary_dict.values()) or 0,
        total_revenue=sum(revenue_dict.values()) or 0,
        months=months,
        salary_data=[salary_dict[month] for month in months],
        revenue_data=[revenue_dict[month] for month in months],
        profit_loss_data=profit_loss_data
    )

#------------------------------- Make Examination -------------------------------
@views.route('/make_examination')
def make_examination():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('auth.make_examination', user_id=current_user.user_id))

#------------------------------- Notification -------------------------------
@views.route('/notifications')
@login_required
def notifications_patient():
    # Lấy danh sách các cuộc khám bệnh sắp tới từ current_user
    upcoming_examinations = current_user.get_upcoming_examinations()

    # Lấy ngày hiện tại dưới dạng đối tượng datetime.date
    today = datetime.now().date()

    # Lọc các cuộc khám bệnh có ngày khám chưa đến
    upcoming_examinations_filtered = [
        {
            'date': examination.date.strftime('%d/%m/%Y'),
            'doctor': examination.doctor.user.name,
            'department': examination.doctor.department.department_name,
        }
        for examination in upcoming_examinations
        if examination.date >= today
    ]

    return jsonify(upcoming_examinations_filtered)

@views.route('/notifications_doctor')
@login_required
def notifications_doctor():
    # Lấy danh sách các cuộc khám bệnh sắp tới của bác sĩ hiện tại
    upcoming_examinations = current_user.get_upcoming_examinations_for_doctor()

    # Lấy ngày hiện tại dưới dạng đối tượng datetime.date
    today = datetime.now().date()

    # Lọc các cuộc khám bệnh có ngày khám chưa đến
    upcoming_examinations_filtered = [
        {
            'date': examination.date.strftime('%d/%m/%Y'),
            'patient': examination.patient.user.name,
        }
        for examination in upcoming_examinations
        if examination.date >= today
    ]

    return jsonify(upcoming_examinations_filtered)

@views.route('/doctor', methods=['GET', 'POST'])
@login_required
def doctor():
    departments = Department.query.all()
    selected_department_ids = request.form.getlist('department')
    if selected_department_ids:
        doctors = Doctor.query.filter(Doctor.department_id.in_(selected_department_ids)).all()
    else:
        doctors = []
    return render_template('doctor.html', departments=departments, doctors=doctors)

