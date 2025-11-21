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


START_DATE_FILTER = '2018-01-01'
END_DATE_FILTER = '2024-12-31'

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
    

# --- CONFIGURAÇÃO DE CAMINHO E IMPORTS ---

# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")

# Tenta importar todas as funções necessárias (Assumindo que estão no seu utils_itu e utils_events)
from utils_itu import get_athlete_info, get_athlete_results, get_program_details



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

# 3. FILTRO DE DATA (INSERIDO AQUI)
start_date = pd.to_datetime(START_DATE_FILTER)
end_date = pd.to_datetime(END_DATE_FILTER)
df_filtered = df_filtered[(df_filtered['event_date'] >= start_date) & 
                          (df_filtered['event_date'] <= end_date)]

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

# --- 4. SALVAMENTO E VISUALIZAÇÃO FINAL ---

# A. Salvar o DataFrame completo e enriquecido
df_hidalgo_results.to_csv(FINAL_CSV_PATH, index=False)
print(f"\n💾 DataFrame final (com distance_category) salvo em: {FINAL_CSV_PATH.name}")

# B. Exibir a visualização organizada (todas as linhas)
target_columns_view = [
    'event_title', 
    'prog_name', 
    'distance_category', 
    'position', 
    'total_time'
]
df_organized = df_hidalgo_results[target_columns_view].copy()

print("\n################################################")
print(f"✅ VISUALIZAÇÃO ORGANIZADA: Resultados de {len(df_organized)} Provas")
print("################################################")
print(df_organized.to_markdown(index=False, numalign="left", stralign="left"))

df_plot = df_sorted.copy()
df_plot['total_time_s'] = df_plot['total_time'].apply(str_to_seconds)

# Converter a data de volta para datetime
df_plot['event_date'] = pd.to_datetime(df_plot['event_date'])

# FILTRAGEM (NOVO)
# 1. Remover valores NaN (inclui casos 'DNF', 'DSQ', tempos inválidos)
df_plot.dropna(subset=['total_time_s'], inplace=True)
# 2. Excluir tempos inferiores a 1 hora (3600 segundos)
df_plot = df_plot[df_plot['total_time_s'] >= 3600]


# --- 3. GERAÇÃO DO GRÁFICO ---

fig, ax = plt.subplots(figsize=(12, 6))

# A. Scatter Plot
ax.scatter(
    df_plot['event_date'], 
    df_plot['total_time_s'], 
    color='deepskyblue', 
    label='Tempo Total (Standard)', 
    zorder=3 
)

# B. Configuração do Eixo X (Datas)
date_format = mdates.DateFormatter('%Y/%m')
ax.xaxis.set_major_formatter(date_format)
ax.tick_params(axis='x', rotation=45)

# C. Configuração do Eixo Y (Tempo)
# Define uma função de formatação para converter segundos de volta para MM:SS
def seconds_to_h_m_s(x, pos):
    s = x
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    s = int(s % 60)
    # Mostra horas apenas se o tempo for >= 1 hora
    if h > 0:
        return f'{h:02d}:{m:02d}:{s:02d}'
    else:
        return f'{m:02d}:{s:02d}'

formatter = FuncFormatter(seconds_to_h_m_s)
ax.yaxis.set_major_formatter(formatter)

# D. Títulos e Grid
ax.set_title(f'Performance de {NOME_ATLETA} em Triathlons STANDARD (Tempos Válidos)', fontsize=14)
ax.set_xlabel('Data do Evento', fontsize=12)
ax.set_ylabel('Tempo Total (h:min:seg)', fontsize=12)
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend()

# Ajusta o layout para evitar cortes
plt.tight_layout()

# Salvar a imagem e exibir
plot_filename = 'vilaca_standard_performance_filtered.png'
plt.savefig(plot_filename)
plt.close(fig)

print(f"\nGráfico de desempenho (filtrado) salvo como: {plot_filename}")

df_reg = df_sorted.copy()
df_reg['total_time_s'] = df_reg['total_time'].apply(str_to_seconds)

df_reg['event_date_dt'] = pd.to_datetime(df_reg['event_date'])


df_reg.dropna(subset=['total_time_s'], inplace=True)
df_reg = df_reg[df_reg['total_time_s'] >= 3600].copy()

df_reg_agg = df_reg.groupby('event_date_dt', as_index=False)['total_time_s'].mean()
df_reg = df_reg_agg.rename(columns={'total_time_s': 'total_time_s_mean'}) # Renomeia para clareza

# B. Conversão da Data para Formato Numérico (Dias desde a primeira corrida)
df_reg['days_since_start'] = (df_reg['event_date_dt'] - df_reg['event_date_dt'].min()).dt.days

# --- 2. CÁLCULO DA REGRESSÃO LINEAR ---

X = df_reg['days_since_start']
Y = df_reg['total_time_s_mean']

# Executa a regressão
slope, intercept, r_value, p_value, std_err = linregress(X, Y)

# Calcula a linha de tendência (Y = a*X + b)
line_of_best_fit = slope * X + intercept

df_reg['line_of_best_fit'] = line_of_best_fit

# Define o caminho de salvamento para o DataFrame filtrado de regressão
REGRESSION_DATA_CSV = Path('data') / "athlete_results" / f"athlete_{ATHLETE_ID}_performance_trend.csv"

# Salva as colunas necessárias (Datas, Segundos e Linha de Tendência)
df_reg[['event_date_dt', 'total_time_s_mean', 'line_of_best_fit']].to_csv(REGRESSION_DATA_CSV, index=False)

print(f"\n💾 Dados de tendência salvos em: {REGRESSION_DATA_CSV.name}")

# --- 3. VISUALIZAÇÃO E INTERPRETAÇÃO ---

fig, ax = plt.subplots(figsize=(12, 6))

# Plota os dados brutos
ax.scatter(df_reg['event_date_dt'], df_reg['total_time_s_mean'], 
           label='Tempos Reais', color='deepskyblue', zorder=3)

# Plota a linha de tendência
ax.plot(df_reg['event_date_dt'], line_of_best_fit, 
        color='red', linestyle='--', linewidth=2, 
        label=f'Tendência (Inclinação: {slope*365.25:.2f} s/ano)') # Multiplica por 365.25 para ter a mudança anual

# Função de formatação do Eixo Y (Tempo)
def seconds_to_h_m_s(x, pos):
    s = x
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    s = int(s % 60)
    if h > 0:
        return f'{h:02d}:{m:02d}:{s:02d}'
    else:
        return f'{m:02d}:{s:02d}'

formatter = FuncFormatter(seconds_to_h_m_s)
ax.yaxis.set_major_formatter(formatter)

# Configuração do Eixo X (Datas)
date_format = mdates.DateFormatter('%Y/%m')
ax.xaxis.set_major_formatter(date_format)
ax.tick_params(axis='x', rotation=45)

# Títulos e Grid
ax.set_title(f'Tendência de Performance de {NOME_ATLETA} em Triathlons STANDARD', fontsize=14)
ax.set_xlabel('Data do Evento', fontsize=12)
ax.set_ylabel('Tempo Total', fontsize=12)
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend()
plt.tight_layout()

# Salvar o gráfico
plot_filename = 'vilaca_performance_trend.png'
plt.savefig(plot_filename)
plt.close(fig)


# --- 4. INTERPRETAÇÃO DA TENDÊNCIA ---
REGRESSION_SUMMARY_JSON = Path('data') / "athlete_results" / f"athlete_{ATHLETE_ID}_regressao_sumario.json"

# Converte a inclinação para mudança de segundos por ano
slope_annual_s = slope * 365.25

regressao_sumario = {
    'athlete_id': ATHLETE_ID,
    'nome_atleta': NOME_ATLETA,
    'slope_annual_s': slope_annual_s,
    'p_value': p_value,
    # Adicione outros metadados se necessário
}

# Salva o sumário em JSON
with open(REGRESSION_SUMMARY_JSON, 'w') as f:
    json.dump(regressao_sumario, f, indent=4)

print(f"\n💾 Sumário de regressão salvo em: {REGRESSION_SUMMARY_JSON.name}")

print(f"\nGráfico de tendência salvo como: {plot_filename}")
print("\n--- ANÁLISE DE REGRESSÃO ---")
print(f"Inclinação (Slope) por dia: {slope:.4f} segundos/dia")
print(f"Tendência Anual: {slope_annual_s:.2f} segundos/ano")
print(f"P-value: {p_value:.4f} (Mede a significância estatística)")
print("---------------------------\n")

if slope_annual_s < 0:
    print(f"✅ TENDÊNCIA: O tempo está DIMINUINDO. A performance de {NOME_ATLETA} está melhorando em média {abs(slope_annual_s):.2f} segundos por ano na distância Standard.")
elif slope_annual_s > 0:
    print(f"❌ TENDÊNCIA: O tempo está AUMENTANDO. A performance está piorando em média {slope_annual_s:.2f} segundos por ano na distância Standard.")
else:
    print("↔️ TENDÊNCIA: A performance está estável (inclinação zero).")