FROM python:3.12-slim@sha256:0000000000000000000000000000000000000000000000000000000000000000
RUN useradd --create-home --uid 10001 app
WORKDIR /home/app
COPY --chown=app:app app.py .
USER 10001
CMD ["python", "app.py"]
