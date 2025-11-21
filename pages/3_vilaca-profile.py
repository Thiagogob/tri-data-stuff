import streamlit as st
import pandas as pd
import sys
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from matplotlib.ticker import FuncFormatter # Necessário para o gráfico de pizza

# --- Configuração de Caminho e Imports ---
sys.path.append(os.path.abspath('scripts'))
from utils_itu import get_athlete_info 

# --- DEFINIÇÕES GLOBAIS E FUNÇÕES DE TEMPO ---
ATHLETE_ID = 86042
NOME_ATLETA = "VASCO VILAÇA"
MEDIAS_CSV_PATH = Path('data') / "athlete_results" / f"athlete_{ATHLETE_ID}_medias_standard.csv"
REGRESSION_DATA_CSV = Path('data') / "athlete_results" / "athlete_80795_performance_trend.csv"

# --- NOVAS FUNÇÕES DE PACE/FORMATO ---
REGRESSION_SUMMARY_JSON = Path('data') / "athlete_results" / f"athlete_{ATHLETE_ID}_regressao_sumario.json"

# Adicionar a função de carregamento
def load_regression_summary():
    if REGRESSION_SUMMARY_JSON.exists():
        with open(REGRESSION_SUMMARY_JSON, 'r') as f:
            return json.load(f)
    return None

def format_seconds_to_m_s(seconds: float) -> str:
    """Formata segundos em Minutos:Segundos (para Pace)."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def calculate_pace(row, disciplina: str) -> str:
    """Calcula o pace específico para cada disciplina Standard."""
    time_s = row['media_segundos']
    
    # 1. Natação (1500m -> min/100m)
    if disciplina == 'swim':
        # Pace em segundos por 100m = (Tempo Total em segundos) / 15
        pace_s = time_s / 15 
        return f"{format_seconds_to_m_s(pace_s)} / 100m"

    # 2. Ciclismo (40km -> km/h)
    elif disciplina == 'bike':
        # Velocidade em km/h = Distância (40) / Tempo (em horas)
        time_h = time_s / 3600
        speed_kmh = 40 / time_h
        return f"{speed_kmh:.1f} km/h"

    # 3. Corrida (10km -> min/km)
    elif disciplina == 'run':
        # Pace em segundos por km = (Tempo Total em segundos) / 10
        pace_s = time_s / 10
        return f"{format_seconds_to_m_s(pace_s)} / km"
        
    return ""
# Médias de referência do esporte (convertidas para segundos na inicialização)
MEDIAS_REFERENCIA_HMS = {
    'swim': "00:22:42",
    'bike': "01:10:27",
    'run': "00:40:55"
}

def plot_performance_trend():
    """Carrega dados de regressão e plota o gráfico de dispersão com linha de tendência usando Plotly."""
    if not REGRESSION_DATA_CSV.exists():
        st.warning("❌ Dados de tendência não encontrados. Execute o script de cálculo de regressão primeiro.")
        return None

    df_trend = pd.read_csv(REGRESSION_DATA_CSV)
    df_trend['event_date_dt'] = pd.to_datetime(df_trend['event_date_dt'])

    # O Plotly precisa de uma função auxiliar para formatar os segundos em MM:SS para o hover
    def format_time_for_hover(seconds):
        return [seconds_to_h_m_s(s) for s in seconds]

    # Cria a base do gráfico
    fig = go.Figure()

    # 1. Adiciona os pontos de dados brutos (Total Time)
    fig.add_trace(go.Scatter(
        x=df_trend['event_date_dt'],
        y=df_trend['total_time_s_mean'],
        mode='markers',
        name='Tempo Real (Segundos)',
        marker=dict(color='deepskyblue', size=8),
        hovertemplate="Data: %{x}<br>Tempo: %{text}<extra></extra>",
        text=format_time_for_hover(df_trend['total_time_s_mean']) # Usa o tempo formatado no hover
    ))

    # 2. Adiciona a linha de tendência (Line of Best Fit)
    fig.add_trace(go.Scatter(
        x=df_trend['event_date_dt'],
        y=df_trend['line_of_best_fit'],
        mode='lines',
        name='Linha de Tendência',
        line=dict(color='red', dash='dash')
    ))

    # 3. Ajustes de layout
    fig.update_layout(
        title='Tendência de Performance (Standard Distance)',
        xaxis_title='Data do Evento',
        yaxis_title='Tempo Total (Segundos)', # O Plotly lida melhor com segundos no eixo
        hovermode="x unified",
        margin=dict(t=50, b=0, l=0, r=0)
    )

    # 4. Formata o eixo Y para exibir tempo (opcional, mas profissional)
    # Define a função que converte segundos para h:m:s ou m:s para o TICK dos eixos
    fig.update_yaxes(
        tickformat=':3%M:%S', # Formata para MM:SS ou H:MM:SS
        hoverformat='.2f' # Mantém o hover em segundos para precisão
    )

    return fig



# Funções de tempo (MANTIDAS AQUI PARA O STREAMLIT)
def seconds_to_h_m_s(seconds: float) -> str:
    if np.isnan(seconds) or seconds < 0:
        return ""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

def str_to_seconds(time_str: str) -> float:
    # Versão simplificada para uso interno
    try:
        td = pd.to_timedelta(time_str)
        return td.total_seconds()
    except:
        return np.nan

# Pré-cálculo das referências em segundos
MEDIAS_REFERENCIA_S = {
    esporte: str_to_seconds(hms) 
    for esporte, hms in MEDIAS_REFERENCIA_HMS.items()
}


def load_athlete_image_url(athlete_id: int):
    athlete_data = get_athlete_info(athlete_id=athlete_id)
    if athlete_data and isinstance(athlete_data, dict):
        data_content = athlete_data.get('data', {})
        return data_content.get('athlete_profile_image')
    return None

def load_medias_data():
    if MEDIAS_CSV_PATH.exists():
        df = pd.read_csv(MEDIAS_CSV_PATH)
        return df
    return None

def plot_pie_chart_plotly(df_medias):
    """Cria e retorna um gráfico de pizza INTERATIVO com o ritmo (pace) nas etiquetas."""
    df_plot = df_medias.reset_index().copy()
    
    # === PASSO NOVO: CALCULAR PACE PARA EXIBIÇÃO ===
    # Cria uma nova coluna com o valor do Pace/Velocidade
    df_plot['Pace_Label'] = df_plot.apply(
        lambda row: calculate_pace(row, row['etapa']), axis=1
    )
    # ===============================================

    # 1. Cria a coluna de rótulo formatado (Etapa + Pace)
    df_plot['Etiqueta_Formatada'] = (
        df_plot['etapa'].str.upper() + 
        ' (' + df_plot['Pace_Label'] + ')'
    )
    
    # Mapeamento das cores solicitadas
    COR_MAP = {
        'swim': '#2ca02c', 
        'run':  '#1f77b4',  
        'bike': '#d62728'

    }
    cores_em_ordem = [COR_MAP[etapa] for etapa in df_plot['etapa']]

    
    # 2. Cria o gráfico de pizza com Plotly Express
    fig = px.pie(
        df_plot,
        values='media_segundos',
        names='Etiqueta_Formatada',
        title='Distribuição Média de Tempo por Disciplina (Standard)',
        hole=.4,
        color_discrete_sequence=cores_em_ordem,
    )
    
    # 3. Ajustes de layout para Streamlit
    fig.update_traces(
        textposition='inside', 
        # Exibe a porcentagem e a ETIQUETA COM PACE
        textinfo='percent+label',
        # Tooltip (Hover) para mostrar o tempo total médio em HH:MM:SS
        hovertemplate="Etapa: %{label}<br>Tempo Médio: %{customdata[0]}<br>Pace: %{customdata[1]}<extra></extra>",
        # Define os dados customizados (tempo HMS e Pace Label)
        customdata=np.stack((df_plot['media_hms'], df_plot['Pace_Label']), axis=-1)
    )
    
    fig.update_layout(
        font=dict(size=14),
        legend_title="Disciplinas",
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    return fig

def analyze_advantage(df_medias):
    """Calcula a vantagem percentual do atleta em relação à média geral."""
    
    comparacao = {}
    
    for index, row in df_medias.iterrows():
        esporte = row['etapa']
        media_hidalgo_s = row['media_segundos']
        media_referencia_s = MEDIAS_REFERENCIA_S.get(esporte)
        
        if media_hidalgo_s and media_referencia_s and media_referencia_s > 0:
            # Vantagem % = (Tempo_Referência - Tempo_Atleta) / Tempo_Referência * 100
            vantagem_s = media_referencia_s - media_hidalgo_s
            vantagem_percentual = (vantagem_s / media_referencia_s) * 100
            
            comparacao[esporte] = {
                'referencia': seconds_to_h_m_s(media_referencia_s),
                'hidalgo': seconds_to_h_m_s(media_hidalgo_s),
                'vantagem_s': vantagem_s,
                'vantagem_percentual': vantagem_percentual
            }
            
    return comparacao


def display_metrics(comparacao):
    """Exibe os resultados da comparação usando st.metric."""
    
    if not comparacao:
        st.warning("Não há dados de comparação disponíveis.")
        return
        
    cols = st.columns(3)
    melhor_esporte = None
    melhor_vantagem = -float('inf')

    # Itera sobre os esportes para exibir as métricas e encontrar o destaque
    for i, (esporte, dados) in enumerate(comparacao.items()):
        
        vantagem = dados['vantagem_percentual']
        
        if vantagem > melhor_vantagem:
            melhor_vantagem = vantagem
            melhor_esporte = esporte
            
        # 1. Formata o valor de exibição
        raw_hidalgo_time = dados['hidalgo']
        
        # 2. Se o tempo for menor que uma hora, remove o prefixo "00:" (ex: 00:15:30 -> 15:30)
        if raw_hidalgo_time.startswith("00:"):
            display_value = raw_hidalgo_time[3:] 
        else:
            display_value = raw_hidalgo_time
            
        # 3. Formata o delta para mostrar apenas duas casas decimais
        delta_label = f"{abs(vantagem):.2f}% ({'Melhor' if vantagem >= 0 else 'Pior'})"
        
        with cols[i]:
            st.metric(
                label=f"MÉDIA {esporte.upper()}",
                value=display_value, # Usa o valor cortado (ex: 15:30)
                delta=delta_label,
                delta_color='inverse' if vantagem < 0 else 'normal'
            )

    # Conclusão (mantida)
    if melhor_esporte:
        st.markdown("---")
        st.success(f"🏆 O esporte de maior destaque de {NOME_ATLETA} é a **{melhor_esporte.upper()}**, onde ele é **{abs(melhor_vantagem):.2f}%** mais rápido que a média dos atletas", icon="🥇")

def main():
    st.set_page_config(layout="wide")
    st.title(f"Perfil do Atleta: {NOME_ATLETA} 🇧🇷")

    # Layout em colunas
    col1, col2 = st.columns([1, 2])

    # --- CARREGAR DADOS ---
    df_medias = load_medias_data()

    # --- COLUNA 1: FOTO E ANÁLISE ---
    with col1:
        st.subheader("Foto do Atleta")
        with st.spinner("Carregando foto..."):
            image_url = load_athlete_image_url(ATHLETE_ID)
            if image_url:
                # Na Coluna 1, dentro do main():
                st.image(image_url, caption=NOME_ATLETA, use_container_width=True)
            else:
                st.warning("Não foi possível carregar a imagem.")

        if df_medias is not None and not df_medias.empty:
            st.subheader("Análise de Vantagem (vs. Média Geral)")
            comparacao = analyze_advantage(df_medias)
            display_metrics(comparacao)
            
            st.markdown("---")
            st.subheader("Médias de Performance")
            
            df_medias_display = df_medias[['etapa', 'media_hms']].rename(
                columns={'etapa': 'Etapa', 'media_hms': 'Tempo Médio'}
            )
            df_medias_display['Etapa'] = df_medias_display['Etapa'].str.upper()
            st.dataframe(df_medias_display, hide_index=True)
            
        else:
            st.error("❌ Dados de médias (CSV) não encontrados. Por favor, execute a análise completa primeiro.")
            
    # --- COLUNA 2: GRÁFICO DE PIZZA ---
    with col2:
        if df_medias is not None and not df_medias.empty:
            st.subheader("Distribuição Média de Tempo")
            
            fig = plot_pie_chart_plotly(df_medias)
            # st.plotly_chart é a função correta para gráficos Plotly
            st.plotly_chart(fig, use_container_width=True) 
            
        else:
            st.warning("Aguardando dados de média para gerar o gráfico.")

        with st.expander("Análise de Tendência Histórica"):
            st.subheader("Performance vs. Tempo (Standard)")
            reg_summary = load_regression_summary()
            fig_trend = plot_performance_trend()
                # 2. Exibir o texto de diminuição de tempo
            if reg_summary and 'slope_annual_s' in reg_summary:
                slope_annual_s = reg_summary['slope_annual_s']
                p_value = reg_summary['p_value']
        
        # Converte para um valor positivo para exibição ("diminuição de X segundos")
            diminuicao = abs(slope_annual_s) 
        
            if slope_annual_s < 0:
                st.success(f"O atleta está **DIMINUINDO** o tempo de prova em: **{diminuicao:.2f} segundos por ano**.", icon="⬇️")
            elif slope_annual_s > 0:
                st.error(f"O atleta está **AUMENTANDO** o tempo de prova em: **{diminuicao:.2f} segundos por ano**.", icon="⬆️")
            else:
                st.info("A performance está estável ou os dados são insuficientes.")
            
            st.caption(f" (P-value: {p_value:.4f})") # Exibir a significância
        
            if fig_trend:
                st.plotly_chart(fig_trend, use_container_width=True)

if __name__ == '__main__':
    Path('data').mkdir(exist_ok=True)
    main()