import streamlit as st
import os
import time
import json
import requests
import pandas as pd
from tools import carregar_dados_ou_demo, consulta_tool, grafico_tool # Importa todas as funções de tools
from io import BytesIO

# --- 1. Configurações e Constantes ---

MODEL_NAME = "gemini-2.5-flash-preview-05-20"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

# Definição das Ferramentas (mantida)
SYSTEM_INSTRUCTION_TEXT = "Você é um Analista de Fraude de Cartão de Crédito especializado em pandas. Sua tarefa é analisar o DataFrame 'df' que contém dados transacionais. As colunas V1-V28 são resultados de PCA. A coluna 'Amount' é o valor, 'Time' é o tempo e 'Class' (0=Normal, 1=Fraude) é o alvo. Use as ferramentas 'consulta_tool' para todas as análises de dados e 'grafico_tool' para visualizar os dados. Retorne apenas o resultado da análise ou a resposta amigável ao usuário. Se o usuário pedir para analisar ou resumir dados, USE A FERRAMENTA. NÃO tente executar código Python diretamente na sua resposta."

TOOL_DECLARATIONS = [
    {
        "functionDeclarations": [
            {
                "name": "consulta_tool",
                "description": "Realiza consultas e análises estatísticas no DataFrame (nomeado 'df'). Deve gerar o código Python COMPLETO em string (ex: 'df.describe()', 'df[df[\"Class\"] == 1].shape[0]', 'df[\"Amount\"].mean()').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"codigo_python": {"type": "STRING", "description": "O código Python válido (como string) para executar no DataFrame 'df'."}},
                    "required": ["codigo_python"]
                }
            },
            {
                "name": "grafico_tool",
                "description": "Gera um gráfico com base nos dados. Tipos aceitos: 'hist' (1 coluna), 'box' (1 coluna, comparado com Class), 'scatter' (2 colunas), 'bar' (coluna 'Class').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "tipo_grafico": {"type": "STRING", "description": "O tipo de gráfico a ser gerado ('hist', 'box', 'scatter', 'bar')."},
                        "colunas": {"type": "ARRAY", "description": "Uma lista de 1 ou 2 strings com os nomes das colunas.", "items": {"type": "STRING"}},
                        "titulo": {"type": "STRING", "description": "O título descritivo do gráfico."}
                    },
                    "required": ["tipo_grafico", "colunas", "titulo"]
                }
            }
        ]
    }
]

# Mapeamento para chamar as funções Python reais
# NOTA: O mapeamento é feito dentro de run_conversation para passar o 'df'
# TOOL_MAP = { "consulta_tool": consulta_tool, "grafico_tool": grafico_tool }


# --- 2. Funções de Chamada de API e Lógica de Tool Calling ---

@st.cache_data(show_spinner=False)
def get_dataframe():
    """Carrega o DataFrame apenas uma vez e usa o cache do Streamlit."""
    return carregar_dados_ou_demo()

def make_api_call_with_backoff(payload, api_key, max_retries=5):
    """Realiza a chamada à API do Gemini com backoff exponencial."""
    if not api_key: return None
    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(max_retries):
        try:
            url_with_key = f"{API_URL}?key={api_key}"
            response = requests.post(url_with_key, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code in [429, 500, 503] and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                st.error(f"Erro HTTP {response.status_code}: {e}. Verifique a chave.")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"Erro de Conexão: {e}")
            return None
    
    st.error("Número máximo de tentativas de API excedido.")
    return None

def run_conversation(df: pd.DataFrame, user_input: str, api_key: str):
    """Controla o fluxo da conversa (Usuário -> Agente -> Ferramenta -> Agente)."""

    st.session_state.messages.append({"role": "user", "parts": [{"text": user_input}]})
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Pensando...")

        # --- Primeira Chamada: Agente decide ---
        payload = {
            "contents": st.session_state.messages,
            "tools": TOOL_DECLARATIONS,
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION_TEXT}]}
        }
        response_json = make_api_call_with_backoff(payload, api_key)
        if response_json is None: 
            st.session_state.messages.pop() # Remove entrada do usuário
            return

        candidate = response_json.get("candidates", [{}])[0]
        first_part = candidate.get('content', {}).get('parts', [{}])[0]
        
        # --- Lógica de Chamada de Ferramenta ---
        if 'functionCall' in first_part or 'functionCalls' in first_part:
            
            function_calls = []
            if 'functionCalls' in first_part: function_calls = first_part['functionCalls']
            elif 'functionCall' in first_part: function_calls = [first_part['functionCall']]

            tool_results = []
            
            for call in function_calls:
                function_name = call['name']
                args = dict(call['args'])
                
                placeholder.markdown(f"**Agente executando:** `{function_name}`...")

                if function_name == "consulta_tool":
                    # Passa o df para a tool
                    result = consulta_tool(df, **args)
                    tool_response_text = result
                elif function_name == "grafico_tool":
                    # Passa o df para a tool
                    plot_buffer_or_error = grafico_tool(df, **args)
                    
                    if isinstance(plot_buffer_or_error, BytesIO):
                        # Armazena o buffer do gráfico na sessão para exibição
                        st.session_state.current_plot_buffer = plot_buffer_or_error
                        tool_response_text = f"Resultado: Gráfico gerado em memória (BytesIO) com o título: {args.get('titulo')}"
                    else:
                        tool_response_text = f"Resultado: ERRO na geração do gráfico: {plot_buffer_or_error}"
                        
                else:
                    tool_response_text = f"ERRO: Função '{function_name}' não mapeada."

                tool_results.append({
                    "functionResponse": {
                        "name": function_name,
                        "response": {"result": tool_response_text}
                    }
                })

            # Adiciona o resultado da ferramenta ao histórico
            st.session_state.messages.append({"role": "tool", "parts": tool_results})
            
            # --- Segunda Chamada: Agente gera a resposta final ---
            payload_tool_response = {
                "contents": st.session_state.messages,
                "tools": TOOL_DECLARATIONS,
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION_TEXT}]}
            }
            
            final_response_json = make_api_call_with_backoff(payload_tool_response, api_key)
            
            if final_response_json is None: 
                st.session_state.messages.pop() # Remove tool
                st.session_state.messages.pop() # Remove user
                return
                
            final_text = final_response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Não foi possível obter a resposta final do Agente.')
            
            placeholder.markdown(final_text)

            # Exibe o gráfico se ele foi gerado na primeira iteração (grafico_tool)
            if 'current_plot_buffer' in st.session_state and st.session_state.current_plot_buffer is not None:
                st.image(st.session_state.current_plot_buffer, caption=args.get('titulo', 'Gráfico de Análise'), use_column_width=True)
                st.session_state.current_plot_buffer = None # Limpa após exibição

            st.session_state.messages.append({"role": "model", "parts": [{"text": final_text}]})

        # --- Lógica de Resposta Direta (Sem Tool Call) ---
        else:
            agent_text = first_part.get('text', 'Não foi possível obter resposta do Agente.')
            placeholder.markdown(agent_text)
            st.session_state.messages.append({"role": "model", "parts": [{"text": agent_text}]})


# --- 3. Streamlit UI (Interface do Usuário) ---

st.set_page_config(page_title="Agente de Análise de Fraude Gemini", layout="centered")
st.title("Agente de Análise de Fraude 💳")

# --- Carregamento e Gerenciamento do DataFrame ---
df_analysis = get_dataframe()

# --- Sidebar para a Chave API ---
with st.sidebar:
    st.header("Configuração e Dados")
    # Tenta ler a chave de 'secrets' (Streamlit Cloud) ou usa string vazia
    api_key = st.text_input(
        "Sua Chave API do Gemini", 
        type="password",
        value=st.secrets.get("GEMINI_API_KEY", "")
    )
    if not api_key:
        st.warning("Insira a chave API para ativar o Agente.")

    st.markdown("---")
    
    st.subheader("Status do DataFrame")
    if df_analysis is not None:
        if df_analysis.shape[0] == 100:
            st.warning("Arquivo CSV **não encontrado**. Usando dados de **DEMONSTRAÇÃO**.")
        else:
            st.success("Dados carregados com sucesso.")
        st.caption(f"Linhas: {df_analysis.shape[0]}, Colunas: {df_analysis.shape[1]}")
        st.dataframe(df_analysis.head(5), use_container_width=True)
    else:
        st.error("Falha ao carregar dados. Verifique a pasta 'data/'.")
    st.markdown("---")
    st.info("No Streamlit Cloud, configure o segredo `GEMINI_API_KEY`.")


# Inicializa o estado da sessão para o histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "model", "parts": [{"text": "Olá! Eu sou o Agente de Análise de Fraude. Faça uma pergunta sobre as transações, como **'Qual é a média dos valores?'** ou **'Mostre um boxplot da V1.'**"}]}]
if "current_plot_buffer" not in st.session_state:
     st.session_state.current_plot_buffer = None


# --- Renderiza Histórico de Chat ---
for message in st.session_state.messages:
    if message["role"] in ["user", "model"]:
        with st.chat_message(message["role"]):
            st.markdown(message["parts"][0]["text"])
            
            # Reexibe o último gráfico se ele estiver no histórico (após uma resposta do modelo)
            if message["role"] == "model" and st.session_state.current_plot_buffer is None:
                # Aqui você poderia adicionar lógica para re-exibir gráficos se necessário,
                # mas mantemos a exibição simples após a geração.
                pass 


# --- Caixa de Input do Usuário ---
if df_analysis is not None:
    if prompt := st.chat_input("Pergunte sobre os dados de fraude..."):
        if not api_key:
            st.error("Por favor, insira sua Chave API do Gemini na barra lateral para começar.")
        else:
            run_conversation(df_analysis, prompt, api_key)
