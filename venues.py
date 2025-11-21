import pandas as pd
import json
from pathlib import Path

# --- DEFINIÇÕES DE CAMINHO ---
DATA_DIR = Path('data')
# Nome do arquivo de todos os eventos (o mais recente da coleta total)
EVENTS_FILE = DATA_DIR / "all_events" / "all_events_2000_2026.json" 
TARGET_FIELD = 'event_country'

TOP3_COUNTRIES_CSV = DATA_DIR / "analysis" / "top3_countries_sede.csv"

# --- 1. CARREGAR DADOS ---
print(f"--- Carregando dados de eventos de: {EVENTS_FILE.name} ---")

try:
    with open(EVENTS_FILE, 'r') as f:
        all_events_list = json.load(f)
except FileNotFoundError:
    print(f"❌ Erro: O arquivo '{EVENTS_FILE.name}' não foi encontrado.")
    print("Por favor, execute a coleta total de eventos (get_all_events) primeiro.")
    exit()
except json.JSONDecodeError:
    print("❌ Erro: Falha ao decodificar o arquivo JSON. O arquivo pode estar corrompido.")
    exit()

if not all_events_list or not isinstance(all_events_list, list):
    print("⚠️ Aviso: A lista de eventos está vazia ou em formato inesperado.")
    exit()

df_all_events = pd.DataFrame(all_events_list)
print(f"✅ DataFrame carregado com {len(df_all_events)} eventos.")


# --- 2. CONTABILIZAÇÃO E CLASSIFICAÇÃO ---

if TARGET_FIELD not in df_all_events.columns:
    print(f"❌ Erro: Coluna '{TARGET_FIELD}' não encontrada no DataFrame.")
    print(f"Colunas disponíveis: {df_all_events.columns.tolist()}")
    exit()

# Contar a frequência de cada país
country_counts = df_all_events[TARGET_FIELD].value_counts()

# Obter o Top 3
top_3_countries_series = country_counts.head(3)


# --- 3. EXIBIÇÃO DO RESULTADO ---

print("\n#####################################################")
print("🏆 TOP 3 PAÍSES QUE MAIS SEDIARAM EVENTOS DE TRIATHLON")
print("#####################################################")

if not top_3_countries_series.empty:
    
    # Criar o diretório de análise se ele não existir
    TOP3_COUNTRIES_CSV.parent.mkdir(parents=True, exist_ok=True)
    
    # Converter a Série em DataFrame para salvar
    df_top3 = top_3_countries_series.reset_index()
    df_top3.columns = ['Country', 'Event_Count']
    
    # Salvar o DataFrame em CSV
    df_top3.to_csv(TOP3_COUNTRIES_CSV, index=False)
    
    print(f"💾 Dados do Top 3 salvos em: {TOP3_COUNTRIES_CSV.name}")

    for country, count in zip(df_top3['Country'], df_top3['Event_Count']):
        print(f"| 🥇 {country:<20}: {count} eventos")
    print("-----------------------------------------------------")
else:
    print("⚠️ Não foi possível determinar o Top 3 (Contagem vazia).")