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
import io
import fitz
from docx import Document
import firebase_admin
import datetime
from firebase_admin import credentials, storage, firestore
import uuid

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

def initialize_firestore():
    # Inicializar Firebase usando el archivo JSON de configuración
    cred = credentials.Certificate("bethateam-b77e0-firebase-adminsdk-yz1cz-bddd759545.json")
    firebase_admin.initialize_app(cred, {'storageBucket': 'bethateam-b77e0.appspot.com'})
    print("Firebase inicializado correctamente.")


def login_user(username, password):
    # Realizar la lógica de inicio de sesión utilizando Firestore
    users_ref = firestore.client().collection('users')
    query = users_ref.where('username', '==', username).limit(1)
    result = query.stream()

    for doc in result:
        stored_password = doc.to_dict().get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if hashed_password == stored_password:
            print('Inicio de sesión exitoso.')
            return True

    print('Credenciales inválidas.')
    return False

def register_user(username, email, password, confirm_password):
    # Realizar la lógica de registro de usuarios utilizando Firestore
    users_ref = firestore.client().collection('users')
    query = users_ref.where('username', '==', username).limit(1)
    result = query.stream()

    if len(list(result)) > 0:
        print("El nombre de usuario ya está registrado.")
        return False

    user_data = {
        'username': username,
        'email': email,
        'password': hashlib.sha256(password.encode()).hexdigest(),
        'confirm_password': confirm_password
    }
    users_ref.document(str(uuid.uuid4())).set(user_data)
    print('Usuario registrado exitosamente.')
    return True

from werkzeug.utils import secure_filename
from firebase_admin import storage as firebase_storage

def upload():
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

            # Subir el archivo directamente a Firebase Storage
            firebase_filename = generate_filename(name, doc_type, date, "pdf")
            bucket = firebase_storage.bucket()
            blob = bucket.blob(firebase_filename)
            blob.upload_from_file(file.stream, content_type=file.content_type)

            # Obtener detalles del archivo subido
            file_size = file.content_length
            upload_date = datetime.datetime.now()

            # Guardar detalles del archivo en Firestore
            file_data = {
                'filename': firebase_filename,
                'name': name,
                'doc_type': doc_type,
                'date': date,
                'size': file_size,
                'upload_date': upload_date
            }
            # Asumiendo que tienes una colección 'files' en Firestore
            files_ref = firestore.client().collection('files')
            files_ref.add(file_data)

            return redirect(url_for('home'))

    return render_template('upload.html')




@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if login_user(username, password):
            # Iniciar sesión almacenando el nombre de usuario en la sesión
            session['username'] = username
            return redirect(url_for('upload_file'))
        else:
            return render_template('login.html', error_message="Credenciales inválidas.")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Verificar si el usuario ya existe en la base de datos
        users_ref = firestore.client().collection('users')
        query = users_ref.where('username', '==', username).limit(1)
        result = query.stream()

        if len(list(result)) > 0:
            return render_template('register.html', error_message="El nombre de usuario ya está registrado.")

        # Verificar si las contraseñas coinciden
        if password != confirm_password:
            return render_template('register.html', error_message="Las contraseñas no coinciden. Por favor, inténtalo de nuevo.")

        # Registrar al usuario en la base de datos
        user_data = {
            'username': username,
            'email': email,
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'confirm_password': confirm_password
        }
        users_ref.document(str(uuid.uuid4())).set(user_data)

        # Iniciar sesión automáticamente después del registro
        session['username'] = username

        return redirect(url_for('upload_file'))

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

            # Subir el archivo directamente a Firebase Storage
            firebase_filename = generate_filename(name, doc_type, date, "pdf")
            bucket = firebase_storage.bucket()
            blob = bucket.blob(firebase_filename)
            blob.upload_from_file(file.stream, content_type=file.content_type)

            # Obtener detalles del archivo subido
            file_size = file.content_length
            upload_date = datetime.datetime.now()

            # Guardar detalles del archivo en Firestore
            file_data = {
                'filename': firebase_filename,
                'name': name,
                'doc_type': doc_type,
                'date': date,
                'size': file_size,
                'upload_date': upload_date,
                'username': session['username']  # Agrega el nombre de usuario desde la sesión
            }
            # Asumiendo que tienes una colección 'files' en Firestore
            files_ref = firestore.client().collection('files')
            files_ref.add(file_data)


            return redirect(url_for('home'))

    return render_template('upload.html')



@app.route('/archivos')
def archivos():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Obtén los archivos del usuario actual desde Firestore
    files_ref = firestore.client().collection('files')
    files_query = files_ref.where('username', '==', session['username']).get()
    files = []

    for file_doc in files_query:
        file_data = file_doc.to_dict()
        file_data['id'] = file_doc.id
        files.append(file_data)

    return render_template('files.html', files=files)


@app.route('/download/<id>', methods=['GET'])
def download_file(id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Verificar si el archivo existe y pertenece al usuario actual
    file_ref = firestore.client().collection('files').document(id)
    file_data = file_ref.get().to_dict()
    if not file_data or file_data['username'] != session['username']:
        return "Error: El archivo no existe o no pertenece al usuario actual."

    # Obtener referencia al archivo en Storage
    storage_bucket = storage.bucket()
    blob = storage_bucket.blob(file_data['filename'])

    # Descargar el archivo desde Storage
    file_content = io.BytesIO()
    blob.download_to_file(file_content)
    file_content.seek(0)

    # Crear una respuesta para devolver el archivo al cliente
    response = send_file(file_content, download_name=file_data['filename'])
    response.headers['Content-Length'] = str(blob.size)

    return response


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
    initialize_firestore()

    app.run(host='0.0.0.0', port=5000, debug=True)