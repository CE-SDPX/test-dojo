# Built from source instead of pulling coleifer/sqlite-web: that image is
# published amd64-only, so on an Apple Silicon (arm64) host Docker runs it
# under QEMU emulation, and its dev server has been observed to hang on
# every HTTP request there (confirmed even from localhost inside its own
# container) even though SQLite access itself is instant. Building from
# python:3.12-slim (already multi-arch, same as app/Dockerfile) compiles
# natively for whatever host runs it — Mac (Intel or Apple Silicon),
# Windows or Linux — with no emulation involved.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 TZ=Asia/Bangkok

RUN pip install --no-cache-dir sqlite-web==0.8.2

EXPOSE 8080

ENTRYPOINT ["sqlite_web", "--host", "0.0.0.0"]
