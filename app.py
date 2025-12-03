import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename

from report_generator import generate_pdf_report

# Config
UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"
ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["REPORT_FOLDER"] = REPORT_FOLDER
app.secret_key = "supersecretkey"  # for flash messages


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part in the request")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            csv_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(csv_path)

            # Generate report
            report_name = f"{os.path.splitext(filename)[0]}_report.pdf"
            report_path = os.path.join(app.config["REPORT_FOLDER"], report_name)

            generate_pdf_report(csv_path, report_path)

            # Send the file to user for download
            return send_file(report_path, as_attachment=True)

        else:
            flash("Invalid file type. Please upload a .csv file.")
            return redirect(request.url)

    return render_template("index.html")


if __name__ == "__main__":
    # debug=True is nice while developing
    app.run(host="0.0.0.0", port=5000, debug=True)
