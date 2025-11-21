import sys
import os

# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")

# Verifica se os imports funcionam
from utils_itu import get_athlete_info
from utils_events import get_events_df
print("✅ Funções importadas com sucesso.")

# A função get_events_df() deve carregar a configuração e começar a trabalhar.
get_athlete_info(105480)