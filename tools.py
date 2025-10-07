import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import sys
from io import BytesIO
import requests

# Variável global para a URL do arquivo grande (150MB)
# LINK FINAL E ESTÁVEL: Aponta para o arquivo creditcard.csv na branch 'main' do GitHub.
PUBLIC_CSV_URL = "https://raw.githubusercontent.com/marcaopamaral/gemini-analise-fraude/main/data/creditcard.csv"

def carregar_dados_dinamicamente(url: str):
    """Carrega um DataFrame a partir de uma URL fornecida, suportando compressão (ZIP, GZ, etc.)."""
    if not url:
        return "Erro: URL não fornecida."
    try:
        print(f"[INFO] Tentando carregar dados da URL: {url}")
        # Suporte a compressão adicionado aqui
        df_retorno = pd.read_csv(url, compression='infer')
        print(f"[INFO] Dados carregados com sucesso da URL.")
        return df_retorno
    except Exception as e:
        return f"Erro ao carregar dados da URL ({e}). Verifique o link e a acessibilidade."

def carregar_dados_ou_demo():
    """Tenta carregar o creditcard.csv via URL pública, localmente, ou cria um DataFrame de demonstração. Suporta compressão."""
    
    GENERIC_PLACEHOLDER_URL = "https://example.com/seu_arquivo_publico_de_150MB.csv"

    # 1. TENTATIVA DE URL (GitHub)
    if PUBLIC_CSV_URL and PUBLIC_CSV_URL != GENERIC_PLACEHOLDER_URL:
        try:
            print(f"[INFO] Tentando carregar dados da URL: {PUBLIC_CSV_URL}")
            # Comando que carrega o arquivo do GitHub
            df_retorno = pd.read_csv(PUBLIC_CSV_URL, compression='infer')
            print(f"[INFO] Dados carregados com sucesso via URL do GitHub.")
            return df_retorno
        except Exception as e:
            # Em caso de falha no GitHub, ele tenta o carregamento local
            print(f"[AVISO] Falha ao carregar dados da URL do GitHub ({e}). Recorrendo ao carregamento local/demo.")
            
    # 2. TENTATIVA SECUNDÁRIA (CARREGAMENTO LOCAL)
    file_path = 'data/creditcard.csv'
    if os.path.exists(file_path):
        try:
            # Comando que carrega o arquivo localmente
            df_retorno = pd.read_csv(file_path, compression='infer')
            print(f"[INFO] Dados carregados com sucesso de '{file_path}' (Ambiente Local).")
            return df_retorno
        except Exception as e:
            print(f"[AVISO] Falha ao carregar arquivo local: {e}. Criando DataFrame de demonstração.")

    # 3. FALLBACK (DEMONSTRAÇÃO)
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
    
    Args:
        df: O DataFrame de dados.
        codigo_python: O código Python (como string) para executar no DataFrame 'df'.
        
    Returns:
        O resultado da execução do código como uma string.
    """
    if df is None:
        return "Erro: O DataFrame não foi carregado corretamente."
        
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
    
    Args:
        df: O DataFrame de dados.
        tipo_grafico: Tipo de gráfico ('hist', 'box', 'scatter', 'bar', 'pie', 'line', 'area').
        colunas: Lista de colunas a serem plotadas.
        titulo: Título do gráfico.
        
    Returns:
        Um objeto BytesIO contendo o PNG do gráfico, ou uma string de erro.
    """
    if df is None:
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
            return f"Erro: Tipo de gráfico '{tipo_grafico}' ou número de colunas inválido."
        
        plt.suptitle(titulo, fontsize=16)
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        plt.close()
        
        return buffer 

    except KeyError as e:
        plt.close()
        return f"Erro: Coluna não encontrada: {e}. Colunas disponíveis: {df.columns.tolist()}"
    except Exception as e:
        plt.close()
        return f"Erro inesperado ao gerar o gráfico: {e}"