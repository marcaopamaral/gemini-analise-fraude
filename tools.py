import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import sys

# Desativa a exibição de janelas interativas do Matplotlib para rodar no terminal
plt.switch_backend('Agg')

# --- Configuração Inicial de Dados ---

# Define o caminho completo do arquivo CSV
DATA_PATH = os.path.join("data", "creditcard.csv")

# Tenta carregar o DataFrame (df)
try:
    # O arquivo real geralmente é grande, então carregamos o DataFrame principal
    df = pd.read_csv(DATA_PATH)
    print(f"\n[INFO] DataFrame carregado com sucesso de: {DATA_PATH}. Linhas: {len(df)}")
    # Mapeia as classes para nomes mais amigáveis para gráficos
    df['Class_Label'] = df['Class'].map({0: 'Normal', 1: 'Fraude'})
except FileNotFoundError:
    print(f"\n[ERRO] O arquivo '{DATA_PATH}' não foi encontrado.")
    print("[ERRO] Por favor, crie a pasta 'data' e insira o arquivo 'creditcard.csv'.")
    print("[INFO] Criando um DataFrame de demonstração com 10 linhas para fins de teste...")
    
    # Cria um DataFrame de demonstração com a estrutura correta para fins de teste
    data = {
        'Time': range(10),
        'V1': [0.1] * 10,
        'V2': [0.5] * 10,
        'V28': [0.9] * 10,
        'Amount': [10.0, 50.0, 100.0, 10.0, 20.0, 5.0, 150.0, 10.0, 5.0, 20.0],
        'Class': [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    }
    # Adiciona as colunas V3 a V27 como zeros para simular a estrutura
    for i in range(3, 28):
        data[f'V{i}'] = [0.0] * 10
        
    df = pd.DataFrame(data)
    df['Class_Label'] = df['Class'].map({0: 'Normal', 1: 'Fraude'})
    print(f"[INFO] DataFrame de demonstração criado com colunas: {df.columns.tolist()}")
except Exception as e:
    print(f"\n[ERRO] Ocorreu um erro ao carregar o CSV: {e}")
    sys.exit(1)


# --- Ferramenta de Consulta (consulta_tool) ---

def consulta_tool(codigo_python: str) -> str:
    """
    Realiza consultas e análises estatísticas complexas no DataFrame global 'df'.
    Esta função executa o código Python fornecido pelo Agente Gemini e retorna o resultado.
    O Agente DEVE fornecer um código Python válido que retorne uma string ou um valor simples.

    Args:
        codigo_python: O código Python a ser executado (ex: 'df.shape', 'df.head()', 'df["Amount"].describe()').

    Returns:
        Uma string contendo o resultado da execução do código ou uma mensagem de erro.
    """
    global df # Permite o acesso ao DataFrame carregado

    # Captura a saída padrão (stdout) para retornar resultados de print() ou display
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output
    
    try:
        # A função 'exec' executa o código Python. 
        # Usamos 'eval' se o código for uma única expressão que retorna um valor.
        # Caso contrário, o código deve ser formatado para printar o resultado.
        
        # Tenta avaliar (eval) se for uma expressão simples (ex: df.shape)
        try:
            resultado = eval(codigo_python)
            if resultado is None:
                # Se for uma expressão que retorna None (como print()), pegamos o que foi printado
                return redirected_output.getvalue().strip()
            # Converte o resultado para string para garantir que possa ser retornado
            return str(resultado)
        except (NameError, TypeError, SyntaxError):
            # Se a avaliação falhar (ex: código com if/for ou sem retorno), usa a execução (exec)
            exec(codigo_python, globals(), {'df': df})
            # Pega o que foi printado durante a execução
            return redirected_output.getvalue().strip()

    except Exception as e:
        # Em caso de erro, retorna a mensagem de erro para o Agente
        return f"ERRO na execução do código: {type(e).__name__}: {str(e)}"
    finally:
        # Restaura a saída padrão
        sys.stdout = old_stdout


# --- Ferramenta de Geração de Gráfico (grafico_tool) ---

def grafico_tool(tipo_grafico: str, colunas: list, titulo: str) -> str:
    """
    Gera e salva um gráfico no formato PNG com base nos dados do DataFrame.
    
    Args:
        tipo_grafico: O tipo de gráfico ('hist', 'scatter', 'box', 'bar').
        colunas: Uma lista de strings com os nomes das colunas a serem usadas no gráfico.
        titulo: O título que o Agente sugere para o gráfico.

    Returns:
        Uma string confirmando que o gráfico foi salvo e a localização do arquivo.
    """
    global df
    
    try:
        plt.figure(figsize=(10, 6))
        plt.title(titulo)

        if tipo_grafico == 'hist' and len(colunas) == 1:
            # Histograma: Ideal para ver a distribuição de uma variável (ex: Amount, V1)
            coluna = colunas[0]
            if coluna in df.columns:
                df[coluna].hist(bins=50, alpha=0.7)
                plt.xlabel(coluna)
                plt.ylabel('Frequência')
                plt.grid(axis='y', alpha=0.5)
            else:
                 return f"ERRO: Coluna '{coluna}' não encontrada no DataFrame para Histograma."

        elif tipo_grafico == 'box' and len(colunas) == 1:
            # Boxplot: Ideal para identificar outliers e distribuição (ex: Amount por Class)
            coluna = colunas[0]
            if coluna in df.columns:
                df.boxplot(column=coluna, by='Class_Label', vert=False)
                plt.suptitle('') # Remove o título automático do 'by'
                plt.xlabel(coluna)
                plt.ylabel('Class (0=Normal, 1=Fraude)')
            else:
                 return f"ERRO: Coluna '{coluna}' não encontrada no DataFrame para Boxplot."

        elif tipo_grafico == 'scatter' and len(colunas) == 2:
            # Scatter Plot: Ideal para ver a relação entre duas variáveis (ex: V1 e V2)
            coluna_x, coluna_y = colunas
            if coluna_x in df.columns and coluna_y in df.columns:
                # Usa 'Class' para colorir os pontos (Fraude em vermelho)
                scatter = plt.scatter(df[coluna_x], df[coluna_y], c=df['Class'], cmap='coolwarm', alpha=0.5)
                plt.xlabel(coluna_x)
                plt.ylabel(coluna_y)
                plt.legend(*scatter.legend_elements(), title="Class")
            else:
                 return f"ERRO: Colunas '{coluna_x}' ou '{coluna_y}' não encontradas no DataFrame para Scatter Plot."
        
        elif tipo_grafico == 'bar' and len(colunas) == 1 and colunas[0] == 'Class':
            # Gráfico de Barras para contagem de classes (Fraude vs. Normal)
            df['Class_Label'].value_counts().plot(kind='bar', color=['skyblue', 'salmon'])
            plt.xticks(rotation=0)
            plt.ylabel('Contagem de Transações')
            plt.xlabel('Tipo de Transação')
            
        else:
            return f"ERRO: Tipo de gráfico '{tipo_grafico}' ou número incorreto de colunas fornecido. Tipos aceitos: 'hist' (1 coluna), 'box' (1 coluna), 'scatter' (2 colunas), 'bar' (coluna 'Class')."

        # Garante que a pasta 'data' exista para salvar o arquivo
        if not os.path.exists("data"):
            os.makedirs("data")

        # Define o nome do arquivo e salva
        file_path = os.path.join("data", "grafico_analise.png")
        plt.tight_layout() # Ajusta o layout para evitar cortes
        plt.savefig(file_path)
        plt.close() # Fecha a figura para liberar memória

        return f"SUCESSO: Gráfico '{titulo}' do tipo '{tipo_grafico}' gerado e salvo em: {file_path}"

    except Exception as e:
        plt.close() # Garante que a figura seja fechada em caso de erro
        return f"ERRO ao gerar o gráfico: {type(e).__name__}: {str(e)}"

# A chamada das ferramentas está comentada para evitar execução automática
# print(consulta_tool("df['Amount'].describe()")) 
# print(grafico_tool('hist', ['Amount'], 'Distribuição do Valor das Transações'))