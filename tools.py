import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import sys
from io import BytesIO

def carregar_dados_ou_demo():
    """Tenta carregar o creditcard.csv ou cria um DataFrame de demonstração."""
    # SUBSTITUA ESTA PARTE:
    # file_path = 'data/creditcard.csv'
    # df_retorno = pd.read_csv(file_path)

    # POR ESTA PARTE (usando a URL pública):
    url_dados = "https://www.dropbox.com/scl/fi/ibuflwf3bvau3a624f3ep/creditcard.csv?rlkey=duuiekt9cskkoya6rf3opokht&st=50sq7ym3&dl=0"
    try:
        df_retorno = pd.read_csv(url_dados)
        print("[INFO] Dados carregados com sucesso via URL.")
        return df_retorno
    except Exception as e:
        print(f"[ERRO] Falha ao carregar dados da URL: {e}")
        # ... fallback para dados de demonstração (se a URL falhar)
    
    try:
        if not os.path.exists(file_path):
            print(f"[AVISO] Arquivo '{file_path}' não encontrado. Criando DataFrame de demonstração.")
            
            # DataFrame de demonstração com a estrutura exigida
            data = {
                'Time': range(100),
                'Amount': [10 + i % 100 for i in range(100)],
                'Class': [0] * 95 + [1] * 5  # 5% de fraude
            }
            # Adiciona as colunas V1 a V28 como zeros
            for i in range(1, 29):
                data[f'V{i}'] = [i * 0.1 for i in range(100)]
                
            colunas_pca = [f'V{i}' for i in range(1, 29)]
            colunas_ordenadas = ['Time'] + colunas_pca + ['Amount', 'Class']
            
            df_retorno = pd.DataFrame(data).reindex(columns=colunas_ordenadas)
            return df_retorno

        else:
            # Em um deploy real, o arquivo deve estar no repo ou ser carregado pelo usuário
            df_retorno = pd.read_csv(file_path)
            print(f"[INFO] Dados carregados com sucesso de '{file_path}'.")
            return df_retorno

    except Exception as e:
        print(f"[ERRO] Falha ao carregar ou criar dados: {e}")
        return None


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
        
    # Usa um buffer de texto para capturar a saída padrão
    stdout_buffer = io.StringIO()
    sys.stdout = stdout_buffer

    try:
        # A função exec() executa o código; o DataFrame 'df' é passado no escopo local
        exec_locals = {'df': df}
        exec(codigo_python, {}, exec_locals) # Usa escopo local para 'df'
        
        output = stdout_buffer.getvalue().strip()
        
        if not output:
            try:
                # Tenta avaliar o código (eval) para obter o valor de retorno de expressões simples
                result = eval(codigo_python, {}, exec_locals)
                return str(result)
            except Exception as e:
                # Erro de eval ou código que não retorna valor
                return f"Código Python executado. Retorno: OK (Use 'print()' para visualizar grandes outputs) | Erro Eval: {e}"
        else:
            return output
            
    except Exception as e:
        return f"Erro na execução do código Python: {e}"
        
    finally:
        sys.stdout = sys.__stdout__


def grafico_tool(df: pd.DataFrame, tipo_grafico: str, colunas: list, titulo: str) -> BytesIO | str:
    """
    Gera um gráfico com base no tipo especificado e retorna o buffer de memória da imagem (BytesIO).
    
    Args:
        df: O DataFrame de dados.
        tipo_grafico: Tipo de gráfico ('hist', 'box', 'scatter', 'bar').
        colunas: Lista de colunas a serem plotadas.
        titulo: Título do gráfico.
        
    Returns:
        Um objeto BytesIO contendo o PNG do gráfico, ou uma string de erro.
    """
    if df is None:
        return "Erro: O DataFrame não foi carregado corretamente para gerar o gráfico."

    try:
        plt.figure(figsize=(10, 6))
        
        # Lógica de plotagem (mantida)
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
            
        else:
            plt.close()
            return f"Erro: Tipo de gráfico '{tipo_grafico}' ou número de colunas inválido."
        
        plt.suptitle(titulo, fontsize=16) 
        plt.tight_layout()
        
        # Salva o gráfico em um buffer de memória
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        plt.close() # Libera a memória
        
        return buffer # Retorna o objeto BytesIO (o Agente não deve ver isso, o app.py deve processar)

    except KeyError as e:
        plt.close()
        return f"Erro: Coluna não encontrada: {e}. Colunas disponíveis: {df.columns.tolist()}"
    except Exception as e:
        plt.close()
        return f"Erro inesperado ao gerar o gráfico: {e}"

