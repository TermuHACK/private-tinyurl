FROM python:3.12-alpine

WORKDIR /app

# зависимости для psycopg2
RUN apk add --no-cache gcc musl-dev postgresql-dev

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["python", "app.py"]
