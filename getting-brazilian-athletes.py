import sys
import os
import pandas as pd
# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")

# Tenta importar novamente
from utils_itu import get_athlete_info, find_athlete_id_by_name, get_athletes_by_country_id # Teste para utils_itu
from utils import load_config # Teste para utils



COUNTRY_ID_BRA = 127

# 1. Busca os atletas
atletas_brasileiros = get_athletes_by_country_id(country_id=COUNTRY_ID_BRA)

if atletas_brasileiros:
    df_atletas_bra = pd.DataFrame(atletas_brasileiros)
    
    print("\n--- Resultados Finais ---")
    print(f"Total de Atletas Brasileiros encontrados: {len(df_atletas_bra)}")
    
    # Exibe a amostra (ajuste as colunas se 'athlete_yob' não for a correta)
    try:
        print(df_atletas_bra[['athlete_id', 'athlete_title', 'athlete_yob', 'athlete_gender']].head(15))
    except KeyError as e:
         print(f"⚠️ Aviso de KeyError: {e}. As colunas da API podem variar. Exibindo as primeiras linhas do DataFrame:")
         print(df_atletas_bra.head())
else:
    print("Nenhum atleta encontrado.")