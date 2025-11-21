import pandas as pd
import json
from pathlib import Path
import numpy as np
import sys
import os

# Define o caminho absoluto para a pasta 'scripts'
caminho_scripts = os.path.abspath('scripts')

# Adiciona o caminho ao sys.path, se ainda não estiver lá
if caminho_scripts not in sys.path:
    sys.path.append(caminho_scripts)
    print(f"✅ Diretório adicionado ao sys.path: {caminho_scripts}")

# Tenta importar as funções necessárias (Assumindo que estão no seu utils_itu)
from utils_itu import get_event_title, get_program_details 

# --- FUNÇÕES AUXILIARES (Tempo) ---

def str_to_seconds(time_str: str) -> float:
    """Converte 'HH:MM:SS' ou 'MM:SS' para segundos, de forma robusta."""
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


# --- DEFINIÇÕES DE CAMINHO E FILTRO ---
PROGRAM_RESULTS_DIR = Path('data') / "program_results"
SPLIT_INDICES_UNTIL_RUN = [0, 1, 2, 3] # Swim (0), T1 (1), Bike (2), T2 (3)

# Listas globais para armazenamento de dados
all_analysis_data = [] # Dados da análise de vitória
all_t1_times = [] # Tempos de T1 dos vencedores
all_t2_times = [] # Tempos de T2 dos vencedores

# Novo caminho para o CSV de sumário Global
CORRIDA_ANALYSIS_CSV_GLOBAL = Path('data') / "analysis" / "vitorias_na_corrida_global.csv"

# --- 2. LOOP PRINCIPAL SOBRE OS ARQUIVOS ---

print(f"--- Iniciando análise GLOBAL: Vitórias decididas na corrida (TODOS EVENTOS) ---")

for result_file in PROGRAM_RESULTS_DIR.glob("event_*_prog_*_results.json"):
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        # Lógica de extração do array 'results' (incluindo o envelope 'data')
        if isinstance(data, dict):
            program_data = data.get('data', {}) 
            results_array = program_data.get('results', [])
        elif isinstance(data, list):
             results_array = data
        else:
             continue 

        if not results_array:
            continue
            
        # 3. EXTRAIR METADADOS E ENCONTRAR VENCEDORES
        prog_name = program_data.get('prog_name', 'N/A')
        event_id = program_data.get('event_id')
        prog_id = program_data.get('prog_id')

        # Obter o event_title (manteremos o placeholder 'prog_name' para este script)
        event_title = prog_name 
        
        # Encontrar os dois primeiros colocados
        top_two_results = {
            result.get('position'): result 
            for result in results_array 
            if result.get('position') in [1, 2]
        }
        
        if 1 not in top_two_results or 2 not in top_two_results:
            continue
            
        result_winner = top_two_results[1]
        result_second = top_two_results[2]
        
        # 4. CAPTURA E ARMAZENAMENTO DE T1 E T2 (Vencedor)
        
        winner_splits = result_winner.get('splits', [])
        
        if isinstance(winner_splits, list) and len(winner_splits) > 3:
            
            t1_time_str = winner_splits[1] # Índice 1 = T1
            t2_time_str = winner_splits[3] # Índice 3 = T2
            
            t1_time_s = str_to_seconds(t1_time_str)
            t2_time_s = str_to_seconds(t2_time_str)
            
            # Armazena apenas se o tempo for válido (> 0 e não NaN)
            if not np.isnan(t1_time_s) and t1_time_s > 0:
                all_t1_times.append(t1_time_s)
                
            if not np.isnan(t2_time_s) and t2_time_s > 0:
                all_t2_times.append(t2_time_s)
        
        # 5. CALCULAR O TEMPO ACUMULADO ATÉ T2 (Para Análise de Corrida)
        
        def calculate_time_until_t2(result):
            splits = result.get('splits', [])
            if not isinstance(splits, list) or len(splits) < 4:
                return np.nan 
            
            time_s = 0
            for i in SPLIT_INDICES_UNTIL_RUN:
                split_time_str = splits[i]
                split_time_s = str_to_seconds(split_time_str)
                
                if np.isnan(split_time_s): 
                    return np.nan
                    
                time_s += split_time_s
            return time_s

        time_until_t2_winner = calculate_time_until_t2(result_winner)
        time_until_t2_second = calculate_time_until_t2(result_second)
        
        
        # 6. VERIFICAR A CONDIÇÃO E REGISTRAR
        
        if np.isnan(time_until_t2_winner) or np.isnan(time_until_t2_second):
            continue
            
        # CONDIÇÃO CRUCIAL: Ganhou na corrida (1) se o tempo acumulado do 2º for MENOR ou IGUAL ao do 1º.
        ganhou_na_corrida = 0
        if time_until_t2_second <= time_until_t2_winner:
            ganhou_na_corrida = 1
        
        # 7. REGISTRO DE DADOS DA ANÁLISE DE VITÓRIA
        
        all_analysis_data.append({
            'event_id': program_data.get('event_id'),
            'prog_id': prog_id,
            'event_title': event_title,
            'time_t2_winner_s': time_until_t2_winner,
            'time_t2_second_s': time_until_t2_second,
            'time_diff_s': time_until_t2_second - time_until_t2_winner,
            'ganhou_na_corrida': ganhou_na_corrida
        })

    except json.JSONDecodeError:
        print(f"❌ Erro de JSONDecode em: {result_file.name}")
    except Exception as e:
        print(f"❌ Erro ao processar arquivo {result_file.name}: {e}")

# --- 8. CÁLCULO DAS MÉDIAS DE TRANSIÇÃO E SUMÁRIO FINAL ---

df_final_analysis = pd.DataFrame(all_analysis_data)

print("\n#####################################################")
print("📊 ANÁLISE GLOBAL: VITÓRIAS DECIDIDAS NA CORRIDA")
print("#####################################################")

if not df_final_analysis.empty:
    
    # A. Sumário da Análise de Vitória
    total_eventos = len(df_final_analysis)
    vitorias_na_corrida = df_final_analysis['ganhou_na_corrida'].sum()
    porcentagem_corrida = (vitorias_na_corrida / total_eventos) * 100
    
    # B. Cálculo das Médias de Transição
    if all_t1_times and all_t2_times:
        avg_t1_s = np.mean(all_t1_times)
        avg_t2_s = np.mean(all_t2_times)
        
        avg_t1_hms = seconds_to_h_m_s(avg_t1_s)
        avg_t2_hms = seconds_to_h_m_s(avg_t2_s)
        
        print("\n--- MÉDIA DE TEMPOS DE TRANSIÇÃO (Vencedores) ---")
        print(f"Média T1 (Natação -> Bike): {avg_t1_hms}")
        print(f"Média T2 (Bike -> Corrida): {avg_t2_hms}")
        print("--------------------------------------------------")
    else:
        avg_t1_hms, avg_t2_hms = "N/A", "N/A"
    
    # C. Criar um DataFrame de sumário para Streamlit
    df_summary = pd.DataFrame({
        'Métrica': ['Total Eventos Analisados', 'Vitórias Decididas na Corrida', 'Frequência %', 'Média T1', 'Média T2'],
        'Valor': [total_eventos, vitorias_na_corrida, f"{porcentagem_corrida:.2f}%", avg_t1_hms, avg_t2_hms]
    })
    
    # D. Salvar o sumário em CSV para o Streamlit
    CORRIDA_ANALYSIS_CSV_GLOBAL.parent.mkdir(parents=True, exist_ok=True)
    df_summary.to_csv(CORRIDA_ANALYSIS_CSV_GLOBAL, index=False)
    
    print(f"\nTotal de eventos analisados: {total_eventos}")
    print(f"Frequência de vitórias decididas na corrida (GLOBAL): {porcentagem_corrida:.2f}%")
    print(f"💾 Dados do sumário GLOBAL salvos em: {CORRIDA_ANALYSIS_CSV_GLOBAL.name}")
    
else:
    print("⚠️ Nenhum evento válido encontrado para análise.")