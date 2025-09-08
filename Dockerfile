# 1. Usar uma imagem base oficial do Python
FROM python:3.9-slim

# 2. Definir o diretório de trabalho dentro do container
WORKDIR /app

# 3. Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar todos os arquivos do projeto para o diretório de trabalho
COPY . .

# 5. Expor a porta que o Gunicorn vai usar dentro do container
EXPOSE 8000

# 6. Comando para iniciar a aplicação quando o container for executado
#    Usamos Gunicorn para rodar o objeto 'app' que está no arquivo 'app.py'
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]