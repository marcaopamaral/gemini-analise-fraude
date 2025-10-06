import streamlit as st
import pandas as pd
import json
import time
import requests
from io import BytesIO
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
            time.sleep(2 ** attempt)

        except requests.exceptions.RequestException as req_err:
            st.warning(f"Erro de conexão: {req_err}. Tentando novamente em {2**attempt}s...")
            if attempt == max_retries - 1:
                st.error(f"Falha na conexão com a API após {max_retries} tentativas.")
                return {}
            time.sleep(2 ** attempt)
            
    return {}


def run_conversation(prompt: str):
    """Gerencia o ciclo de conversa, incluindo a chamada de ferramentas."""
    
    # 1. Adiciona a nova pergunta ao histórico de chat
    st.session_state.messages.append({"role": "user", "parts": [{"text": prompt}]})

    # 2. Prepara a lista de ferramentas disponíveis
    available_tools = [
        {
            "functionDeclarations": [
                {
                    "name": "carregar_dados",
                    "description": "Carrega um DataFrame a partir de uma URL de arquivo .csv fornecida. Use esta ferramenta quando o usuário mencionar uma URL de arquivo.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "url": {"type": "STRING", "description": "A URL pública do arquivo CSV."}
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "consulta_tool",
                    "description": "Executa código Python para consultar o DataFrame 'df' e retorna resultados como string. Use para obter estatísticas, valores, linhas específicas, etc.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "codigo_python": {"type": "STRING", "description": "O código Python a ser executado no DataFrame 'df'. Ex: df.shape[0]"}
                        },
                        "required": ["codigo_python"]
                    }
                },
                {
                    "name": "grafico_tool",
                    "description": "Gera um gráfico e retorna a imagem em buffer de memória. Use para histogramas, boxplots, dispersão (scatter) e gráficos de barra.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "tipo_grafico": {"type": "STRING", "description": "Tipo: 'hist', 'box', 'scatter' ou 'bar'."},
                            "colunas": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Lista de 1 ou 2 colunas para o gráfico. Ex: ['Amount']"},
                            "titulo": {"type": "STRING", "description": "Título descritivo para o gráfico."}
                        },
                        "required": ["tipo_grafico", "colunas", "titulo"]
                    }
                },
                {
                    "name": "analisar_conclusoes",
                    "description": "Analisa o histórico da conversa e as análises já realizadas para tirar conclusões sobre os dados e gerar um resumo final. Use esta ferramenta quando o usuário perguntar 'quais as conclusões' ou 'o que você descobriu' etc.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {},  # Sem parâmetros, pois o histórico já é o input
                    }
                }
            ]
        }
    ]

    # 3. Primeira chamada: Envia a pergunta e o histórico para ver se o modelo usa a ferramenta
    with st.spinner("🧠 Pensando... (Primeira Chamada)"):
        response_1 = call_gemini_api(st.session_state.messages, tools=available_tools)
    
    # Se a primeira chamada falhou (retornou dicionário vazio)
    if not response_1:
        st.session_state.messages.pop() # Remove a última mensagem do usuário para tentar novamente
        return
        
    # 4. Processa a resposta (Texto ou Chamada de Função)
    try:
        candidate = response_1["candidates"][0]
        
        # 4.1. Se o modelo chamou uma função (Function Call)
        if candidate["content"]["parts"] and "functionCall" in candidate["content"]["parts"][0]:
            function_call = candidate["content"]["parts"][0]["functionCall"]
            func_name = function_call["name"]
            func_args = dict(function_call["args"])
            
            # Adiciona a chamada de função ao histórico
            st.session_state.messages.append(candidate["content"])

            # Executa a função localmente
            tool_output = "Erro: Ferramenta não executada."
            
            # --- Adicionado o novo bloco para a ferramenta 'carregar_dados' ---
            if func_name == "carregar_dados":
                with st.spinner("⏳ Carregando dados da URL..."):
                    url = func_args.get("url")
                    st.session_state.df = carregar_dados_dinamicamente(url) # Carrega o novo DataFrame
                    if isinstance(st.session_state.df, pd.DataFrame):
                        tool_output = f"Dados carregados com sucesso! Linhas: {st.session_state.df.shape[0]}, Colunas: {st.session_state.df.shape[1]}."
                    else:
                        tool_output = st.session_state.df # É uma string de erro
            # --- Fim do novo bloco ---
            
            elif func_name == "consulta_tool":
                with st.spinner(f"🛠️ Executando consulta: `{func_args.get('codigo_python')}`"):
                    tool_output = consulta_tool(st.session_state.df, func_args["codigo_python"])
                
            elif func_name == "grafico_tool":
                with st.spinner(f"📊 Gerando gráfico: {func_args.get('titulo')}"):
                    buffer_ou_erro = grafico_tool(st.session_state.df, func_args.get("tipo_grafico"), func_args.get("colunas"), func_args.get("titulo"))
                
                if isinstance(buffer_ou_erro, BytesIO):
                    st.session_state.tool_image = buffer_ou_erro
                    tool_output = "Gráfico gerado com sucesso e salvo em buffer."
                else:
                    tool_output = f"Ocorreu um erro ao gerar o gráfico: {buffer_ou_erro}"
            
            elif func_name == "analisar_conclusoes":
                with st.spinner("🧠 Analisando conclusões..."):
                    tool_output = "Histórico analisado, por favor, gere as conclusões."
            
            # Adiciona o resultado da ferramenta ao histórico
            tool_result_part = {
                "functionResponse": {
                    "name": func_name,
                    "response": {"output": tool_output}
                }
            }
            st.session_state.messages.append({"role": "user", "parts": [tool_result_part]})

            # Segunda chamada: Envia o resultado da ferramenta para o modelo gerar o texto final
            with st.spinner("💬 Gerando resposta final... (Segunda Chamada)"):
                response_2 = call_gemini_api(st.session_state.messages, tools=available_tools)
            
            if not response_2:
                st.session_state.messages.pop() # Remove a mensagem de resultado da ferramenta
                st.session_state.messages.pop() # Remove a mensagem de chamada da ferramenta
                st.session_state.messages.pop() # Remove a mensagem original do usuário
                return
                
            # Extrai a resposta final do modelo
            final_text = response_2["candidates"][0]["content"]["parts"][0]["text"]
            
            # Adiciona a resposta final ao histórico e à interface
            st.session_state.messages.append({"role": "model", "parts": [{"text": final_text}]})
            st.rerun() # FORÇA O RERUN PARA EXIBIR A RESPOSTA IMEDIATAMENTE!
            
        # 4.2. Se o modelo respondeu diretamente com texto
        else:
            final_text = candidate["content"]["parts"][0]["text"]
            st.session_state.messages.append({"role": "model", "parts": [{"text": final_text}]})
            st.rerun() # FORÇA O RERUN PARA EXIBIR A RESPOSTA IMEDIATAMENTE!

    except Exception as e:
        st.error(f"Um erro ocorreu ao processar a resposta da API: {e}. Isso pode indicar um erro de parse do JSON da API.")
        return

# --- Interface do Streamlit ---

st.set_page_config(page_title="Agente de Análise de Fraudes (Gemini)", layout="wide")

st.title("FraudGuard: Agente de Análise de Fraudes 💳")
st.markdown("Use o poder do Gemini e pandas para analisar os dados de fraude de cartão de crédito.")
st.markdown("---")

# 1. Inicialização do Histórico e Imagem Temporária
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tool_image" not in st.session_state:
    st.session_state.tool_image = None
if "api_key_input" not in st.session_state:
    st.session_state.api_key_input = ""

# 2. Sidebar para API Key e Info
with st.sidebar:
    st.header("Configuração")
    st.info("Insira sua Chave API do Google Gemini. Se estiver no Streamlit Cloud, configure-a em 'Secrets'.")
    
    # Campo para inserir a chave API manualmente (útil para desenvolvimento local)
    api_key_input = st.text_input("Sua Chave API Gemini:", type="password", help="A chave será armazenada apenas nesta sessão.")
    st.session_state.api_key_input = api_key_input
    
    st.markdown("---")
    st.header("Status dos Dados")
    # Altera a verificação para o estado da sessão
    if "df" not in st.session_state or st.session_state.df is None or st.session_state.df.empty:
        st.error("Nenhum DataFrame carregado.")
        st.info("Por favor, forneça uma URL de um arquivo CSV, ou use a demo padrão.")
    elif st.session_state.df.shape[0] < 1000:
        st.warning(f"Usando DataFrame de Demonstração (Linhas: {st.session_state.df.shape[0]}).")
        st.write("Você pode fornecer uma URL de um novo arquivo CSV para análise.")
    else:
        st.success(f"Dados Carregados com Sucesso! (Linhas: {st.session_state.df.shape[0]} | Colunas: {st.session_state.df.shape[1]})")

# 3. Exibição do Histórico de Chat
chat_container = st.container()

with chat_container:
    # Itera sobre o histórico de mensagens para exibição
    for message in st.session_state.messages:
        role = "assistant" if message["role"] == "model" else "user"
        
        # Ignora as partes do histórico que são chamadas de função/resposta de ferramenta para o usuário final
        if "functionCall" in message["parts"][0] or "functionResponse" in message["parts"][0]:
            continue
            
        # Exibe mensagens de texto
        if "text" in message["parts"][0]:
            with st.chat_message(role):
                st.markdown(message["parts"][0]["text"])

    # Exibe o gráfico gerado pela ferramenta, se houver
    if st.session_state.tool_image:
        with st.chat_message("assistant"):
            st.image(st.session_state.tool_image, caption="Resultado da Visualização de Dados", use_container_width=True)
        st.session_state.tool_image = None # Limpa a imagem após exibição


# 4. Input de Chat
if prompt := st.chat_input("Pergunte sobre os dados (ex: 'Qual a média do Amount?')"):
    # Limpa a imagem anterior antes de processar a nova pergunta
    st.session_state.tool_image = None 
    
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)
            
    # Inicia a conversa e o processamento de ferramentas
    run_conversation(prompt)

# 5. Adiciona o primeiro prompt de boas-vindas se o histórico estiver vazio
if not st.session_state.messages:
    is_demo_df = st.session_state.df is not None and st.session_state.df.shape[0] < 1000
    
    if is_demo_df:
    welcome_message = """Olá! Eu sou um agente desenvolvido por Marcos para o desafio I2A2.
**Para testes uso dados de demonstração criado por mim.**
**Se quiser outro arquivo, me informe o caminho pelo comando:**
**Análise este arquivo CSV:** `https://link-para-o-seu-arquivo.csv`"""
else:
    welcome_message = """Olá! Eu sou um agente desenvolvido por Marcos para o desafio I2A2.
**Uso dados do arquivo `creditcard.csv`.**
**Se quiser outro arquivo, me informe o caminho pelo comando:**
**Análise este arquivo CSV:** `https://link-para-o-seu-arquivo.csv`"""
    
    st.session_state.messages.append({"role": "model", "parts": [{"text": welcome_message}]})
    st.rerun() # Reinicia para mostrar a mensagem de boas-vindas


