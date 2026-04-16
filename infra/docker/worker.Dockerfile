FROM python:3.11-slim

WORKDIR /app

COPY apps/backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /app
RUN pip install -e /app/ml/attendance_ai

CMD ["python", "scripts/seed_attendance_demo.py"]
