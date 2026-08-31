import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Conecta na Groq usando sua chave do .env
cliente = Groq()

print("Modelos atualmente disponíveis para a sua conta:\n")
# Pede a lista oficial direto do servidor deles
for modelo in cliente.models.list().data:
    print(f"- {modelo.id}")