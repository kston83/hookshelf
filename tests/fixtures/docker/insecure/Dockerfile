# Intentionally insecure Dockerfile: checkov and hadolint should report findings.
FROM ubuntu:latest
ADD https://example.com/install.sh /tmp/install.sh
RUN apt-get update && apt-get install -y curl
RUN sudo chmod +x /tmp/install.sh
EXPOSE 22
