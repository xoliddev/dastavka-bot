# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Tashkent

WORKDIR /app

# Dependencies first for better layer caching. `tzdata` (PyPI) provides zoneinfo data,
# and the calendar uses built-in labels, so no OS locale/tz packages are required.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Run as an unprivileged user.
RUN groupadd --system --gid 10001 bot \
 && useradd --system --uid 10001 --gid bot --home-dir /app --shell /usr/sbin/nologin bot

COPY --chown=bot:bot . .

USER bot

# Exec form: python is PID 1 and receives SIGTERM → aiogram stops polling gracefully.
STOPSIGNAL SIGTERM
CMD ["python", "bot.py"]
