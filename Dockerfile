FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd -m -u 10001 lab && chown -R lab:lab /srv
COPY --chown=lab:lab app ./app
COPY --chown=lab:lab failure-engine ./failure-engine
COPY --chown=lab:lab slo-engine ./slo-engine
COPY --chown=lab:lab remediation-engine ./remediation-engine
USER lab
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
