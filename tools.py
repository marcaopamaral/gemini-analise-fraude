import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import sys
from io import BytesIO
import requests

# Variável global para a URL do arquivo grande (150MB)
# ATENÇÃO: Substitua ESTE link com o link RAW do seu arquivo ZIP no GitHub ou outro serviço.
PUBLIC_CSV_URL = "https://raw.githubusercontent.com/marcaopamaral/gemini-analise-fraude/data/creditcard.zip" 
# Nota: Você deve trocar a extensão no link do GitHub para .zip e usar um link RAW para download direto.

def carregar_dados_dinamicamente(url: str):
    """Carrega um DataFrame a partir de uma URL fornecida (suporta .zip)."""
    if not url:
        return "Erro: URL não fornecida."
    
    # Nome do arquivo CSV dentro do ZIP. Ajuste se o nome for diferente!
    nome_interno_do_csv = 'creditcard.csv' 
    
    try:
        print(f"[INFO] Tentando carregar dados da URL: {url}")
        
        # O Pandas detecta 'compression' automaticamente, mas forçamos para ZIP se a URL terminar em .zip
        if url.lower().endswith('.zip'):
            df_retorno = pd.read_csv(
                url, 
                compression='zip', 
                # Força a leitura do CSV com o nome especificado dentro do ZIP
                filepath_or_buffer=nome_interno_do_csv 
            )
        else:
            df_retorno = pd.read_csv(url)
            
        print(f"[INFO] Dados carregados com sucesso da URL.")
        return df_retorno
    except Exception as e:
        return f"Erro ao carregar dados da URL ({e}). Verifique o link e a acessibilidade."

def carregar_dados_ou_demo():
    """Tenta carregar o creditcard.csv via URL pública ou cria um DataFrame de demonstração."""
    
    GENERIC_PLACEHOLDER_URL = "https://example.com/seu_arquivo_publico_de_150MB.csv"

    if PUBLIC_CSV_URL and PUBLIC_CSV_URL != GENERIC_PLACEHOLDER_URL:
        # A lógica de carregamento dinâmico já lida com ZIP/CSV e retorna o DataFrame ou a string de erro
        df_retorno = carregar_dados_dinamicamente(PUBLIC_CSV_URL)
        if isinstance(df_retorno, pd.DataFrame):
            print(f"[INFO] Dados carregados com sucesso via URL (função de inicialização).")
            return df_retorno
        else:
            print(f"[AVISO] Falha ao carregar dados da URL: {df_retorno}. Recorrendo ao carregamento local/demo.")
            
    file_path = 'data/creditcard.csv'
    if os.path.exists(file_path):
        try:
            df_retorno = pd.read_csv(file_path)
            print(f"[INFO] Dados carregados com sucesso de '{file_path}' (Ambiente Local).")
            return df_retorno
        except Exception as e:
            print(f"[AVISO] Falha ao carregar arquivo local: {e}. Criando DataFrame de demonstração.")

    print(f"[AVISO] Arquivo não encontrado ou falha de URL. Criando DataFrame de demonstração.")
    
    data = {
        'Time': range(100),
        'Amount': [10 + i % 100 for i in range(100)],
        'Class': [0] * 95 + [1] * 5
    }
    for i in range(1, 29):
        data[f'V{i}'] = [i * 0.1 for i in range(100)]
        
    colunas_pca = [f'V{i}' for i in range(1, 29)]
    colunas_ordenadas = ['Time'] + colunas_pca + ['Amount', 'Class']
    
    df_retorno = pd.DataFrame(data).reindex(columns=colunas_ordenadas)
    return df_retorno


def consulta_tool(df: pd.DataFrame, codigo_python: str) -> str:
    """
    Executa um trecho de código Python no DataFrame 'df' e retorna o resultado formatado.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return "Erro: O DataFrame não foi carregado corretamente para consulta."
        
    stdout_buffer = io.StringIO()
    sys.stdout = stdout_buffer

    try:
        exec_locals = {'df': df, 'pd': pd}
        exec(f'result = {codigo_python}', {'pd': pd, 'df': df}, exec_locals)
        
        result = exec_locals.get('result')

        if isinstance(result, (pd.Series, pd.DataFrame)):
            return result.to_markdown()
        
        output = stdout_buffer.getvalue().strip()
        
        if not output and result is not None:
            return str(result)
        elif output:
            return output
        else:
            return "Comando executado com sucesso, mas não gerou um retorno visível."
            
    except Exception as e:
        return f"Erro na execução do código Python: {e}"
        
    finally:
        sys.stdout = sys.__stdout__


def grafico_tool(df: pd.DataFrame, tipo_grafico: str, colunas: list, titulo: str) -> BytesIO | str:
    """
    Gera um gráfico com base no tipo especificado e retorna o buffer de memória da imagem (BytesIO).
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return "Erro: O DataFrame não foi carregado corretamente para gerar o gráfico."

    try:
        plt.figure(figsize=(10, 6))
        
        if tipo_grafico == 'hist' and len(colunas) == 1:
            df[colunas[0]].hist(bins=50, edgecolor='black', alpha=0.7)
            plt.title(f'Histograma de {colunas[0]}')
            plt.xlabel(colunas[0])
            plt.ylabel('Frequência')

        elif tipo_grafico == 'box' and len(colunas) == 1:
            df.boxplot(column=colunas[0], by='Class', grid=False, figsize=(8, 6))
            plt.suptitle('') 
            plt.title(f'Boxplot de {colunas[0]} por Classe (0=Normal, 1=Fraude)')
            plt.xlabel('Classe')
            plt.ylabel(colunas[0])
            
        elif tipo_grafico == 'scatter' and len(colunas) == 2:
            col_x, col_y = colunas[0], colunas[1]
            plt.scatter(df[col_x], df[col_y], c=df['Class'], cmap='coolwarm', alpha=0.6)
            plt.title(f'Dispersão de {col_x} vs {col_y} (Cor por Fraude)')
            plt.xlabel(col_x)
            plt.ylabel(col_y)
            plt.colorbar(label='Class (0=Normal, 1=Fraude)')
            
        elif tipo_grafico == 'bar' and colunas[0].lower() == 'class':
            fraudes = df['Class'].value_counts()
            fraudes.plot(kind='bar', color=['skyblue', 'salmon'])
            plt.title('Contagem de Transações por Classe')
            plt.xlabel('Classe (0=Normal, 1=Fraude)')
            plt.ylabel('Contagem')
            plt.xticks(rotation=0)
        
        elif tipo_grafico == 'pie' and len(colunas) == 1 and colunas[0].lower() == 'class':
            contagem_classe = df['Class'].value_counts()
            labels = ['Normal', 'Fraude']
            plt.pie(contagem_classe, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#66b3ff', '#ff9999'])
            plt.title('Distribuição de Transações (Normal vs. Fraude)')
            plt.ylabel('')
            
        elif tipo_grafico == 'line' and len(colunas) == 2:
            col_x, col_y = colunas[0], colunas[1]
            plt.plot(df[col_x], df[col_y])
            plt.title(f'Gráfico de Linha de {col_x} vs {col_y}')
            plt.xlabel(col_x)
            plt.ylabel(col_y)
        
        elif tipo_grafico == 'area' and len(colunas) == 2:
            col_x, col_y = colunas[0], colunas[1]
            plt.fill_between(df[col_x], df[col_y], color="skyblue", alpha=0.4)
            plt.plot(df[col_x], df[col_y], color="Slateblue", alpha=0.6)
            plt.title(f'Gráfico de Área de {col_x} vs {col_y}')
            plt.xlabel(col_x)
            plt.ylabel(col_y)
            
        else:
            plt.close()
            return f"Erro: Tipo de gráfico '{tipo_grafico}' ou número de colunas inválido para o tipo selecionado."
        
        plt.suptitle(titulo, fontsize=16)
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='
