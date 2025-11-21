import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# --- DEFINIÇÕES DE CAMINHO ---
TOP3_COUNTRIES_CSV = Path("csv") / "top3_countries_sede.csv"
REPRESENTATIVIDADE_CSV = Path("csv") / "brasil_representatividade.csv"
CORRIDA_ANALYSIS_CSV_GLOBAL = Path('csv') / "vitorias_na_corrida_global.csv"

# --- Configuração e Funções (MANTIDAS) ---

st.set_page_config(
    page_title="Dashboard Triathlon Analytics",
    page_icon="🥇",
    layout="wide"
)

def str_to_seconds(time_str: str) -> float:
    try:
        td = pd.to_timedelta(time_str)
        return td.total_seconds()
    except:
        return np.nan
def format_seconds_to_m_s(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"
def seconds_to_h_m_s(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

def plot_top_countries(df):
    """Cria um gráfico de barras (histograma) dos países sediadores com bandeiras e cores customizadas."""
    
    # 1. Definições de Bandeira e Cores Específicas
    COLOR_MAP = {
        'Spain': 'red', 
        'Japan': 'lightgray', # Usamos lightgray para que a barra branca seja visível
        'Italy': 'green'
    }
    FLAG_MAP = {
        'Spain': '🇪🇸 Spain',
        'Japan': '🇯🇵 Japan',
        'Italy': '🇮🇹 Italy'
    }

    # 2. Enriquecimento de Dados (Adicionar Bandeira)
    # Adiciona a coluna com o emoji no nome para o eixo X
    df['Country_Flagged'] = df['Country'].map(FLAG_MAP)
    
    # 3. Criação do Gráfico de Barras com Cores Customizadas
    fig = px.bar(
        df,
        x='Country_Flagged', # Usa o nome com bandeira no eixo X
        y='Event_Count',
        color='Country', # Define a coluna 'Country' como chave para o mapeamento de cores
        title='Top 3 Países que Mais Sediaram Eventos',
        labels={'Country_Flagged': 'País', 'Event_Count': 'Nº de Eventos Sede'},
        
        # Aplica o mapeamento de cores personalizado
        color_discrete_map=COLOR_MAP 
    )
    
    # 4. Ajustes de Layout e Eixo
    fig.update_layout(
        # Remove a legenda de cor, pois é redundante
        showlegend=False, 
        xaxis={'categoryorder':'total descending'} # Garante a ordenação
    )
    return fig


def plot_general_pace_distribution():
    """Cria o gráfico de pizza para a distribuição média global (Baseado em Pace)."""
    
    data_list = []
    
    # 1. Converte e calcula o Pace para cada disciplina
    for disciplina, hms in MEDIAS_REFERENCIA_HMS.items():
        time_s = str_to_seconds(hms)
        
        if disciplina == 'SWIM':
            pace_label = f"{format_seconds_to_m_s(time_s / 15)} / 100m" # 1500m / 100m = 15
        elif disciplina == 'BIKE':
            speed_kmh = 40 / (time_s / 3600)
            pace_label = f"{speed_kmh:.1f} km/h"
        elif disciplina == 'RUN':
            pace_label = f"{format_seconds_to_m_s(time_s / 10)} / km" # 10000m / 1000m = 10
        else:
            pace_label = "N/A"
            
        data_list.append({
            'Disciplina': disciplina,
            'Tempo_s': time_s,
            'Pace_Label': pace_label,
            'Tempo_HMS': hms
        })
        
    df_plot = pd.DataFrame(data_list)
    
    # 2. Cria a coluna de rótulo para Plotly
    df_plot['Etiqueta_Pace'] = df_plot['Disciplina'] + ' (' + df_plot['Pace_Label'] + ')'

    # 3. Mapeamento de cores (Azul, Verde, Vermelho)
    COR_MAP = {'SWIM': '#1f77b4', 'BIKE': '#2ca02c', 'RUN':  '#d62728'}
    cores_em_ordem = [COR_MAP[disc] for disc in df_plot['Disciplina']]
    
    # 4. Cria o Plotly Chart
    fig = px.pie(
        df_plot,
        values='Tempo_s',
        names='Etiqueta_Pace',
        title='Distribuição Média de Tempo Global (Standard Distance)',
        hole=.4,
        color='Disciplina', # Chave para o mapeamento
        color_discrete_map=COR_MAP
    )
    
    # 5. Ajustes de layout e tooltips
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>Tempo Médio: %{customdata[0]}<extra></extra>",
        customdata=df_plot[['Tempo_HMS']],
        marker=dict(line=dict(color='#000000', width=1))
    )
    
    fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
    
    return fig
# --- Título e Introdução (MANTIDOS) ---

st.title("📊 Projeto de Análise de Dados Usando a API da World Triathlon")
st.markdown("""
Bem-vindo

Esta plataforma foi desenvolvida para explorar tendências de atletas e eventos globais, utilizando dados históricos da API oficial da World Triathlon.
""")
st.markdown("---")

st.header("Navegação e Análises Disponíveis")
st.info("""
**Acesse as páginas no menu lateral (sidebar) para verificar o perfil dos atletas no Top 3**

* **Perfil do Atleta:** Análise da performance individual (médias, pace e vantagens percentuais).
* **Análise Geral:** Visualização da logística de eventos e métricas gerais (frequência de vitórias decididas na corrida, tempos médios e tempos de transição).
""")
st.markdown("---")


# ====================================================================
# 🛑 SEÇÃO 1: LOGÍSTICA E SEDE DE EVENTOS
# ====================================================================

st.header("🌍 Análise de Logística e Países Sede")

col_top3_chart, col_top3_table = st.columns([2, 1])

if TOP3_COUNTRIES_CSV.exists():
     df_top3 = pd.read_csv(TOP3_COUNTRIES_CSV)
     
     with col_top3_chart:
         st.markdown("#### Distribuição de Sede de Eventos")
         fig_countries = plot_top_countries(df_top3)
         st.plotly_chart(fig_countries, use_container_width=True)
         
     with col_top3_table:
         st.markdown("#### Contagem Bruta")
         st.dataframe(df_top3, hide_index=True, use_container_width=True)
         
else:
     st.info("Execute os scripts de análise global para gerar os dados do Top 3 países.")


st.markdown("---")


# ====================================================================
# 🛑 SEÇÃO 2: MÉTRICAS CHAVE E ESTRATÉGIA
# ====================================================================

# ----------------------------------------------------------------------
# BLOCO 2.1: REPRESENTATIVIDADE DO BRASIL (LINHA PRÓPRIA)
# ----------------------------------------------------------------------

st.header("🇧🇷 Análise de Representatividade de Atletas Brasileiros")

if REPRESENTATIVIDADE_CSV.exists():
    df_representatividade = pd.read_csv(REPRESENTATIVIDADE_CSV)
    
    total_atletas_raw = df_representatividade[df_representatividade['Métrica'] == 'Total Atletas']['Valor'].iloc[0]
    quantidade_brasil_raw = df_representatividade[df_representatividade['Métrica'] == 'Atletas Brasil']['Valor'].iloc[0]
    percentual = df_representatividade[df_representatividade['Métrica'] == 'Representatividade (%)']['Valor'].iloc[0]

    total_atletas_int = int(total_atletas_raw)
    quantidade_brasil_int = int(quantidade_brasil_raw)

    col_total, col_br, col_percentual = st.columns(3)

    with col_total:
        st.metric(
            label="Total de Atletas na Amostra",
            value=f"{total_atletas_int:,}",
            help="Total de atletas coletados na lista global da API."
        )

    with col_br:
        st.metric(
            label="Atletas Brasileiros",
            value=f"{quantidade_brasil_int:,}",
            help="Número de atletas com o ID de país (127) do Brasil."
        )

    with col_percentual:
        st.metric(
            label="Representatividade Global",
            value=f"{percentual:.2f}%",
            delta_color="off",
            help="Porcentagem de atletas brasileiros em relação ao total global."
        )
else:
    st.info("Aguardando dados de Representatividade.")


st.markdown("---")

# ----------------------------------------------------------------------
# BLOCO 2.2: ESTRATÉGIA DE CORRIDA E TRANSIÇÕES
# ----------------------------------------------------------------------
MEDIAS_REFERENCIA_HMS = {
    'SWIM': "00:22:42",
    'BIKE': "01:10:27",
    'RUN': "00:40:55"
}

st.header("🏃💨 Métricas gerais de prova")
st.subheader("Média de Tempo Geral (Triathlon Standard)")
fig_pace = plot_general_pace_distribution()
st.plotly_chart(fig_pace, use_container_width=True)
st.markdown("---") # Separador

# Contexto das métricas:
st.subheader("Métricas de Transição e Frequência de Vitória")

st.markdown("---") # Separador para as métricas de transição
if CORRIDA_ANALYSIS_CSV_GLOBAL.exists():
    df_corrida = pd.read_csv(CORRIDA_ANALYSIS_CSV_GLOBAL)
    
    # Mapeia as métricas do CSV
    frequencia = df_corrida[df_corrida['Métrica'] == 'Frequência %']['Valor'].iloc[0]
    total_eventos = df_corrida[df_corrida['Métrica'] == 'Total Eventos Analisados']['Valor'].iloc[0]
    media_t1 = df_corrida[df_corrida['Métrica'] == 'Média T1']['Valor'].iloc[0]
    media_t2 = df_corrida[df_corrida['Métrica'] == 'Média T2']['Valor'].iloc[0]

    col_frequencia, col_t1, col_t2 = st.columns(3)

    with col_frequencia:
        st.metric(
            label="Vitória Decidida na Corrida (Geral)",
            value=frequencia,
            help=f"Frequência em {int(total_eventos):,} eventos analisados."
        )
        st.caption("A vitória é decidida quando o 2º colocado estava à frente ou empatado na T2.")

    with col_t1:
        st.metric(
            label="Tempo Médio T1 (Natação → Bike)",
            value=media_t1
        )
        st.caption("Tempo médio de transição do 1° e 2° colocados nos evento.")

    with col_t2:
        st.metric(
            label="Tempo Médio T2 (Bike → Corrida)",
            value=media_t2
        )
        st.caption("Tempo médio de transição do 1° e 2° colocados nos evento.")

else:
    st.info("Aguardando dados de análise de estratégia (Vitórias na Corrida).")


st.markdown("---")
st.caption("Desenvolvido para análise de dados da World Triathlon API.")