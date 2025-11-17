import pandas as pd
import json
from pathlib import Path
import os
import numpy as np

# --- 1. FUNÇÕES DE CONVERSÃO E VALIDAÇÃO ---

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
        return np.nan # Retorna NaN para 'DNF', 'DSQ' ou outros não-numéricos

def seconds_to_h_m_s(seconds: float) -> str:
    """Converte segundos de volta para o formato HH:MM:SS."""
    if np.isnan(seconds) or seconds < 0:
        return ""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

# --- 2. CONFIGURAÇÃO E DEFINIÇÕES ---

PROGRAM_RESULTS_DIR = Path('data') / "program_results"
LIMITE_TEMPO_TOTAL_S = 1 * 3600 + 10 * 60 # 4200 segundos (1h e 10min)

# Índices do array 'splits'
INDICES_ESPORTES = {
    'swim': 0,
    'bike': 2,
    'run': 4
}

# Listas para acumular todos os tempos válidos em segundos
tempos_acumulados = {
    'swim': [],
    'bike': [],
    'run': []
}
total_resultados_validos = 0
total_arquivos_processados = 0

print(f"--- Iniciando Contabilização das Médias por Etapa ---")
print(f"Filtro: Apenas resultados com 'total_time' superior a {seconds_to_h_m_s(LIMITE_TEMPO_TOTAL_S)}")
print("------------------------------------------------------")

# --- 3. LOOP PRINCIPAL SOBRE OS ARQUIVOS ---

for result_file in PROGRAM_RESULTS_DIR.glob("event_*_prog_*_results.json"):
    
    total_arquivos_processados += 1
    

    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        # O campo 'data' pode ser a própria lista de resultados se a função de coleta limpou o envelope,
        # mas aqui assumimos que a lista de resultados está dentro da chave 'results'
# O campo 'data' pode ser a própria lista de resultados se a função de coleta limpou o envelope,
        # mas aqui assumimos que a lista de resultados está dentro da chave 'results'
        if isinstance(data, dict):
            
            # --- CORREÇÃO AQUI ---
            # Tenta obter o objeto 'data' (que contém os detalhes do programa e a lista 'results')
            program_data = data.get('data', {}) 
            
            # Tenta obter a array 'results' desse objeto. Se falhar, usa a lista vazia.
            results_array = program_data.get('results', [])
            
        elif isinstance(data, list):
             # Isso lidaria com arquivos salvos como listas puras, sem o envelope.
             results_array = data
        else:
             continue # Ignora formatos inválidos

        if not results_array:
            continue
            
        # 4. ITERAÇÃO SOBRE OS RESULTADOS DO EVENTO
        for result in results_array:
            
            total_time_str = result.get('total_time')
            print(total_time_str)
            splits = result.get('splits')
            
            # Validação 1: Ignora se o tempo total for nulo ou inválido
            if not total_time_str or total_time_str in ["DNF", "DSQ", "LAP", "DNS"]:
                continue
                
            total_time_s = str_to_seconds(total_time_str)
            # Validação 2: Aplica o filtro de 1h e 10min
            if total_time_s <= LIMITE_TEMPO_TOTAL_S:
                continue

            # Validação 3: Garante que 'splits' é uma lista e tem tamanho suficiente (pelo menos 5 elementos para os índices 0, 2, 4)
            if not isinstance(splits, list) or len(splits) < 5:
                 continue
# 5. EXTRAÇÃO E VALIDAÇÃO CRUZADA (NOVO BLOCO)
            valid_splits = {}
            is_valid_race = True


            total_resultados_validos += 1
            
            for esporte, indice in INDICES_ESPORTES.items():
                tempo_str = splits[indice]
                tempo_s = str_to_seconds(tempo_str)
                
                # Verifica se o tempo é válido, não-zero, e não-NaN.
                # Se qualquer split falhar, a prova é marcada como inválida.
                if np.isnan(tempo_s) or tempo_s <= 0:
                    is_valid_race = False
                    break
                
                valid_splits[esporte] = tempo_s
            
            # REGRA TUDO OU NADA: Se a prova for válida em todas as etapas, acumula os tempos
            if is_valid_race:
                total_resultados_validos += 1
                for esporte, tempo in valid_splits.items():
                    tempos_acumulados[esporte].append(tempo)
                    
    except json.JSONDecodeError:
        print(f"❌ Erro de JSONDecode em: {result_file.name}")
    except Exception as e:
        print(f"❌ Erro ao processar {result_file.name}: {e}")

# --- 6. CÁLCULO DAS MÉDIAS FINAIS ---

medias_finais = {}
print("\n--- RESULTADO FINAL DA ANÁLISE ---")
print(f"Total de arquivos de resultados processados: {total_arquivos_processados}")
print(f"Total de resultados de atletas válidos (após filtro): {total_resultados_validos:,}")
print("-----------------------------------")

for esporte, tempos in tempos_acumulados.items():
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

# Opcional: Converter o resultado final para um DataFrame para fácil análise
df_medias = pd.DataFrame(medias_finais).T
df_medias.index.name = 'etapa'
print("\nDataFrame das Médias Finais:")
print(df_medias)