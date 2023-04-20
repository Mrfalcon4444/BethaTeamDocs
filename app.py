import img2pdf
import shutil
from flask import Flask, request, redirect, url_for, send_file, render_template_string
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

nav_bar = '''
<nav>
    <img src="{{ url_for('static', filename='logo.jpg') }}" alt="Logo" style="width: 50px; height: auto; margin-right: 20px;">
    <a href="{{ url_for('home') }}">Inicio</a>
    <a href="{{ url_for('upload_file') }}">Conversor</a>
    <a href="{{ url_for('about') }}">Acerca de</a>
</nav>
'''

styles = '''
<style>
    body {
        font-family: Arial, sans-serif;
        background-color: #f0f2f5;
    }
    nav {
        background-color: #007bff;
        padding: 10px;
        display: flex;
        justify-content: space-around;
    }
    nav a {
        color: white;
        text-decoration: none;
        font-size: 18px;
    }
    nav a:hover {
        text-decoration: underline;
    }
    h1 {
        text-align: center;
        margin-bottom: 30px;
    }
    form {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    label, input[type="file"] {
        margin-bottom: 15px;
    }
    input[type="submit"] {
        background-color: #007bff;
        color: white;
        padding: 10px;
        font-size: 16px;
        border: none;
        cursor: pointer;
    }
    input[type="submit"]:hover {
        background-color: #0056b3;
    }
    ul {
        list-style-type: none;
    }
    li {
        margin-bottom: 10px;
    }
</style>
'''

@app.route('/', methods=['GET'])
def home():
    home_template = '''
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>Inicio - Conversor de documentos</title>
        ''' + styles + '''
      </head>
      <body>
        ''' + nav_bar + '''
        <h1>¡Bienvenido a la aplicación de administración de archivos personales en la nube de Betha Team!</h1>
        <p>¿Estás cansado de perder tiempo buscando documentos importantes en tu computadora o en una pila de papeles? ¿Te gustaría tener acceso a todos tus archivos personales desde cualquier lugar y en cualquier momento? ¡Entonces nuestra aplicación es la solución para ti!</p>
        <p>Nuestra aplicación realiza un OCR y convierte imágenes en PDF para que puedas organizar tus archivos de manera rápida y sencilla. Además, modificamos los nombres de los archivos para que sean útiles y fáciles de encontrar. Y para ahorrar espacio, todos los documentos generados se pasan a un archivo ZIP. De esta manera podras subir tus archivos al servicio de nube de tu preferencia y tener todo debidamente organizado, manteniendo tu tus archivos faciles de encontrar a la vez que ahorras espacio y dinero.</p>
        <p> La administración de archivos personales nunca ha sido tan fácil. ¡Únete a nuestra aplicación hoy mismo y comienza a tener control total sobre tus archivos personales!</p>
      </body>
    </html>
    '''
    return render_template_string(home_template)

@app.route('/upload', methods=['GET', 'POST'])
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

    upload_template = '''
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>Conversor de documentos</title>
        ''' + styles + '''
      </head>
      <body>
        ''' + nav_bar + '''
        <h1>Subir archivo PDF o imagen</h1>
        <form method=post enctype=multipart/form-data>
          <label for=name>Nombre:</label>
          <input type=text name=name required>
          <br>
          <label for=doc_type>Tipo de documento:</label>
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
      </body>
    </html>
    '''
    return render_template_string(upload_template)

@app.route('/about', methods=['GET'])
def about():
    about_template = '''
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>Acerca de</title>
        ''' + styles + '''
      </head>
      <body>
        ''' + nav_bar + '''
        <h1>Acerca de</h1>
        <p>Equipo:</p>
        <ul>
          <li>Miembro del equipo 1</li>
          <li>Miembro del equipo 2</li>
          <li>Miembro del equipo 3</li>
          <li>Miembro del equipo 4</li>
        </ul>
      </body>
    </html>
    '''
    return render_template_string(about_template)

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


