from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import func
from reportlab.pdfgen import canvas
import openpyxl
import os
import random
import io

app = Flask(__name__)
app.secret_key = "kikym_secret_key"

# -------------------------
# ADMIN LOGIN
# -------------------------

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# -------------------------
# DATABASE CONFIG
# -------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["UPLOAD_PHOTO"] = "uploads/photos"
app.config["UPLOAD_AADHAR"] = "uploads/aadhar"

db = SQLAlchemy(app)

os.makedirs(app.config["UPLOAD_PHOTO"], exist_ok=True)
os.makedirs(app.config["UPLOAD_AADHAR"], exist_ok=True)

# -------------------------
# DATABASE TABLES
# -------------------------

class Applicant(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(20))

    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    mobile = db.Column(db.String(20))

    course = db.Column(db.String(100))
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))

    photo = db.Column(db.String(200))
    aadhar = db.Column(db.String(200))

    status = db.Column(db.String(50), default="Pending")
    placement = db.Column(db.String(50), default="Not Placed")


class Course(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))


# -------------------------
# APPLICATION ID GENERATOR
# -------------------------

def generate_app_id():
    number = random.randint(10000,99999)
    return f"KIKYM2026{number}"


# -------------------------
# HOME PAGE
# -------------------------

@app.route("/")
def home():

    courses = Course.query.all()
    total_applicants = Applicant.query.count()

    announcements = [
        {"title":"New IT Skills Batch Starting Soon"},
        {"title":"Last Date to Apply: 30 June"},
        {"title":"Free Training for Eligible Candidates"}
    ]

    return render_template(
        "index.html",
        courses=courses,
        total_applicants=total_applicants,
        announcements=announcements
    )


# -------------------------
# COURSES PAGE
# -------------------------

@app.route("/courses")
def courses():

    courses = Course.query.all()
    return render_template("courses.html", courses=courses)


# -------------------------
# ADMIN LOGIN
# -------------------------

@app.route("/admin-login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")

    return render_template("admin_login.html")


# -------------------------
# ADMIN LOGOUT
# -------------------------

@app.route("/admin-logout")
def admin_logout():

    session.pop("admin", None)
    return redirect("/")


# -------------------------
# APPLY FORM
# -------------------------

@app.route("/apply", methods=["GET","POST"])
def apply():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]

        course = request.form["course"]
        district = request.form["district"]
        state = request.form["state"]

        photo = request.files["photo"]
        aadhar = request.files["aadhar"]

        photo_name = secure_filename(photo.filename)
        aadhar_name = secure_filename(aadhar.filename)

        photo.save(os.path.join(app.config["UPLOAD_PHOTO"], photo_name))
        aadhar.save(os.path.join(app.config["UPLOAD_AADHAR"], aadhar_name))

        app_id = generate_app_id()

        applicant = Applicant(
            app_id=app_id,
            name=name,
            email=email,
            mobile=mobile,
            course=course,
            district=district,
            state=state,
            photo=photo_name,
            aadhar=aadhar_name
        )

        db.session.add(applicant)
        db.session.commit()

        return redirect(url_for("success", id=applicant.id))

    courses = Course.query.all()

    return render_template("apply.html", courses=courses)


# -------------------------
# SUCCESS PAGE
# -------------------------

@app.route("/success/<int:id>")
def success(id):

    applicant = Applicant.query.get(id)
    return render_template("success.html", applicant=applicant)


# -------------------------
# DOWNLOAD APPLICATION PDF
# -------------------------

@app.route("/download/<int:id>")
def download(id):

    applicant = Applicant.query.get_or_404(id)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.drawString(200,800,"K-IKYM APPLICATION")

    pdf.drawString(100,750,f"Application ID : {applicant.app_id}")
    pdf.drawString(100,720,f"Name : {applicant.name}")
    pdf.drawString(100,690,f"Email : {applicant.email}")
    pdf.drawString(100,660,f"Mobile : {applicant.mobile}")
    pdf.drawString(100,630,f"Course : {applicant.course}")
    pdf.drawString(100,600,f"District : {applicant.district}")
    pdf.drawString(100,570,f"State : {applicant.state}")
    pdf.drawString(100,540,f"Status : {applicant.status}")
    pdf.drawString(100,510,f"Placement : {applicant.placement}")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{applicant.app_id}.pdf",
        mimetype="application/pdf"
    )


# -------------------------
# SERVE UPLOADED FILES
# -------------------------

@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):

    return send_from_directory(f'uploads/{folder}', filename)


# -------------------------
# TRACK APPLICATION
# -------------------------

@app.route("/track/<int:id>")
def track(id):

    applicant = Applicant.query.get(id)
    return render_template("track.html", applicant=applicant)


# -------------------------
# SEARCH APPLICATION
# -------------------------

@app.route("/search", methods=["GET","POST"])
def search():

    if request.method == "POST":

        app_id = request.form["app_id"]
        applicant = Applicant.query.filter_by(app_id=app_id).first()

        if applicant:
            return redirect(url_for("track", id=applicant.id))

    return render_template("search.html")


# -------------------------
# ADMIN DASHBOARD
# -------------------------

@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/admin-login")

    applicants = Applicant.query.all()

    return render_template("admin.html", applicants=applicants)


# -------------------------
# EXPORT EXCEL
# -------------------------

@app.route("/export-excel")
def export_excel():

    applicants = Applicant.query.all()

    workbook = openpyxl.Workbook()
    sheet = workbook.active

    sheet.append([
        "Application ID","Name","Email","Mobile",
        "Course","District","State","Status","Placement"
    ])

    for a in applicants:
        sheet.append([
            a.app_id,
            a.name,
            a.email,
            a.mobile,
            a.course,
            a.district,
            a.state,
            a.status,
            a.placement
        ])

    filename = "applicants.xlsx"
    workbook.save(filename)

    return send_file(filename, as_attachment=True)


# -------------------------
# APPROVE / REJECT / PLACE
# -------------------------

@app.route("/approve/<int:id>")
def approve(id):

    applicant = Applicant.query.get(id)
    applicant.status = "Approved"
    db.session.commit()

    return redirect("/admin")


@app.route("/reject/<int:id>")
def reject(id):

    applicant = Applicant.query.get(id)
    applicant.status = "Rejected"
    db.session.commit()

    return redirect("/admin")


@app.route("/place/<int:id>")
def place(id):

    applicant = Applicant.query.get(id)
    applicant.placement = "Placed"
    db.session.commit()

    return redirect("/admin")


# -------------------------
# START SERVER
# -------------------------

if __name__=="__main__":

    with app.app_context():

        db.create_all()

        if Course.query.count()==0:

            courses=[
            "IT Skills","Python Programming","Web Development",
            "Data Science","Cyber Security","Cloud Computing",
            "Mobile App Development","Digital Marketing",
            "Graphic Design","UI UX Design","Electrical Technician",
            "Automobile Technician","Healthcare Assistant",
            "Nursing Assistant","Fashion Design","Hotel Management"
            ]

            for c in courses:
                db.session.add(Course(name=c))

            db.session.commit()

    app.run(debug=True)
