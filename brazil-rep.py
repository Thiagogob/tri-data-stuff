import pandas as pd
import json
import os
import sys
from pathlib import Path

# --- CONFIGURAÇÃO DE CAMINHO ---
caminho_scripts = os.path.abspath('scripts')
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
# Importa a função (Assumindo que get_all_athletes está em utils_itu) 
# from utils_itu import get_all_athletes 

# --- DEFINIÇÕES GLOBAIS ---
ATHLETES_FILE = Path('data') / "all_athletes" / "all_athletes_full_list.json"
COUNTRY_ID_BRASIL = 127
CAMPO_ID = 'athlete_country_id'
# NOVO CAMINHO: Arquivo de saída para o Streamlit
REPRESENTATIVIDADE_CSV = Path('data') / "analysis" / "brasil_representatividade.csv"

# --- 1. CARREGAR DADOS ---
print(f"--- Carregando dados de eventos de: {ATHLETES_FILE.name} ---")

try:
    with open(ATHLETES_FILE, 'r') as f:
        all_athletes_list = json.load(f)
except FileNotFoundError:
    print(f"❌ Erro: O arquivo de dados '{ATHLETES_FILE.name}' não foi encontrado.")
    exit()
except json.JSONDecodeError:
    print("❌ Erro: Falha ao decodificar o arquivo JSON.")
    exit()

if not all_athletes_list:
    print("⚠️ Aviso: A lista de atletas está vazia.")
    exit()

df_all_athletes = pd.DataFrame(all_athletes_list)

# --- 2. CONTABILIZAÇÃO E CÁLCULO ---

df_all_athletes[CAMPO_ID] = pd.to_numeric(df_all_athletes[CAMPO_ID], errors='coerce')
total_atletas = len(df_all_athletes)
quantidade_brasil = len(df_all_athletes[df_all_athletes[CAMPO_ID] == COUNTRY_ID_BRASIL])
representatividade = (quantidade_brasil / total_atletas) * 100 if total_atletas > 0 else 0.0

# --- 3. SALVAMENTO EM CSV PARA O STREAMLIT (COM DADOS ADICIONAIS) ---

# Cria um DataFrame de sumário com todas as métricas solicitadas
df_sumario_brasil = pd.DataFrame({
    'Métrica': ['Total Atletas', 'Atletas Brasil', 'Representatividade (%)'],
    # Os valores são salvos como strings formatadas ou números, dependendo de como serão usados no Streamlit.
    # Usaremos números para facilitar cálculos futuros, exceto o percentual que manteremos a formatação.
    'Valor': [total_atletas, quantidade_brasil, round(representatividade, 2)] 
})

# Cria o diretório de análise se ele não existir
REPRESENTATIVIDADE_CSV.parent.mkdir(parents=True, exist_ok=True)
df_sumario_brasil.to_csv(REPRESENTATIVIDADE_CSV, index=False)

print(f"\n💾 Dados de representatividade salvos em: {REPRESENTATIVIDADE_CSV.name}")

# --- 4. EXIBIÇÃO DO RESULTADO ---

print("\n--- REPRESENTATIVIDADE DE ATLETAS BRASILEIROS ---")
print(f"Total de atletas na amostra: {total_atletas:,}")
print(f"Atletas brasileiros encontrados: {quantidade_brasil:,}")
print(f"Representatividade: {representatividade:.2f}%")

print("\n--- Amostra do DataFrame de Sumário Salvo ---")
print(df_sumario_brasil.to_markdown(index=False))