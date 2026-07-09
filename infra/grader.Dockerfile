# Sandbox image for lab grading (GRADER_MODE=docker).
# Build:  docker build -f infra/grader.Dockerfile -t mo-academy-grader .
# The grader runs it with --network=none, memory/cpu/pid limits, and the
# submission mounted read-write at /grade.
FROM python:3.12-slim

COPY packages/mo_teach/ /opt/mo_teach/
RUN pip install --no-cache-dir /opt/mo_teach && \
    useradd --no-create-home grader
USER grader
