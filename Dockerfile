FROM python

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["python", "main.py"]

# sudo chmod -R 755 pgdata