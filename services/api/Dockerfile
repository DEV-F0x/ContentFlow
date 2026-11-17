# Docker Hardened Image (DHI): the -dev variant has apt/a shell for
# installing packages; the runtime stage below uses the non-dev variant,
# which is minimal, nonroot-by-default, and has neither. Both require
# `docker login dhi.io` to pull -- see .github/workflows/create-docker-on-release.yml.
#
# DHI's python image has no linux/arm/v7 build, so the CI workflow
# overrides these to python:3.14-slim for that platform only.
ARG BUILDER_IMAGE=dhi.io/python:3.14-dev
ARG RUNTIME_IMAGE=dhi.io/python:3.14

FROM ${BUILDER_IMAGE} AS builder

ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

COPY services/api/requirements.txt .
RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt

FROM ${RUNTIME_IMAGE}

ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

COPY --from=builder /install /usr/local

COPY services/shared/ /shared/
COPY services/api/ .

EXPOSE 5000

# No curl/wget in the slim image -- use python's stdlib instead so the
# healthcheck doesn't need an extra apt-get install.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz', timeout=2)"]

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--threads", "4", \
     "--worker-class", "gthread", "run:app"]
