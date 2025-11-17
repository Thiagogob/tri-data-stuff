import sys
import os

# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")

# Verifica se os imports funcionam
from utils import load_config
from utils_events import get_events_df
print("✅ Funções importadas com sucesso.")

# A função get_events_df() deve carregar a configuração e começar a trabalhar.
print("Iniciando a coleta, processamento e limpeza dos dados de eventos (get_events_df())...")

# Se você precisar passar configurações, use:
# config = load_config()
# df_final = get_events_df(events_config=config["events"])

# Se não precisar de customização, chame sem argumentos:
df_final = get_events_df()

print(f"\n--- Processo Concluído ---")
print(f"Total de eventos no DataFrame final (após limpeza): {len(df_final)}")
if not df_final.empty:
    print("\nAmostra das primeiras linhas do DataFrame:")
    print(df_final.head())
    
# O log de processamento (eventos carregados, ignorados e retornados) será impresso pelo print_log_file()