import img2pdf
import shutil
from flask import Flask, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import os
from flask import make_response
import zipfile

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Crear el directorio de salida si no existe
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_filename(name, doc_type, date, extension):
    name_part = name[:3].lower()
    doc_type_part = doc_type[:3].lower()
    date_part = date.replace("-", "")
    return f"{name_part}_{doc_type_part}_{date_part}.{extension}"

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            name = request.form['name']
            doc_type = request.form['doc_type']
            date = request.form['date']
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'pdf':
                text = process_pdf(filepath)
            else:
                text = process_image(filepath)

            custom_txt_filename = generate_filename(name, doc_type, date, "txt")
            custom_pdf_filename = generate_filename(name, doc_type, date, "pdf")

            # Save the text file
            txt_output_path = os.path.join(app.config['OUTPUT_FOLDER'], custom_txt_filename)
            with open(txt_output_path, 'w') as txt_file:
                txt_file.write(text)

            # Save the original PDF or converted image to PDF with the custom name
            pdf_output_path = os.path.join(app.config['OUTPUT_FOLDER'], custom_pdf_filename)
            if file_extension == 'pdf':
                shutil.copyfile(filepath, pdf_output_path)
            else:
                with open(pdf_output_path, "wb") as f:
                    img_data = img2pdf.convert(filepath)
                    f.write(img_data)

            # Create a zip file with the text and PDF files
            zip_filename = generate_filename(name, doc_type, date, "zip")
            zip_output_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
            with zipfile.ZipFile(zip_output_path, 'w') as zipf:
                zipf.write(txt_output_path, custom_txt_filename)
                zipf.write(pdf_output_path, custom_pdf_filename)

            # Return the download link for the zip file
            return send_file(zip_output_path, as_attachment=True, download_name=zip_filename)
    return '''
    <!doctype html>
    <title>Subir archivo PDF o imagen</title>
    <h1>Subir archivo PDF o imagen</h1>
    <form method=post enctype=multipart/form-data>
      <label for=name>Nombre:</label>
      <input type=text name=name required>
      <br>
      <label for=doc_type>Tipo      de documento:</label>
      <input type=text name=doc_type required>
      <br>
      <label for=date>Fecha:</label>
      <input type=date name=date required>
      <br>
      <label for=file>Archivo:</label>
      <input type=file name=file>
      <br>
      <input type=submit value=Subir>
    </form>
    '''

def process_image(filepath):
    image = Image.open(filepath)
    text = pytesseract.image_to_string(image, lang="eng")
    return text

def process_pdf(filepath):
    poppler_path = "/usr/bin"  # Suponiendo que las utilidades de Poppler están instaladas en /usr/bin
    images = convert_from_path(filepath)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image, lang="eng")
    return text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    #app.run(debug=True)

