FROM python:3.14-slim

WORKDIR /app

COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared/ /shared/
COPY services/api/ .

EXPOSE 5000

# No curl/wget in the slim image -- use python's stdlib instead so the
# healthcheck doesn't need an extra apt-get install.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz', timeout=2)"

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--threads", "4", \
     "--worker-class", "gthread", "run:app"]
