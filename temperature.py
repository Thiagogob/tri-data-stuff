import pandas as pd
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import sys
import os
import seaborn as sns

# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")
from utils_itu import get_event_title, get_program_details

# --- 1. DEFINIÇÕES E FUNÇÕES AUXILIARES ---

# Caminhos
TEMPERATURE_CSV = Path('data') / "program_details" / "programa_temperatura_bruto.csv"
PROGRAM_RESULTS_DIR = Path('data') / "program_results"
PLOT_FILENAME = 'performance_vs_temperature_top5.png'
MIN_AVG_RUN_TIME_S = 25 * 60

# Índices
RUN_SPLIT_INDEX = 4
TARGET_PROG_NAME = 'standard' # O último item do array de 5 splits (0, 1, 2, 3, 4)

def str_to_seconds(time_str: str) -> float:
    """Converte 'HH:MM:SS' para segundos, de forma robusta."""
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

def seconds_to_m_s(seconds: float) -> str:
    """Converte segundos para MM:SS."""
    if np.isnan(seconds) or seconds < 0:
        return ""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f'{m:02d}:{s:02d}'

def get_distance_category_for_temp_analysis(row):
    """
    Busca a categoria de distância do programa usando get_program_details para garantir a precisão.
    É necessário que get_program_details esteja importada/disponível.
    """
    # event_id e prog_id vêm do DataFrame (df_temps) e são tratados como Int64/float
    event_id = row['event_id']
    prog_id = row['prog_id'] 

    if pd.isna(event_id) or pd.isna(prog_id):
        return None
    
    event_id_int = int(event_id)
    prog_id_int = int(prog_id)
    
    # Chama a função de detalhes do programa (com cache)
    # Assumindo que get_program_details está importada/disponível no ambiente principal
    details = get_program_details(event_id=event_id_int, prog_id=prog_id_int) 
    
    distance_category = details.get('prog_distance_category')

    if pd.isna(distance_category) or distance_category is None or distance_category == '':
        # O campo 'event_specifications' não está disponível no df_temps, 
        # mas a função get_program_details retorna o corpo do programa, 
        # que pode conter info para um fallback mais avançado, se necessário.
        
        # Para simplificar, neste contexto (df_temps), focamos apenas no prog_distance_category.
        # Se for nulo, retornamos None e o registro será filtrado, garantindo robustez.
        return None
    
    return distance_category

def get_avg_run_time_top5(row):
    """
    Carrega o arquivo de resultados correspondente e calcula o tempo médio de corrida 
    das 5 posições entre 5 e 9 (inclusive).
    """
    event_id = int(row['event_id'])
    prog_id = int(row['prog_id'])
    
    results_file = PROGRAM_RESULTS_DIR / f"event_{event_id}_prog_{prog_id}_results.json"
    
    if not results_file.exists():
        return np.nan
    
    try:
        with open(results_file, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            program_data = data.get('data', {}) 
            results_array = program_data.get('results', [])
        elif isinstance(data, list):
             results_array = data
        else:
             return np.nan

        if not results_array:
            return np.nan
            
        run_times_s = []
        
        # 🛑 FILTRO MODIFICADO: Posições 5, 6, 7, 8, 9
        POSITIONS_TO_ANALYZE = [5, 6, 7, 8, 9] 

        for result in results_array:
            position = int(result.get('position')) if pd.notna(result.get('position')) and str(result.get('position')).isdigit() else None
            splits = result.get('splits')
            
            # Aplica o novo filtro
            if position in POSITIONS_TO_ANALYZE and isinstance(splits, list) and len(splits) > RUN_SPLIT_INDEX:
                run_time_str = splits[RUN_SPLIT_INDEX]
                run_time_s = str_to_seconds(run_time_str)
                
                if not np.isnan(run_time_s) and run_time_s > 0:
                    run_times_s.append(run_time_s)
        
        # 4. Calcula a média e retorna
        if run_times_s:
            return np.mean(run_times_s)
        
        return np.nan
        
    except Exception as e:
        return np.nan

# --- 2. FUNÇÃO PRINCIPAL DE EXTRAÇÃO DE TEMPO DE CORRIDA ---


# --- 3. CARREGAMENTO E PROCESSAMENTO ---

print(f"--- Iniciando análise de Correlação: Temperatura vs. Performance ---")

try:
    df_temps = pd.read_csv(TEMPERATURE_CSV)
    # Garante que os IDs estão como inteiros antes de usar na função
    df_temps['event_id'] = pd.to_numeric(df_temps['event_id'], errors='coerce').astype('Int64')
    df_temps['prog_id'] = pd.to_numeric(df_temps['prog_id'], errors='coerce').astype('Int64')
    df_temps.dropna(subset=['humidity', 'event_id', 'prog_id'], inplace=True)
    df_temps = df_temps[df_temps['event_id'].notna() & df_temps['prog_id'].notna()] # Limpeza final
    
    df_temps['distance_category'] = df_temps.apply(get_distance_category_for_temp_analysis, axis=1)

    df_temps['distance_category'] = df_temps['distance_category'].str.lower().str.strip()
    df_temps = df_temps[df_temps['distance_category'] == 'standard'].copy()

    print(f"✅ Dados de temperatura carregados: {len(df_temps)} amostras válidas.")
except FileNotFoundError:
    print(f"❌ Erro: O arquivo de temperatura '{TEMPERATURE_CSV.name}' não foi encontrado. Por favor, gere-o primeiro.")
    exit()
except Exception as e:
    print(f"❌ Erro ao carregar/processar CSV: {e}")
    exit()


# Adiciona a coluna de tempo médio de corrida ao DataFrame de temperaturas
df_temps['avg_run_time_s'] = df_temps.apply(get_avg_run_time_top5, axis=1)

# Limpeza final: remove linhas onde o tempo médio de corrida não pôde ser calculado
df_final = df_temps.dropna(subset=['avg_run_time_s'])

df_final = df_final[df_final['avg_run_time_s'] >= MIN_AVG_RUN_TIME_S].copy()

print(f"Total de pontos para o gráfico (Temperatura + Tempo): {len(df_final)}")

# --- 4. GERAÇÃO DO GRÁFICO ---

if not df_final.empty:
    
    X = df_final['humidity']
    Y = df_final['avg_run_time_s']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 🛑 NOVO GRÁFICO: Seaborn regplot com ordem 2 (Quadrática)
    sns.regplot(x=X, y=Y, data=df_final, 
                order=2, # A regressão de 2º grau
                scatter_kws={'color': 'darkorange', 'alpha': 0.6},
                line_kws={'color': 'red'},
                ax=ax)
    
    # Configuração do Limite Y (0s a 3000s)
    ax.set_ylim([0, 3000])
    
    # Configuração do Eixo Y (Tempo)
    formatter = FuncFormatter(lambda y, pos: seconds_to_m_s(y))
    ax.yaxis.set_major_formatter(formatter)
    
    # Títulos
    ax.set_title('Impacto da Temperatura na Performance (Standard - Posições 5-9) - Ajuste Quadrático', fontsize=14)
    ax.set_xlabel('Temperatura do Ar (°C)', fontsize=12)
    ax.set_ylabel('Tempo Médio de Corrida (min:seg)', fontsize=12)
    
    # Informação da contagem
    ax.text(0.05, 0.95, f'Nº de Amostras: {len(df_final)}', 
            transform=ax.transAxes, 
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    PLOT_FILENAME = 'performance_vs_temperature_quadratic_fit.png'
    plt.savefig(PLOT_FILENAME)
    plt.close(fig)
    
    print(f"✅ Gráfico de Correlação Quadrática salvo como: {PLOT_FILENAME}")
    
else:
    print("⚠️ Não há dados suficientes para gerar o gráfico após a limpeza.")