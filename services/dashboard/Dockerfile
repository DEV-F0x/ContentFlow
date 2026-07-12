FROM python:3.14-slim

WORKDIR /app

COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared/ /shared/
COPY services/dashboard/ .

EXPOSE 5000

CMD python init_db.py && exec gunicorn -b 0.0.0.0:5000 -w 2 run:app
