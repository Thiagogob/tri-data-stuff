import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# --- DEFINIÇÕES DE CAMINHO ---
TOP3_COUNTRIES_CSV = Path("data") / "analysis" / "top3_countries_sede.csv"
REPRESENTATIVIDADE_CSV = Path("data") / "analysis" / "brasil_representatividade.csv"
CORRIDA_ANALYSIS_CSV_GLOBAL = Path('data') / "analysis" / "vitorias_na_corrida_global.csv"

# --- Configuração e Funções (MANTIDAS) ---

st.set_page_config(
    page_title="Dashboard Triathlon Analytics",
    page_icon="🥇",
    layout="wide"
)

def plot_top_countries(df):
    """Cria um gráfico de barras (histograma) dos países sediadores."""
    fig = px.bar(
        df,
        x='Country',
        y='Event_Count',
        color='Event_Count',
        title='Top 3 Países que Mais Sediaram Eventos',
        labels={'Country': 'País', 'Event_Count': 'Nº de Eventos Sede'},
        color_continuous_scale=px.colors.sequential.Plasma
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    return fig


# --- Título e Introdução (MANTIDOS) ---

st.title("🥇 Dashboard de Análise de Performance no Triathlon")
st.markdown("Bem-vindo ao Dashboard de Análise de Performance!")
st.markdown("---")
st.header("Navegação e Análises Disponíveis")
st.info("Acesse as páginas no menu lateral (sidebar) para iniciar a análise.")
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

st.header("🏃💨 Estratégia de Corrida e Tempos de Transição")

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
            label="Vitória Decidida na Corrida (Global)",
            value=frequencia,
            help=f"Frequência em {int(total_eventos):,} eventos analisados."
        )
        st.caption("A vitória é decidida quando o 2º colocado estava à frente ou empatado na T2.")

    with col_t1:
        st.metric(
            label="Tempo Médio T1 (Natação → Bike)",
            value=media_t1
        )
        st.caption("Tempo médio de transição dos vencedores de evento.")

    with col_t2:
        st.metric(
            label="Tempo Médio T2 (Bike → Corrida)",
            value=media_t2
        )
        st.caption("Tempo médio de transição dos vencedores de evento.")

else:
    st.info("Aguardando dados de análise de estratégia (Vitórias na Corrida).")


st.markdown("---")
st.caption("Desenvolvido para análise de dados da World Triathlon API.")