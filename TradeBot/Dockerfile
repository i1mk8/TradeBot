FROM python:3

WORKDIR /bot

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY /bot .

CMD ["python", "bot.py"]
