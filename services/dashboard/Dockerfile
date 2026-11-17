# Separate build stage: on platforms without a prebuilt wheel (e.g.
# linux/arm/v7), pip compiles deps like cryptography (via Authlib), cffi,
# and greenlet (via SQLAlchemy) from source. That needs a full C/C++
# toolchain (gcc, g++, libc headers/crt objects), libatomic.so.1, and
# libffi's headers (cffi's extension is built against libffi) -- none of
# which are in the base image. build-essential pulls in gcc/g++/make/
# libc6-dev together; installing them in their own stage keeps the
# toolchain out of the runtime image.
#
# Docker Hardened Image (DHI): the -dev variant has apt/a shell; the
# runtime stage below uses the non-dev variant, which is minimal,
# nonroot-by-default, and has neither -- so it can't apt-get install
# libpq5 itself. Instead, libpq5 and its runtime shared-library
# dependencies are resolved by apt here and copied into the runtime
# stage below. Both variants require `docker login dhi.io` to pull --
# see .github/workflows/create-docker-on-release.yml.
#
# DHI's python image has no linux/arm/v7 build, so the CI workflow
# overrides these to python:3.14-slim for that platform only -- the
# libpq copy step below still runs (and still works) on that image too.
ARG BUILDER_IMAGE=dhi.io/python:3.14-dev
ARG RUNTIME_IMAGE=dhi.io/python:3.14

FROM ${BUILDER_IMAGE} AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libatomic1 libffi-dev libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && libdir="$(dpkg -L libpq5 | grep -m1 -oE '^/usr/lib/[^/]+')" \
    && mkdir -p "/libpq-deps${libdir}" \
    && for pkg in libpq5 libssl3t64 libgssapi-krb5-2 libldap2 libsasl2-2 \
                  libkrb5-3 libk5crypto3 libkrb5support0 libcom-err2 libkeyutils1; do \
         dpkg -L "$pkg" | grep -E "^${libdir}/lib[^/]+\.so(\.[0-9]+)*\$"; \
       done | xargs cp -a --target-directory="/libpq-deps${libdir}"

# Under QEMU emulation (arm/v7 builds), rustc's multi-threaded codegen
# backend can deadlock -- a known qemu-user-static bug. Force a
# single-threaded Rust build so it stays slow but finite instead of
# hanging indefinitely. No effect on platforms with a prebuilt wheel.
ENV CARGO_BUILD_JOBS=1
ENV RUSTFLAGS="-C codegen-units=1"

# A venv rather than `pip install --prefix=/install` + copying that prefix
# into the runtime stage's /usr/local: DHI's python installs under /usr,
# not /usr/local (unlike the official python:*-slim images, which build
# CPython with --prefix=/usr/local), so a copied /install prefix silently
# isn't on sys.path there. A venv's own site-packages is found regardless
# of where the base image's interpreter lives, as long as its bin/ is
# first on PATH -- set below in the runtime stage. --copies (rather than
# the platform-default symlinks) so /opt/venv/bin/python doesn't depend on
# resolving a symlink back into this (discarded) builder stage.
RUN python -m venv --copies /opt/venv

COPY services/dashboard/requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir --require-hashes -r requirements.txt

FROM ${RUNTIME_IMAGE}

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# libpq5 (needed by psycopg, which talks to Postgres via ctypes) plus
# the shared libraries it links against -- see the builder stage above,
# which resolved this set via apt since this runtime image has no
# package manager of its own.
COPY --from=builder /libpq-deps/ /

COPY --from=builder /opt/venv /opt/venv

COPY services/shared/ /shared/
COPY services/dashboard/ .

EXPOSE 5000

# No curl/wget in the slim image -- use python's stdlib instead so the
# healthcheck doesn't need an extra apt-get install. Longer start-period
# than the api service to cover init_db.py running before gunicorn is up.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz', timeout=2)"]

CMD ["python", "docker-entrypoint.py"]
