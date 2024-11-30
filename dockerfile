FROM python:3.11

WORKDIR /app/backend

COPY requirements.txt .
COPY voice_api-1.1.0-py3-none-any.whl .
COPY avatar_sync_lip-1.0.1-py3-none-any.whl .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install ./voice_api-1.1.0-py3-none-any.whl
RUN pip install ./avatar_sync_lip-1.0.1-py3-none-any.whl

COPY . .

# 收集靜態文件
RUN python manage.py collectstatic --noinput

EXPOSE 5000

CMD ["python", "manage.py", "runserver", "0.0.0.0:5000"]