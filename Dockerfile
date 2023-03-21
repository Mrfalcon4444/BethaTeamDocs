FROM python:3.8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
    apt-get install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/bin:${PATH}"

RUN ln -s /usr/bin/pdfinfo /usr/local/bin/pdfinfo

COPY . .

CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:5000", "app:app"]





