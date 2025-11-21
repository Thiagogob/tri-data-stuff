import pandas as pd
import json
from pathlib import Path
import os
import numpy as np
import sys
# --- CONFIGURAÇÃO E IMPORTS ---
# Adicionar importação da nova função
sys.path.append(os.path.abspath('scripts'))
from utils_itu import fetch_and_cache_program_details

PROGRAM_RESULTS_DIR = Path('data') / "program_results"
total_arquivos_processados = 0
total_detalhes_coletados = 0

print(f"--- Iniciando Coleta de Detalhes de Programa Faltantes ---")

# --- 1. LOOP SOBRE OS ARQUIVOS DA PASTA program_results ---

for result_file in PROGRAM_RESULTS_DIR.glob("event_*_prog_*_results.json"):
    
    total_arquivos_processados += 1
    
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
            
        if not data or not isinstance(data, dict):
            continue
            
        # 2. EXTRAÇÃO DOS IDs (do arquivo de resultados)
        
        # O arquivo de resultados (program_results) tem a estrutura { "data": { ... } }
        program_data = data.get('data', {}) 
        
        event_id = program_data.get('event_id')
        prog_id = program_data.get('prog_id')
        
        # O ID deve ser um inteiro para ser usado na URL
        if event_id and prog_id:
            event_id = int(event_id)
            prog_id = int(prog_id)
        else:
            continue
            
        # 3. CHAMADA À NOVA FUNÇÃO (Cache/Requisição)
        
        details = fetch_and_cache_program_details(event_id=event_id, prog_id=prog_id)
        
        if details:
            total_detalhes_coletados += 1
            
    except json.JSONDecodeError:
        # print(f"❌ Erro de JSONDecode em: {result_file.name}")
        continue
    except Exception as e:
        # print(f"❌ Erro ao processar arquivo {result_file.name}: {e}")
        continue

# --- 4. EXIBIÇÃO DE STATUS ---

print("\n#########################################################")
print("✅ Coleta de Detalhes do Programa (program_details) Concluída.")
print(f"Total de arquivos de resultados inspecionados: {total_arquivos_processados:,}")
print(f"Total de Detalhes de Programa Coletados/Atualizados: {total_detalhes_coletados:,}")
print("#########################################################")