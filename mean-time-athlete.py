import sys
import os
import pandas as pd
import json
from pathlib import Path
import numpy as np
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from scipy.stats import linregress


def str_to_seconds(time_str):
    """Converte 'HH:MM:SS' ou 'MM:SS' para segundos."""
    try:
        parts = str(time_str).split(':')
        if len(parts) == 3:
            h, m, s = map(float, parts)
        elif len(parts) == 2:
            h = 0
            m, s = map(float, parts)
        else:
            return np.nan
        return h * 3600 + m * 60 + s
    except:
        return np.nan
    
def str_to_seconds(time_str: str) -> float:
    """Converte 'HH:MM:SS' ou 'MM:SS' para segundos."""
    if not isinstance(time_str, str):
        return np.nan
    try:
        parts = time_str.split(':')
        h = 0
        if len(parts) == 3:
            h, m, s = map(float, parts)
        elif len(parts) == 2:
            m, s = map(float, parts)
        else:
            return np.nan
        return h * 3600 + m * 60 + s
    except ValueError:
        return np.nan

def seconds_to_h_m_s(seconds: float) -> str:
    """Converte segundos de volta para o formato HH:MM:SS."""
    if np.isnan(seconds) or seconds < 0:
        return ""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

MEDIAS_REFERENCIA_HMS = {
    'swim': "00:22:42",  # 22 minutos e 42 segundos
    'bike': "01:10:27",  # 1 hora, 10 minutos e 27 segundos
    'run': "00:40:55"   # 40 minutos e 55 segundos
}

MEDIAS_REFERENCIA_S = {
    esporte: str_to_seconds(hms) 
    for esporte, hms in MEDIAS_REFERENCIA_HMS.items()
}

# --- CONFIGURAÇÃO DE CAMINHO E IMPORTS ---

# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")

# Tenta importar todas as funções necessárias (Assumindo que estão no seu utils_itu e utils_events)
from utils_itu import get_athlete_info, get_athlete_results, get_program_details
from utils import load_config
from utils_events import get_events_categories, get_events_specifications


# --- DEFINIÇÕES GLOBAIS ---
NOME_ATLETA = "Vasco Vilaca"
ATHLETE_ID = 86042 
RESULTS_FILE = Path('data') / "athlete_results" / f"athlete_{ATHLETE_ID}_results.json"
FINAL_CSV_PATH = RESULTS_FILE.parent / f"athlete_{ATHLETE_ID}_results_final.csv"

# --- 1. FUNÇÃO DE ENRIQUECIMENTO DE DADOS (COM FALLBACK) ---

def get_distance_category(row):
    """
    Busca a categoria de distância do programa. Se estiver vazia, usa o 
    segundo elemento ('cat_name') de 'event_specifications' como fallback.
    """
    event_id = row['event_id']
    prog_id = row['prog_id'] 

    # 1. Tenta obter o prog_distance_category (valor original)
    if pd.isna(event_id) or pd.isna(prog_id):
        return None
    
    event_id_int = int(event_id)
    prog_id_int = int(prog_id)
    
    # Chama a função de detalhes do programa (com cache)
    details = get_program_details(event_id=event_id_int, prog_id=prog_id_int)
    
    # Valor principal (do programa)
    distance_category = details.get('prog_distance_category')

    # 2. Verifica se o valor é nulo/vazio (NaN)
    if pd.isna(distance_category) or distance_category is None or distance_category == '':
        
        # --- LÓGICA DE FALLBACK ---
        
        # O campo 'event_specifications' é retornado como string de JSON, precisa ser convertida
        event_specs_array = row.get('event_specifications')

        # Verifica se o campo é uma lista (ou None)
        if isinstance(event_specs_array, list) and len(event_specs_array) > 1:
            
            # Não use json.loads()! Use o array diretamente:
            fallback_cat_name = event_specs_array[1].get('cat_name')
            
            if fallback_cat_name:
                return fallback_cat_name
                
        # Removido o bloco try/except json.JSONDecodeError, pois agora verificamos se é lista.
                
        
        # Se o fallback falhar ou não for aplicável, retorna None
        return None 
    
    # 3. Se o valor original não era nulo, retorna ele
    return distance_category

# --- 2. FLUXO PRINCIPAL DE PROCESSAMENTO ---

print(f"--- Processando resultados de {NOME_ATLETA} para adicionar categoria de distância ---")

# A. Carregar ou Coletar o DataFrame de resultados do atleta
if RESULTS_FILE.exists():
    with open(RESULTS_FILE, 'r') as f:
        results_list = json.load(f)
    df_hidalgo_results = pd.DataFrame(results_list)
    print(f"DataFrame de resultados carregado com {len(df_hidalgo_results)} entradas.")
else:
    # Se o arquivo não existir, chama a coleta (assumindo que esta parte foi testada e funciona)
    print(f"⚠️ Arquivo {RESULTS_FILE.name} não encontrado. Iniciando coleta da API...")
    results_list = get_athlete_results(athlete_id=ATHLETE_ID)
    if not results_list:
        print("❌ Coleta da API falhou. Encerrando o processamento.")
        exit()
    df_hidalgo_results = pd.DataFrame(results_list)


# B. Aplicar a função para criar a nova coluna 'distance_category'
print("\nIniciando busca de 'distance_category' (com fallback) para cada resultado...")
df_hidalgo_results['distance_category'] = df_hidalgo_results.apply(
    get_distance_category, 
    axis=1 
)

print("\n\n#############################################")
print(f"✅ PROCESSAMENTO CONCLUÍDO. Coluna 'distance_category' adicionada.")
print(f"Total de resultados processados: {len(df_hidalgo_results)}")
print("#############################################")


# --- 3. FILTRAGEM, ORDENAÇÃO E EXIBIÇÃO DE 'STANDARD' ---
df_hidalgo_results['distance_category'] = (
    df_hidalgo_results['distance_category']
    .str.lower()   # Converte para minúsculas
    .str.strip()   # Remove espaços em branco antes/depois
)



df = df_hidalgo_results



# 1. Filtrar pela categoria 'standard'
df_standard = df[df['distance_category'] == 'standard'].copy()

# 2. Selecionar e preparar colunas para ordenação
df_filtered = df_standard[['total_time', 'event_date', 'position']].copy()
df_filtered['event_date'] = pd.to_datetime(df_filtered['event_date'])

# 3. Ordenar pela data, da mais antiga à mais recente (ascendente)
df_sorted = df_filtered.sort_values(by='event_date', ascending=True)

# 4. Converter o Timestamp de volta para string para serialização JSON
df_sorted['event_date'] = df_sorted['event_date'].dt.strftime('%Y-%m-%d')

# 5. Converter o DataFrame ordenado para um array/lista de registros (dicionários)
results_array = df_sorted.to_dict('records')

# --- Exibir o Resultado 'Standard' (JSON) ---
print("\n#############################################")
print(f"✅ Resultados 'Standard' (Ordenados por Data): {len(results_array)} entradas")
print("#############################################")
print(json.dumps(results_array, indent=2))

# Continuação do script, usando df_hidalgo_results

# --- 1. DEFINIÇÕES E PREPARAÇÃO DO DATAFRAME ---

# --- DEFINIÇÕES GLOBAIS ---

RESULTS_FILE = Path('data') / "athlete_results" / f"athlete_{ATHLETE_ID}_results.json"

# Disciplinas e seus índices no array 'splits' da API
INDICES_ESPORTES = {
    'swim': 0,
    'bike': 2,
    'run': 4
}
DISCIPLINAS = list(INDICES_ESPORTES.keys())


# A função get_distance_category (e os imports de utils_itu) são necessários para carregar o df_hidalgo_results corretamente.
# Assumindo que o código anterior foi executado e df_hidalgo_results está disponível, ou que o CSV final foi salvo.
# Se o CSV final foi salvo (que contém 'distance_category'), usaremos ele para simplificar o carregamento:
FINAL_PROCESSED_CSV = RESULTS_FILE.parent / f"athlete_{ATHLETE_ID}_results_final.csv"

# --- 1. CARREGAMENTO E FILTRAGEM ---

try:
    # Tenta carregar o DataFrame final que já foi enriquecido
    df_hidalgo_results = pd.read_csv(FINAL_PROCESSED_CSV)
except FileNotFoundError:
    print(f"❌ Erro: O arquivo processado '{FINAL_PROCESSED_CSV.name}' não foi encontrado.")
    print("Por favor, execute o script anterior de enriquecimento de dados (com get_distance_category) primeiro.")
    exit()

# Filtrar apenas pela distância 'standard'
df_standard_results = df_hidalgo_results[
    df_hidalgo_results['distance_category'] == 'standard'
].copy()

if df_standard_results.empty:
    print("⚠️ Aviso: Não foram encontrados resultados 'standard' válidos após o carregamento.")
    exit()

PROG_ID_BLACKLIST = [655049, 580918, 453982, 337834, 337817, 500613, 477469, 493231, 501764, 338168, 265540, 338762]

# --- 2. EXTRAÇÃO E CONVERSÃO DOS SPLITS (TODOS JUNTOS) ---

tempos_acumulados = {disc: [] for disc in DISCIPLINAS}
total_provas_validas = 0

for index, row in df_standard_results.iterrows():
    
    # 🛑 NOVO FILTRO: Excluir provas da Blacklist
    prog_id = row.get('prog_id')
    if prog_id in PROG_ID_BLACKLIST:
        print(f"🚫 EXCLUÍDO: {row.get('event_title', 'Evento Desconhecido')} | Motivo: prog_id {prog_id} na Blacklist.")
        continue # Pula para a próxima iteração
        
    splits = row.get('splits')
    event_title = row.get('event_title') 
    
    # O campo 'splits' foi salvo como string no CSV, precisamos converter para lista
    if isinstance(splits, str):
        try:
            # Converte a string de lista para lista Python
            splits = json.loads(splits.replace("'", '"')) 
        except json.JSONDecodeError:
             continue
    
    if not isinstance(splits, list) or len(splits) < 5:
        continue

    # Validação Cruzada: TUDO OU NADA
    valid_splits = {}
    is_valid_race = True

    for esporte, indice in INDICES_ESPORTES.items():
        tempo_str = splits[indice]
        tempo_s = str_to_seconds(tempo_str)
        
        if np.isnan(tempo_s) or tempo_s <= 0:
            is_valid_race = False
            break
        
        valid_splits[esporte] = tempo_s
    
    if is_valid_race:
        # Bloco de Inspeção (Mantido para verificação)
        swim_time = seconds_to_h_m_s(valid_splits['swim'])
        bike_time = seconds_to_h_m_s(valid_splits['bike'])
        run_time = seconds_to_h_m_s(valid_splits['run'])
        
        print(f"✅ INCLUÍDO: {event_title:<45} | N: {swim_time} | B: {bike_time} | C: {run_time}")
        
        total_provas_validas += 1
        for esporte, tempo in valid_splits.items():
            tempos_acumulados[esporte].append(tempo)


# --- 3. CÁLCULO DAS MÉDIAS GERAIS (RESTANTE DO CÓDIGO) ---
# ... (código de cálculo e exibição de médias)


# --- 3. CÁLCULO DAS MÉDIAS GERAIS ---

medias_finais = {}
print("\n--- MÉDIAS GERAIS DE TEMPO DE MIGUEL HIDALGO (Standard Distance) ---")
print(f"Total de provas Standard válidas contabilizadas: {total_provas_validas:,}")
print("------------------------------------------------------------------")

for esporte in DISCIPLINAS:
    tempos = tempos_acumulados[esporte]
    
    if tempos:
        media_s = np.mean(tempos)
        media_hms = seconds_to_h_m_s(media_s)
        
        medias_finais[esporte] = {
            'media_segundos': media_s,
            'media_hms': media_hms,
            'contagem': len(tempos)
        }
        print(f"Média de Tempo na Etapa de {esporte.upper():<5}: {media_hms} ({len(tempos):,} amostras)")
    else:
        print(f"Média de Tempo na Etapa de {esporte.upper():<5}: N/A (0 amostras)")

# --- 4. EXIBIÇÃO FINAL ---

df_medias = pd.DataFrame(medias_finais).T
df_medias.index.name = 'etapa'
print("\nDataFrame das Médias Finais:")
print(df_medias)
MEDIAS_CSV_PATH = RESULTS_FILE.parent / f"athlete_{ATHLETE_ID}_medias_standard.csv"

# Salva o DataFrame final em CSV
df_medias.to_csv(MEDIAS_CSV_PATH)

print(f"\n💾 Médias de tempo salvas em: {MEDIAS_CSV_PATH.name}")

# --- 5. COMPARAÇÃO COM A MÉDIA GERAL DO ESPORTE ---

print("\n\n--- ANÁLISE DE VANTAGEM INDIVIDUAL ---")
print(f"ATLETA (Média Standard): {NOME_ATLETA}")
print("MÉDIA GERAL DO ESPORTE:  (00:22:42 / 01:10:27 / 00:40:55)")
print("------------------------------------------------------------------")

comparacao_percentual = {}

for esporte in DISCIPLINAS:
    
    media_hidalgo_s = medias_finais.get(esporte, {}).get('media_segundos')
    media_referencia_s = MEDIAS_REFERENCIA_S.get(esporte)
    
    if media_hidalgo_s and media_referencia_s and media_referencia_s > 0:
        
        # Para calcular a vantagem percentual de tempo:
        # Vantagem % = (Tempo_Referência - Tempo_Atleta) / Tempo_Referência * 100
        # Se o resultado for positivo, o atleta é X% mais rápido.
        vantagem_s = media_referencia_s - media_hidalgo_s
        vantagem_percentual = (vantagem_s / media_referencia_s) * 100
        
        comparacao_percentual[esporte] = {
            'vantagem_s': vantagem_s,
            'vantagem_percentual': vantagem_percentual
        }
        
        # Formatação da saída
        if vantagem_percentual > 0:
            status = "MELHOR"
        elif vantagem_percentual < 0:
            status = "PIOR"
        else:
            status = "IGUAL"
            
        print(f"[{esporte.upper():<5}] | Vantagem: {status:<5} ({abs(vantagem_percentual):.2f}% mais rápido/lento)")
    else:
        print(f"[{esporte.upper():<5}] | Não foi possível comparar (Dados faltantes).")

print("------------------------------------------------------------------")

# --- O restante do seu código (Exibição da média final do DF) deve ser mantido abaixo. ---