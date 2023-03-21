from flask import Flask, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import os
from flask import make_response

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'pdf':
                text = process_pdf(filepath)
            else:
                text = process_image(filepath)

            response = make_response(text)
            response.headers.set('Content-Type', 'text/plain')
            response.headers.set('Content-Disposition', 'attachment', filename='result.txt')
            return response
    return '''
<!doctype html>
<title>Upload PDF or Image File</title>
<h1>Upload PDF or Image File</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Upload>
</form>
'''

def process_image(filepath):
    image = Image.open(filepath)
    text = pytesseract.image_to_string(image, lang="eng")
    return text

def process_pdf(filepath):
    text = ""
    images = convert_from_path(filepath, poppler_path='/usr/bin')
    #images = convert_from_path(filepath, pdfinfo_path='/usr/bin/pdfinfo')
    #images = convert_from_path(filepath)
    for image in images:
        text += pytesseract.image_to_string(image, lang="eng")
    return text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    #app.run(debug=True)
