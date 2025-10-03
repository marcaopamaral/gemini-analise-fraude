import pandas as pd
import matplotlib.pyplot as plt
import os
import io

# Variável global para armazenar o DataFrame
df = None

def carregar_dados_ou_demo():
    """Tenta carregar o creditcard.csv ou cria um DataFrame de demonstração."""
    global df
    file_path = 'data/creditcard.csv'
    try:
        if not os.path.exists(file_path):
            print(f"[AVISO] Arquivo '{file_path}' não encontrado. Criando DataFrame de demonstração.")
            
            # DataFrame de demonstração com a estrutura exigida
            data = {
                'Time': range(100),
                'V1': [i * 0.1 for i in range(100)],
                'V28': [i * 0.5 for i in range(100)],
                'Amount': [10 + i % 100 for i in range(100)],
                'Class': [0] * 95 + [1] * 5  # 5% de fraude
            }
            # Adiciona as colunas V2 a V27 como zeros para completar as 28 colunas PCA
            for i in range(2, 28):
                data[f'V{i}'] = [0] * 100
                
            # Garante que as colunas V estejam na ordem correta, seguido por Amount, Class
            colunas_pca = [f'V{i}' for i in range(1, 29)]
            colunas_ordenadas = ['Time'] + colunas_pca + ['Amount', 'Class']
            
            df = pd.DataFrame(data).reindex(columns=colunas_ordenadas)

        else:
            df = pd.read_csv(file_path)
            print(f"[INFO] Dados carregados com sucesso de '{file_path}'.")
            
        print(f"[INFO] DataFrame (df) pronto. Colunas: {df.columns.tolist()}")

    except Exception as e:
        print(f"[ERRO] Falha ao carregar ou criar dados: {e}")
        df = None # Certifica que df é None em caso de falha total

# Carrega os dados uma vez ao importar o módulo
carregar_dados_ou_demo()


def consulta_tool(codigo_python: str) -> str:
    """
    Executa um trecho de código Python no DataFrame 'df' e retorna o resultado formatado.
    
    Args:
        codigo_python: O código Python (como string) para executar no DataFrame 'df'.
        
    Returns:
        O resultado da execução do código como uma string.
    """
    global df
    if df is None:
        return "Erro: O DataFrame não foi carregado corretamente."
        
    # Usa um buffer de texto para capturar a saída padrão (ex: print())
    stdout_buffer = io.StringIO()
    # Redireciona a saída padrão para o buffer
    sys.stdout = stdout_buffer

    try:
        # A função exec() executa o código; o DataFrame 'df' está disponível no escopo global
        exec_globals = {'df': df}
        # Executa o código Python
        exec(codigo_python, exec_globals)
        
        # Recupera a saída (se houver print ou saída de console)
        output = stdout_buffer.getvalue().strip()
        
        # Se não houve saída de console (output vazio), tenta avaliar o código (eval)
        if not output:
            try:
                # Usa eval() para obter o valor de retorno de expressões simples
                result = eval(codigo_python, {'df': df})
                # Retorna a representação em string do resultado (incluindo DataFrames/Series)
                return str(result)
            except NameError:
                 # Captura NameError se o código não for uma expressão avaliável
                return "Código Python executado. Sem valor de retorno (use 'print()' se necessário) ou erro de variável. Retorno: OK"
            except Exception as e:
                # Outros erros de eval (ex: sintaxe)
                return f"Erro na execução (eval) do código '{codigo_python}': {e}"
        else:
            # Retorna a saída capturada (ex: resultado de df.head() que usa print)
            return output
            
    except Exception as e:
        return f"Erro na execução do código Python: {e}"
        
    finally:
        # Restaura a saída padrão original
        sys.stdout = sys.__stdout__


def grafico_tool(tipo_grafico: str, colunas: list, titulo: str) -> str:
    """
    Gera um gráfico com base no tipo especificado e salva como PNG.
    
    Args:
        tipo_grafico: Tipo de gráfico ('hist', 'box', 'scatter', 'bar').
        colunas: Lista de colunas a serem plotadas.
        titulo: Título do gráfico.
        
    Returns:
        O caminho onde o gráfico foi salvo.
    """
    global df
    if df is None:
        return "Erro: O DataFrame não foi carregado corretamente para gerar o gráfico."

    output_path = "data/grafico_analise.png"
    
    try:
        plt.figure(figsize=(10, 6))
        
        if tipo_grafico == 'hist' and len(colunas) == 1:
            df[colunas[0]].hist(bins=50, edgecolor='black', alpha=0.7)
            plt.title(f'Histograma de {colunas[0]}')
            plt.xlabel(colunas[0])
            plt.ylabel('Frequência')

        elif tipo_grafico == 'box' and len(colunas) == 1:
            # Boxplot comparando a coluna contra a classe (fraude/normal)
            df.boxplot(column=colunas[0], by='Class', grid=False, figsize=(8, 6))
            plt.suptitle('') # Remove o super-título padrão do boxplot
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
            plt.close() # Fecha a figura se o tipo for inválido
            return f"Erro: Tipo de gráfico '{tipo_grafico}' ou número de colunas inválido para a ferramenta."
        
        # Ajustes finais e salvamento
        plt.suptitle(titulo, fontsize=16) # Define o título principal
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close() # Fecha a figura para liberar memória
        
        return f"Gráfico salvo com sucesso em: {output_path}"

    except KeyError as e:
        plt.close()
        return f"Erro: Coluna não encontrada no DataFrame: {e}. Colunas disponíveis: {df.columns.tolist()}"
    except Exception as e:
        plt.close()
        return f"Erro inesperado ao gerar o gráfico: {e}"