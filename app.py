import streamlit as st
import pandas as pd
import json
import time
import requests
from io import BytesIO
# Importe as ferramentas que assumimos estar no arquivo tools.py
from tools import carregar_dados_ou_demo, consulta_tool, grafico_tool, carregar_dados_dinamicamente

# --- Configurações Iniciais ---

# URL da API do Gemini (usada para chamadas não-streaming)
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# Instrução do sistema para guiar o agente
SYSTEM_INSTRUCTION = (
    "Você é um Agente de Análise de Fraudes especializado em DataFrames pandas. "
    "Sua função é responder a perguntas usando as ferramentas 'carregar_dados', 'consulta_tool', 'grafico_tool' ou 'analisar_conclusoes'. "
    "NÃO gere código Python diretamente na resposta; use as ferramentas."
    "O DataFrame principal é chamado 'df' e contém colunas 'Time', 'V1' a 'V28', 'Amount' e 'Class'. "
    "Se o usuário fornecer uma URL de um arquivo .csv, use a ferramenta 'carregar_dados' com a URL. "
    "Sempre que o usuário pedir análise numérica ou estatística, use 'consulta_tool'. "
    "Sempre que o usuário pedir visualização (gráfico, histograma, boxplot), use 'grafico_tool'."
    "Quando o usuário solicitar um resumo, conclusões ou o que foi descoberto, use a ferramenta 'analisar_conclusoes'."
    "Responda de forma concisa e profissional, em português."
)

# --- Carregamento de Dados (Cache) ---
# A função de carregamento foi removida e o DataFrame agora será carregado dinamicamente por uma ferramenta.
# Inicializamos o DataFrame como None no início da sessão.
df = None

# Se o DataFrame ainda não foi carregado na sessão, carregue o de demonstração
if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = carregar_dados_ou_demo()

# --- Funções de Comunicação com a API ---

def call_gemini_api(history: list, tools: list | None = None) -> dict:
    """Função central para chamar a API do Gemini com backoff exponencial."""
    
    # 1. Obtenção da Chave API
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        api_key = st.session_state.get("api_key_input", "")
    
    if not api_key:
        st.error("Por favor, insira sua Chave de API Gemini na barra lateral.")
        return {}
        
    # 2. Construção do Payload
    payload = {
        "contents": history,
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
    }
    
    if tools:
        payload["tools"] = tools

    headers = {
        'Content-Type': 'application/json'
    }

    # 3. Lógica de Backoff e Requisição
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Anexa a chave API diretamente na URL
            response = requests.post(f"{API_URL}?key={api_key}", headers=headers, data=json.dumps(payload))
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as http_err:
            st.warning(f"Erro de comunicação com a API: {http_err}. Resposta: {response.text}")
            if attempt == max_retries - 1:
                st.error(f"Falha na comunicação com a API após {max_retries} tentativas. Verifique sua chave ou o formato JSON.")
                return {}
            time.sleep(2 **
