import hashlib
import shutil
from flask import Flask, request, redirect, url_for, send_file, render_template, session, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import os
from flask import make_response
import zipfile
import fitz
import mysql.connector
from docx import Document


UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\danna\Dropbox\ProyectoBethaTeam'
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.secret_key = 'secret_key'  # Clave secreta para firmar las sesiones

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

def create_connection():
    conn = None
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # No se requiere contraseña para el usuario root
            database="proyecto"  # Nombre de tu base de datos
        )
        print('Conexión a la base de datos establecida.')
    except mysql.connector.Error as e:
        print(f'Error al conectar a la base de datos: {e}')
    return conn

def login_user(conn, username, password):
    sql = '''
    SELECT * FROM users WHERE username = %s;
    '''
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (username,))
        result = cursor.fetchone()
        if result:
            stored_password = result[3]
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password == stored_password:
                print('Inicio de sesión exitoso.')
                return True
            else:
                print('Credenciales inválidas.')
                return False
        else:
            print('Credenciales inválidas.')
            return False
    except mysql.connector.Error as e:
        print(f'Error al iniciar sesión: {e}')
        return False


def register_user(conn, username, email, password, confirm_password):
    if password != confirm_password:
        print("Las contraseñas no coinciden.")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar si el usuario ya existe en la base de datos (por nombre de usuario o correo electrónico)
        sql = "SELECT * FROM users WHERE username = %s OR email = %s"
        cursor.execute(sql, (username, email))
        result = cursor.fetchone()
        if result:
            if result[1] == username:
                print("El nombre de usuario ya está registrado.")
            elif result[2] == email:
                print("El correo electrónico ya está registrado.")
            return False

        # Registrar al usuario en la base de datos
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        sql = "INSERT INTO users (username, email, password, confirm_password) VALUES (%s, %s, %s, %s)"
        values = (username, email, hashed_password, confirm_password)
        cursor.execute(sql, values)
        conn.commit()
        print('Usuario registrado exitosamente.')
        return True
    
    except mysql.connector.Error as e:
        print(f'Error al registrar el usuario: {e}')
        return False
    

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = create_connection()
        username = request.form['username']
        password = request.form['password']
        if login_user(conn, username, password):
            # Iniciar sesión almacenando el nombre de usuario en la sesión
            session['username'] = username
            conn.close()
            return redirect(url_for('upload_file'))
        else:
            conn.close()
            return render_template('login.html', error_message="Credenciales inválidas.")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = create_connection()
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Verificar si el usuario ya existe en la base de datos
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        result = cursor.fetchone()
        if result:
            if result[1] == username:
                return render_template('register.html', error_message="El nombre de usuario ya está registrado.")
            elif result[2] == email:
                return render_template('register.html', error_message="El correo electrónico ya está registrado.")

        # Registrar al usuario en la base de datos
        success = register_user(conn, username, email, password, confirm_password)
        conn.close()

        if success:
            # Iniciar sesión automáticamente después del registro
            session['username'] = username
            return redirect(url_for('upload_file'))
        else:
            return render_template('register.html', error_message="Error al registrar el usuario.")

    return render_template('register.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))

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

            # Save the original PDF or convert the image to PDF with the custom name
            pdf_output_path = os.path.join(app.config['OUTPUT_FOLDER'], custom_pdf_filename)
            if file_extension == 'pdf':
                shutil.copyfile(filepath, pdf_output_path)
            else:
                images = [filepath]
                pdf = fitz.open()
                for image in images:
                    img = fitz.open(image)
                    pdf.insert_pdf(img)
                pdf.save(pdf_output_path)
                pdf.close()

            # Create a zip file with the text and PDF files
            zip_filename = generate_filename(name, doc_type, date, "zip")
            zip_output_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
            with zipfile.ZipFile(zip_output_path, 'w') as zipf:
                zipf.write(txt_output_path, custom_txt_filename)
                zipf.write(pdf_output_path, custom_pdf_filename)

            # Return the download link for the zip file
            return send_from_directory(app.config['OUTPUT_FOLDER'], zip_filename, as_attachment=True)

    return render_template('upload.html')



@app.route('/about', methods=['GET'])
def about():
    about_template = render_template('about.html')
    return about_template

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


def process_doc(filepath):
    doc = Document(filepath)
    text = ''
    for paragraph in doc.paragraphs:
        text += paragraph.text + '\n'
    return text


def process_image(filepath):
    try:
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image, lang="eng")
        return text
    except IOError:
        print("Error al procesar la imagen.")
        return ""



def process_pdf(filepath):
    pdf = fitz.open(filepath)
    text = ""
    for page in pdf:
        text += page.get_text("text")
    pdf.close()
    return text


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)