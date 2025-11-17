import pandas as pd
import json
import os
import sys
from pathlib import Path

# --- CONFIGURAÇÃO DE CAMINHO ---
# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)

# Importa a nova função 
from utils_itu import get_all_athletes 

### --- EXECUÇÃO DA COLETA ---
##PER_PAGE = 10 
##START_PAGE_RESUME = 513 # Ponto onde a falha ocorreu
##
##print(f"\n--- Retomando coleta de atletas a partir da página {START_PAGE_RESUME} ---")
##
### Chama a função de coleta, que carregará os 5120 atletas e reiniciará o loop
##all_athletes_list = get_all_athletes(
##    per_page=PER_PAGE,
##    start_page=START_PAGE_RESUME
##)

# --- VISUALIZAÇÃO ---
#if all_athletes_list:
#    df_all_athletes = pd.DataFrame(all_athletes_list)
#    
#    print("\n\n#############################################")
#    print(f"✅ COLETA FINALIZADA. Total de Atletas: {len(df_all_athletes)}")
#    print("#############################################")
#    
#    # Exibe uma amostra dos dados coletados
#    print(df_all_athletes[['athlete_id', 'athlete_title', 'athlete_noc', 'athlete_gender']].tail(10))
#else:
#    print("❌ Não foi possível coletar atletas.")

ATHLETES_FILE = Path('data') / "all_athletes" / "all_athletes_full_list.json"
COUNTRY_ID_BRASIL = 127
CAMPO_ID = 'athlete_country_id' # O campo que contém o ID do país

# --- 1. CARREGAR DADOS ---
try:
    with open(ATHLETES_FILE, 'r') as f:
        all_athletes_list = json.load(f)
except FileNotFoundError:
    print(f"❌ Erro: O arquivo de dados '{ATHLETES_FILE.name}' não foi encontrado.")
    print("Execute a coleta de todos os atletas primeiro.")
    exit()

if not all_athletes_list:
    print("⚠️ Aviso: O arquivo está vazio. Não é possível realizar a contagem.")
    exit()

df_all_athletes = pd.DataFrame(all_athletes_list)

# --- 2. CONTABILIZAÇÃO E CÁLCULO ---

# Garante que a coluna de ID seja numérica para a comparação (evita problemas de tipo)
df_all_athletes[CAMPO_ID] = pd.to_numeric(df_all_athletes[CAMPO_ID], errors='coerce')

# Total de atletas na lista (o denominador)
total_atletas = len(df_all_athletes)

# Contagem de atletas brasileiros (o numerador)
atletas_brasil = df_all_athletes[df_all_athletes[CAMPO_ID] == COUNTRY_ID_BRASIL]
quantidade_brasil = len(atletas_brasil)

# Calcula a representatividade
if total_atletas > 0:
    representatividade = (quantidade_brasil / total_atletas) * 100
else:
    representatividade = 0.0

# --- 3. EXIBIÇÃO DO RESULTADO ---

print("\n--- REPRESENTATIVIDADE DE ATLETAS BRASILEIROS ---")
print(f"ID do Brasil (athlete_country_id): {COUNTRY_ID_BRASIL}")
print(f"Total de atletas na amostra: {total_atletas:,}")
print(f"Atletas brasileiros encontrados: {quantidade_brasil:,}")
print(f"Representatividade: {representatividade:.2f}%")

print("\n--- Amostra dos IDs de País Encontrados ---")
# Exibe os IDs mais frequentes para verificação
print(df_all_athletes[CAMPO_ID].value_counts().head(5).to_markdown())

