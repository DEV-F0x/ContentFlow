# Separate build stage: on platforms without a prebuilt wheel (e.g.
# linux/arm/v7), pip compiles deps like cryptography (via Authlib), cffi,
# and greenlet (via SQLAlchemy) from source. That needs a full C/C++
# toolchain (gcc, g++, libc headers/crt objects), libatomic.so.1, and
# libffi's headers (cffi's extension is built against libffi) -- none of
# which are in the slim base image. build-essential pulls in
# gcc/g++/make/libc6-dev together; installing them in their own stage
# keeps the toolchain out of the runtime image.
FROM python:3.14-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libatomic1 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Under QEMU emulation (arm/v7 builds), rustc's multi-threaded codegen
# backend can deadlock -- a known qemu-user-static bug. Force a
# single-threaded Rust build so it stays slow but finite instead of
# hanging indefinitely. No effect on platforms with a prebuilt wheel.
ENV CARGO_BUILD_JOBS=1
ENV RUSTFLAGS="-C codegen-units=1"

COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.14-slim

WORKDIR /app

# psycopg (no [binary] extra) talks to Postgres via ctypes, loading the
# system libpq.so at runtime instead of bundling a precompiled driver --
# needed since no psycopg-binary wheel exists for platforms like arm/v7.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY services/shared/ /shared/
COPY services/dashboard/ .

EXPOSE 5000

CMD python init_db.py && exec gunicorn -b 0.0.0.0:5000 -w 2 run:app
