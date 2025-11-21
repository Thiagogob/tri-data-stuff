import json
from pathlib import Path
from typing import Optional
import requests  # pip install requests
from typing import List, Dict, Any
import time

url_prefix = "https://api.triathlon.org/v1/"


api_file = Path(__file__).parent.parent / "api_key.txt"
assert api_file.exists(), f"{api_file = } does not exist"
with open(api_file, "r") as f:
    api_key = f.readline()

headers = {
    "accept": "application/json",
    "apikey": api_key
}

data_dir = Path(__file__).parent.parent / "data"

MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

def get_request(url_suffix, params=""):
 url = url_prefix + url_suffix
 for attempt in range(1, MAX_RETRIES + 1):
        print(f"📡 Solicitando URL: {url} (Tentativa {attempt}/{MAX_RETRIES})")
        try:
            # Tenta a requisição com o timeout
            response = requests.request("GET", url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Se for bem-sucedido, retorna o resultado e sai do loop
            d = json.loads(response.text)
            #d = d["data"]
            return d
            
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            # Se for a última tentativa, falha
            if attempt == MAX_RETRIES:
                print(f"❌ Falha final após {MAX_RETRIES} tentativas. Erro: {e}")
                return None
            
            # Caso contrário, espera um pouco e tenta novamente
            wait_time = 2 ** attempt # Espera exponencial: 2s, 4s, 8s...
            print(f"⚠️ Timeout ou Erro de Conexão. Esperando {wait_time}s antes de tentar novamente...")
            time.sleep(wait_time)
            
        return None

def get_athlete_info(athlete_id: int):
    saving_path = Path(__file__).parent / "data" / "athletes" / f"{athlete_id}.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True)
    # check if athlete_id has already been retrieved and saved
    if saving_path.exists():
        with open(saving_path) as f:
            res = json.load(f)
        if res is None:
            print(f"ERROR: no data found for {athlete_id = } in {saving_path = }")
        return res
    url_suffix = f"athletes/{athlete_id}"
    print(f"requesting {url_suffix = }")
    res = get_request(url_suffix=url_suffix)
    if res is None:
        print(f"ERROR: no data found for {athlete_id = } request = {url_prefix + url_suffix}")
    with open(saving_path, "w") as f:
        json.dump(res, f)
    return res

def find_athlete_id_by_name(full_name: str) -> Optional[int]:
    """
    Busca o ID de um atleta na API a partir do nome completo.
    """
    # 1. Formata o nome para a busca (ex: 'miguel hidalgo' -> 'miguel+hidalgo')
    search_query = full_name.lower().replace(" ", "+")
    
    # 2. Assume o endpoint de busca da API do World Triathlon
    # OBS: O endpoint real pode variar, mas este é um padrão comum.
    url_suffix = f"athletes?search={search_query}"
    
    # 3. Faz a requisição usando sua função existente
    res = get_request(url_suffix=url_suffix)
    
    
    if res and isinstance(res, list) and len(res) > 0:
        # A API pode retornar vários resultados. 
        # Idealmente, você faria uma verificação mais rigorosa (ex: se o nome 'title' bate).
        # Vamos pegar o primeiro resultado para simplicidade.
        primeiro_atleta = res[0]
        
        # O ID na resposta geralmente se chama 'athlete_id'
        athlete_id = primeiro_atleta.get("athlete_id") 
        athlete_title = primeiro_atleta.get("athlete_title")
        
        if athlete_id:
            print(f"✅ Encontrado: {athlete_title} (ID: {athlete_id})")
            return athlete_id
        
    print(f"❌ Erro: Nenhum atleta encontrado para '{full_name}'.")
    return None

def get_athletes_by_country_id(country_id: int, per_page: int = 10) -> List[Dict[str, Any]]:
    """
    Busca uma lista completa de atletas por country_id, usando o total de páginas (last_page).
    """
    # 1. Define o caminho de salvamento baseado no country_id
    saving_dir = data_dir / "athletes_by_country"
    saving_path = saving_dir / f"{country_id}.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica se o cache existe
    if saving_path.exists():
        print(f"✅ Lendo cache para Country ID '{country_id}' de: {saving_path}")
        with open(saving_path, 'r') as f:
            res = json.load(f)
        return res if res is not None else []

    # 3. Faz a primeira requisição para descobrir 'last_page' e 'total'
    # URL inicial (página 1)
    initial_url_suffix = f"athletes?country_id={country_id}&per_page={per_page}&page=1"
    print(f"📡 Solicitando página inicial (1) para descobrir o total de páginas...")
    
    first_res = get_request(url_suffix=initial_url_suffix)
    
    # Validação da primeira resposta
    if not first_res or not isinstance(first_res, dict) or first_res.get('status') != 'success':
        print(f"❌ Erro na API ou formato inesperado na requisição inicial.")
        return []

    last_page = first_res.get('last_page', 1)
    total_athletes = first_res.get('total', 0)
    
    print(f"✅ Total de páginas a coletar: {last_page}. Total de atletas: {total_athletes}")

    # 4. Inicializa a lista com os dados da primeira página
    all_athletes = first_res.get('data', [])
    
    # 5. Loop do restante das páginas (da página 2 até last_page)
    for page_num in range(2, last_page + 1):
        current_url_suffix = f"athletes?country_id={country_id}&per_page={per_page}&page={page_num}"
        print(f"📡 Solicitando página {page_num}/{last_page}...")

        res = get_request(url_suffix=current_url_suffix) 

        # Trata a resposta
        if res and isinstance(res, dict) and res.get('status') == 'success':
            page_data = res.get('data', [])
            all_athletes.extend(page_data)
        else:
            print(f"⚠️ Aviso: Falha ao obter dados da página {page_num}. Interrompendo coleta.")
            break 
            
    # 6. Salva o resultado final completo no cache
    final_count = len(all_athletes)
    print(f"\n💾 Sucesso: Coletados {final_count} atletas no total. Salvando cache em {saving_path}")
    
    with open(saving_path, "w") as f:
        json.dump(all_athletes, f)
        
    return all_athletes

def get_all_events(
    start_date: str = "2000-01-01", 
    end_date: str = "2026-01-01", 
    per_page: int = 10
) -> List[Dict[str, Any]]:
    """
    Busca uma lista completa de TODOS os eventos em um período, usando paginação e cache.
    """
    # 1. Define o caminho de salvamento baseado no período (para cache)
    saving_dir = data_dir / "all_events"
    saving_path = saving_dir / f"all_events_{start_date[:4]}_{end_date[:4]}.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica se o cache existe
    if saving_path.exists():
        print(f"✅ Lendo cache de TODOS os Eventos ({start_date} a {end_date}) de: {saving_path}")
        with open(saving_path, 'r') as f:
            res = json.load(f)
        return res if res is not None else []

    # 3. Faz a primeira requisição para descobrir 'last_page' e 'total'
    # URL inicial (página 1) - Sem category_id
    initial_url_suffix = (
        f"events?start_date={start_date}&end_date={end_date}&per_page={per_page}&page=1&order=asc"
    )
    print(f"📡 Solicitando página inicial (1) de TODOS os eventos...")
    
    first_res = get_request(url_suffix=initial_url_suffix)
    
    # Validação da primeira resposta
    if not first_res or not isinstance(first_res, dict) or first_res.get('status') != 'success':
        print("❌ Erro na API ou formato inesperado na requisição inicial de eventos.")
        return []

    last_page = first_res.get('last_page', 1)
    total_events = first_res.get('total', 0)
    
    print(f"✅ Total de páginas a coletar: {last_page}. Total de eventos: {total_events}")
    if total_events == 0:
        return []

    # 4. Inicializa a lista com os dados da primeira página
    all_events = first_res.get('data', [])
    
    # 5. Loop do restante das páginas (da página 2 até last_page)
    for page_num in range(2, last_page + 1):
        # A URL de cada página deve incluir todos os filtros
        current_url_suffix = (
             f"events?start_date={start_date}&end_date={end_date}&per_page={per_page}&page={page_num}&order=asc"
        )
        print(f"📡 Solicitando página {page_num}/{last_page}...")

        res = get_request(url_suffix=current_url_suffix) 

        # Trata a resposta
        if res and isinstance(res, dict) and res.get('status') == 'success':
            page_data = res.get('data', [])
            all_events.extend(page_data)
        else:
            print(f"⚠️ Aviso: Falha ao obter dados da página {page_num}. Interrompendo coleta total.")
            break 
            
    # 6. Salva o resultado final completo no cache
    final_count = len(all_events)
    print(f"\n💾 Sucesso: Coletados {final_count} eventos no total. Salvando cache em {saving_path}")
    
    with open(saving_path, "w") as f:
        json.dump(all_events, f)
        
    return all_events


def get_event_programs(event_id: int) -> List[Dict[str, Any]]:
    """
    Busca a lista de programas (competições/provas) para um evento específico 
    e implementa cache em arquivo.
    
    :param event_id: O ID numérico do evento.
    :return: Uma lista de dicionários com os dados dos programas.
    """
    # 1. Define o caminho de salvamento baseado no event_id
    saving_dir = data_dir / "event_programs"
    saving_path = saving_dir / f"event_{event_id}_programs.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica se o cache existe
    if saving_path.exists():
        # print(f"✅ Lendo cache de programas para Evento ID: {event_id} de: {saving_path}")
        with open(saving_path, 'r') as f:
            res = json.load(f)
        return res if res is not None else []

    url_suffix = f"events/{event_id}/programs"
    print(f"📡 Solicitando programas da API para Evento ID: {event_id}")
    
    res = get_request(url_suffix=url_suffix)
    
    # --- NOVO TRATAMENTO DE ERRO E RESPOSTA NULA ---
    
    # 1. Verifica se houve falha na requisição (get_request retorna None)
    if res is None:
        print(f"❌ Erro de Requisição (Retorno None) para Evento ID: {event_id}. Pulando.")
        with open(saving_path, "w") as f:
             json.dump(None, f) # Salva o erro/None no cache
        return []

    # 2. Extrai a lista de programas (lida com o formato de metadados e o caso "data": null)
    programs_list = []
    
    if isinstance(res, list):
        # Caso a API retorne a lista diretamente (sem envelope)
        programs_list = res
    elif isinstance(res, dict) and res.get('status') == 'success':
        # Caso a API retorne o envelope (com 'status': 'success')
        data = res.get('data')
        
        # 🛑 CORREÇÃO CHAVE: Verifica se 'data' é nulo (null) ou lista vazia
        if data is None:
            programs_list = [] # Trata como lista vazia de programas
            print(f"⚠️ Aviso: Evento ID {event_id} retornou 'data': null (Sem Programas).")
        elif isinstance(data, list):
            programs_list = data
        else:
            # Caso a API tenha um formato de dados inesperado (não lista)
            print(f"❌ Erro: Evento ID {event_id} retornou dados em formato inesperado.")
            programs_list = []

    # Se não for sucesso e não for lista (ex: status: 'error'), programs_list será []

    # 4. Salva o resultado final completo no cache
    print(f"💾 Sucesso: Encontrados {len(programs_list)} programas. Salvando cache em {saving_path}")
    with open(saving_path, "w") as f:
        # Salva apenas a lista de programas para manter o cache limpo (ou a lista vazia [])
        json.dump(programs_list, f) 
        
    return programs_list


def get_program_results(event_id: int, prog_id: int) -> Dict[str, Any]:
    """
    Busca os resultados detalhados para um programa específico (prog_id) dentro de um evento (event_id)
    e implementa cache em arquivo.
    
    :param event_id: O ID numérico do evento.
    :param prog_id: O ID numérico do programa.
    :return: Um dicionário com os resultados e metadados.
    """
    # 1. Define o caminho de salvamento baseado no event_id e prog_id
    saving_dir = data_dir / "program_results"
    saving_path = saving_dir / f"event_{event_id}_prog_{prog_id}_results.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica se o cache existe
    if saving_path.exists():
        # print(f"✅ Lendo cache de resultados para Prog ID {prog_id} do Evento {event_id}")
        with open(saving_path, 'r') as f:
            res = json.load(f)
        return res if res is not None else {}

    # 3. Faz a requisição à API
    url_suffix = f"events/{event_id}/programs/{prog_id}/results"
    print(f"📡 Solicitando resultados da API para Evento {event_id} / Programa {prog_id}")
    
    res = get_request(url_suffix=url_suffix)
    
    # 4. Trata a resposta (lida com None ou formato de metadados)
    if res is None:
        print(f"❌ Erro de Requisição (Retorno None) para {event_id}/{prog_id}. Pulando.")
        with open(saving_path, "w") as f:
             json.dump(None, f)
        return {}
        
    # Salva o resultado no cache. Mesmo que esteja vazio ou contenha erro, o cache evita novas requisições.
    with open(saving_path, "w") as f:
        json.dump(res, f)
        
    return res

def get_athlete_results(athlete_id: int, per_page: int = 10) -> List[Dict[str, Any]]:
    """
    Busca todos os resultados de um atleta específico (athlete_id), usando paginação e cache.
    """
    # 1. Define o caminho de salvamento baseado no athlete_id
    saving_dir = data_dir / "athlete_results"
    saving_path = saving_dir / f"athlete_{athlete_id}_results.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica se o cache existe
    if saving_path.exists():
        print(f"✅ Lendo cache de resultados para Athlete ID: {athlete_id} de: {saving_path}")
        with open(saving_path, 'r') as f:
            res = json.load(f)
        return res if res is not None else []

    # 3. Inicializa variáveis e URL
    all_results = []
    # URL inicial para a primeira página. O endpoint não tem um 'page' explícito inicialmente,
    # então a API deve retornar a página 1 e os metadados.
    current_url_suffix = f"athletes/{athlete_id}/results?per_page={per_page}"
    page_count = 1
    
    # 4. Loop de Paginação
    while current_url_suffix:
        print(f"📡 Solicitando resultados do Athlete {athlete_id} (Página {page_count})...")

        res = get_request(url_suffix=current_url_suffix) 

        # 5. Trata a resposta
        if not res or not isinstance(res, dict) or res.get('status') != 'success':
            print(f"❌ Erro na API ou status não é 'success' na página {page_count}.")
            break

        # Extrai a lista de resultados da chave 'data'
        page_data = res.get('data', [])
        
        if page_data:
            all_results.extend(page_data)
        
        # 6. Verifica se há uma próxima página usando 'next_page_url'
        next_page_url_full = res.get('next_page_url')
        
        if next_page_url_full:
            # Extrai apenas o sufixo (tudo após a URL base, assumindo que url_prefix existe)
            if 'url_prefix' in globals() and url_prefix in next_page_url_full:
                 current_url_suffix = next_page_url_full.split(url_prefix)[-1]
            else:
                 current_url_suffix = next_page_url_full # Assume que o get_request lida com a URL completa
                 
            page_count += 1
        else:
            current_url_suffix = None # Finaliza o loop

    # 7. Salva o resultado final completo no cache
    final_count = len(all_results)
    print(f"\n💾 Sucesso: Coletados {final_count} resultados no total. Salvando cache em {saving_path}")
    
    with open(saving_path, "w") as f:
        json.dump(all_results, f)
        
    return all_results

# Dentro do utils_itu.py (a função get_program_details)

def get_program_details(event_id: int, prog_id: int) -> Dict[str, Any]:
    # 1. Define o caminho de salvamento baseado no event_id e prog_id
    saving_dir = data_dir / "program_details"
    saving_path = saving_dir / f"event_{event_id}_prog_{prog_id}_details.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica se o cache existe
    if saving_path.exists():
        with open(saving_path, 'r') as f:
            res = json.load(f)
        # O cache já deve ter o objeto de detalhes limpo
        return res if res is not None else {}

    # 3. Faz a requisição à API
    url_suffix = f"events/{event_id}/programs/{prog_id}"
    print(f"📡 Solicitando detalhes da API para Evento {event_id} / Programa {prog_id}")
    
    res = get_request(url_suffix=url_suffix)
    
    # 4. Trata a resposta e EXTRAI OS DADOS CORRETOS
    if res is None:
        print(f"❌ Erro de Requisição (Retorno None) para {event_id}/{prog_id}. Pulando.")
        with open(saving_path, "w") as f:
             json.dump(None, f)
        return {}
        
    # Extrai o objeto de detalhes da chave 'data'. Se não houver 'data' (formato antigo/erro), usa a resposta inteira.
    program_details = res.get('data', res) 

    # Salva APENAS O OBJETO DE DETALHES no cache.
    with open(saving_path, "w") as f:
        json.dump(program_details, f)
        
    return program_details # Retorna o objeto de detalhes (que contém 'prog_distance_category')


# Dentro do utils_itu.py

# Dentro do utils_itu.py

def get_all_athletes(per_page: int = 10, force_start_page: int = 1) -> List[Dict[str, Any]]:
    """
    Busca uma lista completa de TODOS os atletas, verificando o total oficial da API
    e retomando a coleta a partir da última página salva.
    """
    saving_dir = data_dir / "all_athletes"
    saving_path = saving_dir / f"all_athletes_full_list.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 1. Carregar Dados Pré-existentes (Cache)
    all_athletes = []
    if saving_path.exists():
        with open(saving_path, 'r') as f:
            all_athletes = json.load(f)
        
        if isinstance(all_athletes, list):
            print(f"✅ Cache encontrado. Carregados {len(all_athletes)} atletas.")
        else:
            all_athletes = []

    # 2. Requisitar Metadados (total, last_page)
    initial_url_suffix = f"athletes?per_page={per_page}&page=1"
    first_res = get_request(url_suffix=initial_url_suffix)
    
    if not first_res or not isinstance(first_res, dict) or first_res.get('status') != 'success':
        print("❌ Erro ao obter metadados. Retornando dados do cache.")
        return all_athletes

    last_page = first_res.get('last_page', 1)
    total_athletes = first_res.get('total', 0)
    
    print(f"\n--- Verificação da API ---")
    print(f"Total OFICIAL de atletas na API: {total_athletes:,}")
    print(f"Total de páginas a coletar: {last_page}")
    print(f"Total de atletas no cache: {len(all_athletes):,}")
    
    
    # 3. Determinar o Ponto de Reinício
    
    # Ponto de reinício baseado no cache (página seguinte à última página totalmente salva)
    start_page_from_cache = (len(all_athletes) // per_page) + 1
    
    # O loop deve começar no maior valor entre o ponto do cache e o 'force_start_page' (513 no seu caso)
    start_page_final = max(start_page_from_cache, force_start_page)
    
    if len(all_athletes) >= total_athletes:
         print("✅ Coleta completa no cache. Nenhuma requisição adicional necessária.")
         return all_athletes
    
    print(f"⏩ Reiniciando coleta a partir da página: {start_page_final}")

    # 4. Loop de Paginação
    for page_num in range(start_page_final, last_page + 1):
        current_url_suffix = f"athletes?per_page={per_page}&page={page_num}"
        print(f"📡 Solicitando página {page_num}/{last_page}...")

        res = get_request(url_suffix=current_url_suffix) 

        # Trata a resposta
        if res and isinstance(res, dict) and res.get('status') == 'success':
            page_data = res.get('data', [])
            all_athletes.extend(page_data)
        else:
            print(f"⚠️ Aviso: Falha final ao obter dados da página {page_num}. Pulando para a próxima.")

    # 5. Salva o resultado final completo no cache
    final_count = len(all_athletes)
    print(f"\n💾 Sucesso: Coletados {final_count} atletas no total. Salvando cache em {saving_path}")
    
    with open(saving_path, "w") as f:
        json.dump(all_athletes, f)
        
    return all_athletes

def get_event_title(event_id: int) -> str:
    """
    Busca o título de um evento específico (event_id) na API/cache.
    Acessa o endpoint /v1/events/{event_id} e extrai o título de dentro do envelope 'data'.
    """
    # Define o caminho de salvamento para o título
    saving_dir = data_dir / "event_titles"
    saving_path = saving_dir / f"event_{event_id}_title.json"
    saving_path.parent.mkdir(parents=True, exist_ok=True) 

    # 1. Verifica se o cache existe
    if saving_path.exists():
        with open(saving_path, 'r') as f:
            res = json.load(f)
        return res.get('event_title', 'Título Não Encontrado (Cache)') if res else 'Título Não Encontrado'

    # 2. Faz a requisição à API
    url_suffix = f"events/{event_id}"
    print(f"📡 Solicitando título da API para Evento ID: {event_id}")
    
    res = get_request(url_suffix=url_suffix)
    
    # 3. Trata a resposta (envelope 'data')
    event_data = res.get('data', {}) if isinstance(res, dict) else {}
    event_title = event_data.get('event_title', 'Título Não Encontrado')
    
    # 4. Salva o título no cache
    with open(saving_path, "w") as f:
        json.dump({'event_title': event_title}, f)
        
    return event_title

# Dentro do utils_itu.py

PROGRAM_DETAILS_DIR = Path('data') / "program_details"

def fetch_and_cache_program_details(event_id: int, prog_id: int) -> dict:
    """
    Faz a requisição para /events/{event_id}/programs/{prog_id},
    salva o conteúdo do campo 'data' em program_details, e retorna os detalhes.
    """
    # 1. Define o caminho de salvamento com o padrão de nomenclatura
    saving_path = PROGRAM_DETAILS_DIR / f"event_{event_id}_prog_{prog_id}_details.json"
    PROGRAM_DETAILS_DIR.mkdir(parents=True, exist_ok=True) 

    # 2. Verifica o Cache
    if saving_path.exists():
        # print(f"✅ Cache exists: {saving_path.name}")
        with open(saving_path, 'r') as f:
            details = json.load(f)
        return details if details is not None else {}

    # 3. Faz a requisição à API
    url_suffix = f"events/{event_id}/programs/{prog_id}"
    print(f"📡 Solicitando Detalhes do Programa: {event_id}/{prog_id}")
    
    res = get_request(url_suffix=url_suffix)
    
    # 4. Extração do Envelope e Salvamento
    if res and isinstance(res, dict):
        # A API retorna os detalhes dentro da chave 'data' para este endpoint
        program_details = res.get('data', {}) 
        
        # Salva o conteúdo do 'data' no arquivo (sem o envelope externo)
        with open(saving_path, "w") as f:
            json.dump(program_details, f)
            
        return program_details
    else:
        print(f"❌ Falha ao obter detalhes para {event_id}/{prog_id}. Resposta: {res}")
        return {}