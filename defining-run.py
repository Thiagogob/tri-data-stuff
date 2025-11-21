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
from utils_itu import get_event_title, get_program_details

# A função str_to_seconds DEVE estar definida no seu script. 
# Reutilizamos a versão robusta:
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

def get_distance_category(row):
    """
    Busca a categoria de distância do programa. Se estiver vazia, usa o 
    segundo elemento ('cat_name') de 'event_specifications' como fallback.
    """
    # É necessário que get_program_details esteja importada/disponível
    # from utils_itu import get_program_details
    event_id = row['event_id']
    prog_id = row['prog_id'] 

    if pd.isna(event_id) or pd.isna(prog_id):
        return None
    
    event_id_int = int(event_id)
    prog_id_int = int(prog_id)
    
    # Chama a função de detalhes do programa (com cache)
    # Assumindo que 'get_program_details' está importada/disponível
    details = get_program_details(event_id=event_id_int, prog_id=prog_id_int) 
    
    distance_category = details.get('prog_distance_category')

    if pd.isna(distance_category) or distance_category is None or distance_category == '':
        event_specs_array = row.get('event_specifications')

        if isinstance(event_specs_array, list) and len(event_specs_array) > 1:
            fallback_cat_name = event_specs_array[1].get('cat_name')
            if fallback_cat_name:
                return fallback_cat_name
        return None 
    
    return distance_category

# --- DEFINIÇÕES DE CAMINHO E FILTRO ---
PROGRAM_RESULTS_DIR = Path('data') / "program_results"
TARGET_PROGRAM_NAME = "Elite Men"
TARGET_DISTANCE = "standard"
SPLIT_INDICES_UNTIL_RUN = [0, 1, 2, 3] # Swim (0), T1 (1), Bike (2), T2 (3)

# Lista para armazenar os dados de cada evento
all_analysis_data = []

# --- 2. LOOP PRINCIPAL SOBRE OS ARQUIVOS ---

print(f"--- Iniciando análise: Vitórias decididas na corrida ({TARGET_PROGRAM_NAME}) ---")

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
            
        # 3. FILTRAR POR "ELITE MEN" E EXTRAIR METADADOS
        
        # Assume que o nome do programa está no objeto program_data (um dicionário)
        prog_name = program_data.get('prog_name', 'N/A')
        event_id = program_data.get('event_id')
        prog_id = program_data.get('prog_id')
        
        if prog_name != TARGET_PROGRAM_NAME:
            continue

        # Cria um objeto temporário para a linha, para usar a função get_distance_category
        temp_row = {
            'event_id': event_id, 
            'prog_id': prog_id, 
            # O campo event_specifications é necessário para o fallback
            'event_specifications': program_data.get('event_categories') # A API retorna o spec. do evento aqui
        }
        
        distance_category = get_distance_category(temp_row)
        
        # Normaliza a categoria e aplica o filtro
        if distance_category:
            distance_category = str(distance_category).lower().strip()
            if distance_category != TARGET_DISTANCE:
                continue
        else:
            continue # Se não conseguirmos determinar a distância, ignoramos.
        
        if not event_id:
            event_title = 'ID Faltante'
        else:
            # 🛑 NOVO PASSO: CHAMAR A FUNÇÃO PARA OBTER O TÍTULO CORRETO (com cache)
            #event_title = get_event_title(event_id=event_id)
            event_title = 'dr.'
        # 4. ENCONTRAR OS DOIS PRIMEIROS COLOCADOS
        
        # Filtra os resultados que têm posição 1 ou 2
        top_two_results = {
            result.get('position'): result 
            for result in results_array 
            if result.get('position') in [1, 2]
        }
        
        # Verifica se temos o primeiro e o segundo (ambos precisam existir)
        if 1 not in top_two_results or 2 not in top_two_results:
            # print(f"⚠️ Ignorando {event_title}: Faltando 1º ou 2º colocado.")
            continue
            
        result_winner = top_two_results[1]
        result_second = top_two_results[2]
        
        # 5. CALCULAR O TEMPO ACUMULADO ATÉ T2 (Sem a Corrida)
        
        def calculate_time_until_t2(result):
            splits = result.get('splits', [])
            if not isinstance(splits, list) or len(splits) < 4:
                return np.nan # Menos de 4 splits significa que a corrida não pode ser avaliada
            
            time_s = 0
            # Soma Swim(0), T1(1), Bike(2), T2(3)
            for i in SPLIT_INDICES_UNTIL_RUN:
                split_time_str = splits[i]
                split_time_s = str_to_seconds(split_time_str)
                
                # Se qualquer split for inválido/DNF, a soma é inválida
                if np.isnan(split_time_s): 
                    return np.nan
                    
                time_s += split_time_s
            return time_s

        time_until_t2_winner = calculate_time_until_t2(result_winner)
        time_until_t2_second = calculate_time_until_t2(result_second)
        
        
        # 6. VERIFICAR A CONDIÇÃO E REGISTRAR
        
        if np.isnan(time_until_t2_winner) or np.isnan(time_until_t2_second):
            # print(f"⚠️ Ignorando {event_title}: Splits até T2 incompletos ou inválidos.")
            continue
            
        # CONDIÇÃO CRUCIAL:
        # Ganhou na corrida (1) se o tempo acumulado do 2º for MENOR ou IGUAL ao do 1º.
        # Se 2º chegou primeiro na T2, o 1º teve que vencer na corrida.
        ganhou_na_corrida = 0
        if time_until_t2_second <= time_until_t2_winner:
            ganhou_na_corrida = 1
        
        # 7. REGISTRO DE DADOS
        
        all_analysis_data.append({
            'event_id': program_data.get('event_id'),
            'prog_id': prog_id,
            'event_title': event_title,
            'time_t2_winner_s': time_until_t2_winner,
            'time_t2_second_s': time_until_t2_second,
            'time_diff_s': time_until_t2_second - time_until_t2_winner, # Negativo = 2º estava à frente
            'ganhou_na_corrida': ganhou_na_corrida
        })
        
        # print(f"✅ Processado {event_title}: Ganhou na Corrida? {ganhou_na_corrida}")

    except json.JSONDecodeError:
        print(f"❌ Erro de JSONDecode em: {result_file.name}")
    except Exception as e:
        print(f"❌ Erro ao processar arquivo {result_file.name}: {e}")

# --- 8. CRIAÇÃO E EXIBIÇÃO DO DATAFRAME FINAL ---

df_final_analysis = pd.DataFrame(all_analysis_data)

CORRIDA_ANALYSIS_CSV = Path('data') / "program_results" / "vitorias_na_corrida_elite_men.csv"

print("\n#####################################################")
print("📊 ANÁLISE: VITÓRIAS DECIDIDAS NA CORRIDA (Elite Men)")
print("#####################################################")

if not df_final_analysis.empty:
    
    # Contagem final
    total_eventos = len(df_final_analysis)
    vitorias_na_corrida = df_final_analysis['ganhou_na_corrida'].sum()
    porcentagem_corrida = (vitorias_na_corrida / total_eventos) * 100
    
    print(f"Total de eventos Elite Men analisados: {total_eventos}")
    print(f"Vitórias decididas na corrida: {vitorias_na_corrida}")
    print(f"Frequência de vitórias decididas na corrida: {porcentagem_corrida:.2f}%")
    
    print("\n--- Amostra do DataFrame de Análise ---")
    print(df_final_analysis[['event_title', 'time_diff_s', 'ganhou_na_corrida']].head().to_markdown(index=False))
    
else:
    print("⚠️ Nenhum evento 'Elite Men' válido encontrado para análise.")