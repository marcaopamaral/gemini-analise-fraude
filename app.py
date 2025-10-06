# 5. Adiciona o primeiro prompt de boas-vindas se o histórico estiver vazio
if not st.session_state.messages:
    is_demo_df = st.session_state.df is not None and isinstance(st.session_state.df, pd.DataFrame) and st.session_state.df.shape[0] < 1000
    
    # NOVO: Mensagens formatadas com linhas em branco para garantir 4 linhas no chat.
    if is_demo_df:
        welcome_message = """Olá! Eu sou um agente desenvolvido por Marcos para o desafio I2A2.

**Para testes uso dados de demonstração criado por mim.**

Se quiser outro arquivo, me informe o caminho pelo comando:

**Análise este arquivo CSV:** `https://link-para-o-seu-arquivo.csv`"""
    else:
        welcome_message = """Olá! Eu sou um agente desenvolvido por Marcos para o desafio I2A2.

**Uso dados do arquivo `creditcard.csv`.**

Se quiser outro arquivo, me informe o caminho pelo comando:

**Análise este arquivo CSV:** `https://link-para-o-seu-arquivo.csv`"""
    
    st.session_state.messages.append({"role": "model", "parts": [{"text": welcome_message}]})
    st.rerun() # Reinicia para mostrar a mensagem de boas-vindas
