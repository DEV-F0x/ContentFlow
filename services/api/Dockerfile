FROM python:3.14-slim

WORKDIR /app

COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared/ /shared/
COPY services/api/ .

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--threads", "4", \
     "--worker-class", "gthread", "run:app"]
