import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
from io import BytesIO
from datetime import datetime
import dash
from dash import dcc, html

# Configuração da página
st.set_page_config(
    page_title="ZARAPLAST",
    page_icon=":bar_chart:",
    layout="wide",
)

st.header("ZARAPLAST - Departamento: Assistência Técnica")
st.markdown("---")

# Função para conectar ao MySQL e buscar dados
def get_mysql_data(query):
    conexao = mysql.connector.connect(
        host='162.241.103.245',
        user='datatech_zara',
        password='L$@8,oR]S6K=',
        database='datatech_mc_zaraplast',
    )
    cursor = conexao.cursor()
    cursor.execute(query)
    resultado = cursor.fetchall()
    cursor.close()
    conexao.close()
    return resultado

# Buscar dados do banco
tecnico = pd.DataFrame(get_mysql_data('SELECT * FROM tecnico'), columns=["id", "Nome"])
df3 = pd.DataFrame(get_mysql_data('SELECT * FROM NCA'), columns=["id", "Cliente", "Peso"])
df2 = pd.DataFrame(get_mysql_data('SELECT * FROM sd'), columns=["id", "Desvios", "Peso"])

# Upload do arquivo
uploaded_file = st.file_uploader("Selecione um arquivo CSV ou XLSM", type=["csv", "xlsm", "xlsx"])

if uploaded_file:
    file_extension = uploaded_file.name.split(".")[-1]
    if file_extension == "csv":
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file, sheet_name='Dados Gerais RAC - Atualizado')

        # Lista de descrições de defeito a excluir
    defeitos_excluidos = ["Material De Teste", "Devolução Comercial", "Atraso na entrega", "Material Molhado", "Pedido Divergente", "Sentido De Embobinameto"]
    
    # Filtra removendo essas descrições da coluna teste
    df = df[~df['Descrição Defeito'].fillna('').str.strip().str.lower().isin([d.lower() for d in defeitos_excluidos]) & (df['Qtde Reclamada'].fillna(0) >= 0)]
    
    # Processamento dos dados
    df['SD'] = df['Sigla Defeito'].map(df2.set_index('Desvios')['Peso']).fillna(0)
    df['NCA'] = df['Cliente'].map(df3.set_index('Cliente')['Peso']).fillna(0)
    df[['Qtde Devolvida', 'Qtde Reclamada']] = df[['Qtde Devolvida', 'Qtde Reclamada']].fillna(0)
    df['SN'] = df.apply(lambda row: 0 if row['Qtde Devolvida'] >= row['Qtde Reclamada'] or (row['Qtde Devolvida'] == 0 and row['Qtde Reclamada'] == 0)
                        else 1 if row['Qtde Devolvida'] == 0
                        else row['Qtde Devolvida'] / row['Qtde Reclamada'] if row['Qtde Reclamada'] != 0
                        else 0, axis=1)
    # Fator 1: (df['SN'] * 0.1 + 0.9)
    # Fator 2: (df['SN'] * 0.2 + 0.8)
    # Fator 3: (df['SN'] * 0.05 + 0.95)
    # Fator 4: (df['SN'] * 0.01 + 0.99)
    # Fator 5: (df['SN'] * 0.005 + 0.995)
    df['NPS'] = df['SD'] * df['NCA'] * (df['SN'] * 0.7 + 0.3)
    df['MC'] = 2000 * df['NPS']
    df['Mês'] = pd.to_datetime(df['Data Corte']).dt.strftime('%B')
    #df['Ano'] = pd.to_datetime(df['Data Corte']).dt.year
    
    # Menu lateral para filtros
    st.sidebar.image("logo.png")
    st.sidebar.header("Filtros")
    # Adiciona o texto no final da sidebar
    st.sidebar.markdown(
            """
            <div style="position: fixed; bottom: 9px; width: 100%; text-align: left; font-size: 9px; color: gray;">
                <p>Desenvolvedor: Alyson Anapaz</p>
                <p>Departamento: Assistência Técnica</p>
                <p>Versão do Software: 2.0</p>
            </div>
            """,
            unsafe_allow_html=True
    )

    # Filtro de Cliente (Múltipla escolha)
    clientes_selecionados = st.sidebar.multiselect(
        "Cliente", 
        options=["Todos"] + sorted(df['Cliente'].dropna().unique().tolist()), 
        default=["Todos"]
    )

        # Lista de técnicos a excluir da seleção padrão (mas ainda aparecem na lista do filtro)
    tecnicos_excluidos = ["LARISSA PASQUOTO RODRIGUES", "LAIRA ROBERTA SOUZA LOPES"]
    
    # Lista de todos técnicos disponíveis (inclusive os que serão excluídos da seleção)
    tecnicos_disponiveis = sorted(df['Iniciador'].dropna().unique().tolist())
    
    # Define os técnicos que estarão selecionados por padrão (todos menos os excluídos)
    tecnicos_selecionados_default = [
        nome for nome in tecnicos_disponiveis if nome not in tecnicos_excluidos
    ]
    
    # Multiselect com os técnicos, com default já sem os excluídos
    tecnicos_selecionados = st.sidebar.multiselect(
        "Nome do Técnico",
        options=tecnicos_disponiveis,
        default=tecnicos_selecionados_default
    )
    
    # Aplica o filtro aos dados com base na seleção
    df_filtrado = df[df['Iniciador'].isin(tecnicos_selecionados)]


    # Filtro de Período (Data de Abertura)
    st.sidebar.subheader("Filtrar por Período (Data de Abertura)")

    # Converter para datetime e tratar valores NaN
    df['Data de Abertura'] = pd.to_datetime(df['Data de Abertura'], errors='coerce')
    df = df.dropna(subset=['Data de Abertura'])

    # Definir valores mínimo e máximo do dataset
    data_min = df['Data de Abertura'].min() if not df.empty else pd.to_datetime("today")
    data_max = df['Data de Abertura'].max() if not df.empty else pd.to_datetime("today")

    # Definir o período padrão como o mês atual
    hoje = pd.to_datetime("today")
    primeiro_dia_mes = hoje.replace(day=1)
    ultimo_dia_mes = data_max if hoje.month == data_max.month else primeiro_dia_mes + pd.DateOffset(months=1) - pd.Timedelta(days=1)

    # Widget de seleção de período
    data_inicio, data_fim = st.sidebar.date_input(
        "Selecione o período:",
        [primeiro_dia_mes, ultimo_dia_mes],
        min_value=data_min,
        max_value=data_max
    )

    # Aplicação dos filtros
    if "Todos" not in clientes_selecionados:
        df = df[df['Cliente'].isin(clientes_selecionados)]

    if "Todos" not in tecnicos_selecionados:
        df = df[df['Iniciador'].isin(tecnicos_selecionados)]

    # Aplicação do filtro de período
    df = df[(df['Data de Abertura'] >= pd.to_datetime(data_inicio)) & 
            (df['Data de Abertura'] <= pd.to_datetime(data_fim))]



    # Card
    # Calcular as médias
    media_sn = df["SN"].mean()
    media_nps = df["NPS"].mean()
    media_mc = df["MC"].mean()
    
    

    # Agrupar os dados pela coluna "Iniciador" e calcular a média da coluna "MC"
    df_grouped_iniciado = df.groupby("Iniciador")["MC"].mean().reset_index()

    # Calcular a soma das médias de MC por Iniciador
    soma_medias_mc = df_grouped_iniciado["MC"].sum()

    # Formatar os valores
    media_sn = f"{media_sn:.2f}"
    media_nps = f"{media_nps:.2f}"
    media_mc = f"R${media_mc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    soma_medias_mc_formatado = f"R${soma_medias_mc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    PA_20 = f"R${soma_medias_mc * 0.2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    teste = f"R${soma_medias_mc * 0.8:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Layout do Streamlit
    st.title("Dashboard de Métricas")

    # grades

    # grades
    
    # Gráfico

    df_grouped_iniciado = df.groupby("Iniciador")["MC"].mean().reset_index()

    df_grouped_iniciado = df_grouped_iniciado.sort_values(by="MC", ascending=False)

    # Formatar os valores de MC como moeda BR (R$)
    df_grouped_iniciado['MC_formatted'] = df_grouped_iniciado['MC'].apply(lambda x: f'R${x:,.2f}')

    # Inicializando o app Dash
    app = dash.Dash(__name__)
    
    # Criando o gráfico com rótulos de dados
    fig = px.bar(df_grouped_iniciado, x='Iniciador', y='MC', title='Média do MC por Iniciador')

    # Adicionando rótulos de dados no gráfico com formatação de moeda BR
    fig.update_traces(text=df_grouped_iniciado['MC_formatted'], textposition='outside')

    # Configuração do Streamlit
    # Ajustando o layout (tamanho do gráfico)
    fig.update_layout(
        width=1000,  # Largura do gráfico
        height=600,  # Altura do gráfico
        margin=dict(t=50, b=100, l=50, r=50),  # Margens para evitar corte
    )
    st.title("Média do MC por Iniciador")
    st.plotly_chart(fig)
        
    # Exibir dataframe filtrado
    st.dataframe(df)

 # ======================
# NOVO GRÁFICO (MC + Progressão) — ORDEM CORRIGIDA
# ======================

def dividir_progressao(total, n):
    a1 = 20.0  # primeiro termo fixo
    d = (2 * total / n - 2 * a1) / (n - 1)
    valores = [round(a1 + i * d, 2) for i in range(n)]
    diferenca = round(total - sum(valores), 2)
    valores[-1] += diferenca
    return valores

# Parâmetros da PA

total_pa = round(soma_medias_mc * 0.2, 2)
n_alvo = len(df_grouped_iniciado)
st.write("N = ", len(df_grouped_iniciado))
st.write("Média dos 80% = ", round(soma_medias_mc * 0.8 / n_alvo, 2))

# Média de MC por Iniciador
df_mc_iniciador = df.groupby("Iniciador")["MC"].mean().reset_index()

if df_mc_iniciador.empty:
    st.warning("Sem dados após os filtros para calcular o gráfico MC + Progressão.")
else:
    # Ajusta n ao número de iniciadores disponíveis
    n = min(n_alvo, len(df_mc_iniciador))

    # Gera a PA e ordena crescente (menor com menor)
    pa_vals = dividir_progressao(total_pa, n)
    pa_vals_sorted = sorted(pa_vals)  # crescente

    # Ordena MC crescente e pega os n menores (mantém os Iniciadores correspondentes)
    df_mc_sorted = (
        df_mc_iniciador
        .sort_values(by="MC", ascending=True)
        .head(n)
        .reset_index(drop=True)
    )

    # Soma 1–para–1: menor MC com menor PA, etc.
    df_mc_sorted = df_mc_sorted.assign(PA=pa_vals_sorted)
    df_mc_sorted["MC"] = df_mc_sorted["MC"] + df_mc_sorted["PA"]

    # Ordena para exibição (decrescente por MC combinado)
    df_mc_pa_plot = df_mc_sorted.sort_values(by="MC", ascending=False).reset_index(drop=True)

    # Formata rótulo
    df_mc_pa_plot["MC_formatted"] = df_mc_pa_plot["MC"].apply(lambda x: f'R${x:,.2f}')

    # Gráfico (mesmas métricas do primeiro)
    fig = px.bar(df_mc_pa_plot, x="Iniciador", y="MC", title="MC + Progressão por Iniciador")

    # Rótulos de dados
    fig.update_traces(text=df_mc_pa_plot["MC_formatted"], textposition="outside")

    # Força a ordem do eixo X a seguir a ordem do DataFrame já ordenado por MC
    fig.update_layout(
        xaxis={"categoryorder": "array", "categoryarray": df_mc_pa_plot["Iniciador"].tolist()},
        width=1000, height=600, margin=dict(t=50, b=100, l=50, r=50),
    )

    st.title("MC + Progressão por Iniciador")
    st.plotly_chart(fig)
    
    # Tabela com os valores combinados
    st.dataframe(df_mc_pa_plot[["Iniciador", "PA", "MC", "MC_formatted"]])

        # ======================
    # NOVO GRÁFICO (MD + PA)
    # ======================
    md = round(soma_medias_mc * 0.8 / n_alvo, 2)
    #st.write(md)
    # Cria uma cópia para não afetar o gráfico anterior
    df_md_pa = df_mc_sorted.copy()

    # Substitui MC pela soma de md + PA
    df_md_pa["MC"] = md + df_md_pa["PA"]
    
    media_md_pa = df_md_pa["MC"].mean()
    
    # Ordena decrescente para exibição
    df_md_pa_plot = df_md_pa.sort_values(by="MC", ascending=False).reset_index(drop=True)

    # Formata rótulos
    df_md_pa_plot["MC_formatted"] = df_md_pa_plot["MC"].apply(lambda x: f'R${x:,.2f}')

    # Gráfico
    fig2 = px.bar(df_md_pa_plot, x="Iniciador", y="MC", title="MC por Iniciador")

    fig2.update_traces(text=df_md_pa_plot["MC_formatted"], textposition="outside")
    fig2.update_layout(
        xaxis={"categoryorder": "array", "categoryarray": df_md_pa_plot["Iniciador"].tolist()},
        width=1000, height=600, margin=dict(t=50, b=100, l=50, r=50),
    )

    st.title("MC por Iniciador")
    st.plotly_chart(fig2)

    # Exibe a tabela com os valores do novo gráfico
    st.dataframe(df_md_pa_plot[["Iniciador", "PA", "MC", "MC_formatted"]])

    # st.write("Média = ", round(media_md_pa, 2))

    # Criando os cards em uma grid (4 colunas agora)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="Média SN", value=media_sn)

    with col2:
        st.metric(label="Média NPS", value=media_nps)

    with col3:
        #st.metric(label="Média MC Por técnico", value=media_mc)
        st.metric(label="Média MC Por técnico", value=media_md_pa)

    with col4:
        st.metric(label="Total Por Mês de MC", value=soma_medias_mc_formatado)
        st.metric(label="80%", value=teste)
        st.metric(label="20%", value=PA_20)











































