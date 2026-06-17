FROM python:3.12-slim
WORKDIR /app
COPY services/common/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt
COPY services/common ./common
COPY services/shipping-api/app.py .
EXPOSE 8080
CMD ["python", "app.py"]
