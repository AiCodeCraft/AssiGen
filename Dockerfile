FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=7860
ENV HF_SPACE=True
ENV MPLCONFIGDIR=/tmp/matplotlib-cache
RUN mkdir -p $MPLCONFIGDIR && chmod 777 $MPLCONFIGDIR

CMD ["python", "app.py"]
