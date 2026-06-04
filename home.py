import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
from io import BytesIO

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="ZARAPLAST",
    page_icon=":bar_chart:",
    layout="wide",
)

st.header("ZARAPLAST - Departamento: Assistência Técnica")
st.markdown("---")

# =========================================================
# FUNÇÃO MYSQL
# =========================================================

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

# =========================================================
# DADOS AUXILIARES
# =========================================================

tecnico = pd.DataFrame(
    get_mysql_data('SELECT * FROM tecnico'),
    columns=["id", "Nome"]
)

df3 = pd.DataFrame(
    get_mysql_data('SELECT * FROM NCA'),
    columns=["id", "Cliente", "Peso"]
)

df2 = pd.DataFrame(
    get_mysql_data('SELECT * FROM sd'),
    columns=["id", "Desvios", "Peso"]
)

# =========================================================
# UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "Selecione um arquivo CSV ou XLSM",
    type=["csv", "xlsm", "xlsx"]
)

# =========================================================
# PROCESSAMENTO
# =========================================================

if uploaded_file:

    try:

        # =====================================================
        # LEITURA DO ARQUIVO
        # =====================================================

        file_extension = uploaded_file.name.split(".")[-1]

        if file_extension == "csv":

            df = pd.read_csv(uploaded_file)

        else:

            df = pd.read_excel(
                uploaded_file,
                sheet_name='Dados Gerais RAC - Atualizado'
            )

        # =====================================================
        # FILTRO DE DEFEITOS
        # =====================================================

        defeitos_excluidos = [
            "Material De Teste",
            "Devolução Comercial",
            "Atraso na entrega",
            "Material Molhado",
            "Pedido Divergente",
            "Sentido De Embobinameto",
            "Laudo Divergente",
            "Especificação Divergente"
        ]

        df = df[
            ~df['Descrição Defeito']
            .fillna('')
            .str.strip()
            .str.lower()
            .isin([d.lower() for d in defeitos_excluidos])

            &

            (df['Qtde Reclamada'].fillna(0) >= 100)
        ]

        # =====================================================
        # CONVERSÃO DE DATAS
        # =====================================================

        df['Data de Abertura'] = pd.to_datetime(
            df['Data de Abertura'],
            errors='coerce',
            dayfirst=True
        )

        df['Data Corte'] = pd.to_datetime(
            df['Data Corte'],
            errors='coerce',
            dayfirst=True
        )

        # Remove datas inválidas
        df = df.dropna(subset=['Data de Abertura'])

        # Verifica dataframe vazio
        if df.empty:

            st.error(
                "Não existem datas válidas na coluna 'Data de Abertura'"
            )

            st.stop()

        # =====================================================
        # CÁLCULOS
        # =====================================================

        df['SD'] = df['Sigla Defeito'].map(
            df2.set_index('Desvios')['Peso']
        ).fillna(0)

        df['NCA'] = df['Cliente'].map(
            df3.set_index('Cliente')['Peso']
        ).fillna(0)

        df[['Qtde Devolvida', 'Qtde Reclamada']] = (
            df[['Qtde Devolvida', 'Qtde Reclamada']]
            .fillna(0)
        )

        df['SN'] = df.apply(
            lambda row:
            0 if (
                row['Qtde Devolvida']
                >= row['Qtde Reclamada']
            ) or (
                row['Qtde Devolvida'] == 0
                and row['Qtde Reclamada'] == 0
            )

            else 1 if row['Qtde Devolvida'] == 0

            else 1 - (
                row['Qtde Devolvida']
                / row['Qtde Reclamada']
            )

            if row['Qtde Reclamada'] != 0
            else 0,

            axis=1
        )

        # Zera SD e NCA quando SN = 0
        df.loc[df['SN'] == 0, ['SD', 'NCA']] = 0

        # NPS
        df['NPS'] = (
            df['SD']
            * df['NCA']
            * (df['SN'] * 0.75 + 0.25)
        )

        # MC
        df['MC'] = 1500 * df['NPS']

        # Mês
        df['Mês'] = df['Data Corte'].dt.strftime('%B')

        # =====================================================
        # SIDEBAR
        # =====================================================

        st.sidebar.image("logo.png")

        st.sidebar.header("Filtros")

        # =====================================================
        # FILTRO CLIENTE
        # =====================================================

        clientes_selecionados = st.sidebar.multiselect(
            "Cliente",
            options=["Todos"] + sorted(
                df['Cliente'].dropna().unique().tolist()
            ),
            default=["Todos"]
        )

        # =====================================================
        # FILTRO TÉCNICOS
        # =====================================================

        tecnicos_excluidos = [
            "LARISSA PASQUOTO RODRIGUES",
            "LAIRA ROBERTA SOUZA LOPES",
            "EDUARDO DO VALE DE OLIVEIRA"
        ]

        tecnicos_disponiveis = sorted(
            df['Iniciador'].dropna().unique().tolist()
        )

        tecnicos_default = [
            nome
            for nome in tecnicos_disponiveis
            if nome not in tecnicos_excluidos
        ]

        tecnicos_selecionados = st.sidebar.multiselect(
            "Nome do Técnico",
            options=tecnicos_disponiveis,
            default=tecnicos_default
        )

        # =====================================================
        # FILTRO DE DATA
        # =====================================================

        st.sidebar.subheader(
            "Filtrar por Período (Data de Abertura)"
        )

        # Datas mínimas e máximas
        data_min = (
            df['Data de Abertura']
            .min()
            .date()
        )

        data_max = (
            df['Data de Abertura']
            .max()
            .date()
        )

        # Widget de período
        periodo = st.sidebar.date_input(
            "Selecione o período:",
            value=(data_min, data_max)
        )

        # Garantir duas datas
        if len(periodo) != 2:

            st.warning(
                "Selecione uma data inicial e final."
            )

            st.stop()

        data_inicio, data_fim = periodo

        # =====================================================
        # TEXTO SIDEBAR
        # =====================================================

        st.sidebar.markdown(
            """
            <div style="position: fixed; bottom: 9px; width: 100%; text-align: left; font-size: 12px; color: gray;">
                <p>Departamento: Assistência Técnica</p>
                <p>Desenvolvedor: Alyson Anapaz</p>
                <p>Versão do Software: 3.0</p>
            </div>
            """,
            unsafe_allow_html=True
    )

        # =====================================================
        # APLICAÇÃO DOS FILTROS
        # =====================================================

        if "Todos" not in clientes_selecionados:

            df = df[
                df['Cliente']
                .isin(clientes_selecionados)
            ]

        if "Todos" not in tecnicos_selecionados:

            df = df[
                df['Iniciador']
                .isin(tecnicos_selecionados)
            ]

        # Filtro por data
        df = df[
            (
                df['Data de Abertura']
                >= pd.to_datetime(data_inicio)
            )

            &

            (
                df['Data de Abertura']
                <= pd.to_datetime(data_fim)
            )
        ]

        # =====================================================
        # MÉTRICAS
        # =====================================================

        media_sn = df["SN"].mean()
        media_nps = df["NPS"].mean()

        df_grouped_iniciado = (
            df.groupby("Iniciador")["MC"]
            .mean()
            .reset_index()
        )

        # =====================================================
        # CARDS
        # =====================================================

        st.title("Dashboard de Métricas")

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                label="Média SN",
                value=f"{media_sn:.2f}"
            )

        with col2:

            st.metric(
                label="Média NPS",
                value=f"{media_nps:.2f}"
            )

        with col3:

            st.metric(
                "N (Número de técnicos)",
                len(df_grouped_iniciado)
            )

        # =====================================================
        # GRÁFICO
        # =====================================================

        media_nps_geral = df["NPS"].mean()

        df_grouped = (
            df.groupby("Iniciador")["NPS"]
            .mean()
            .round(2)
            .reset_index()
        )

        df_grouped = df_grouped.sort_values(
            by="NPS",
            ascending=False
        )

        # =====================================================
        # FUNÇÃO BÔNUS
        # =====================================================

        def calcular_bonus(sn, media_nps):

            if media_nps < 0.49:
                return 0

            if sn < 0.49:
                return 200

            elif 0.49 <= sn <= 0.60:
                return 300

            elif 0.61 <= sn <= 0.70:
                return 400

            elif 0.71 <= sn <= 0.80:
                return 500

            elif 0.81 <= sn <= 0.90:
                return 550

            else:
                return 600

        # Aplicar bônus
        df_grouped["Bonus"] = df_grouped["NPS"].apply(
            lambda x: calcular_bonus(x, media_nps_geral)
        )

        # Texto formatado
        df_grouped["SN_text"] = df_grouped["NPS"].apply(
            lambda x: f"{x:.2f}".replace(".", ",")
        )

        df_grouped["Bonus_text"] = df_grouped["Bonus"].apply(
            lambda x: f"R$ {x:.2f}".replace(".", ",")
        )

        # =====================================================
        # GRÁFICO PLOTLY
        # =====================================================

        fig = px.bar(
            df_grouped,
            x="Iniciador",
            y="NPS",
            title="Média do NPS por Iniciador"
        )

        fig.update_traces(
            text=df_grouped["SN_text"],
            textposition="outside"
        )

        # Anotações bônus
        for i, bonus in enumerate(df_grouped["Bonus_text"]):

            fig.add_annotation(
                x=df_grouped["Iniciador"].iloc[i],
                y=df_grouped["NPS"].iloc[i] / 2,
                text=bonus,
                showarrow=False,
                font=dict(
                    size=13,
                    color="white"
                ),
                bgcolor="rgba(0,0,0,0.6)"
            )

        fig.update_layout(
            height=600
        )

        # =====================================================
        # EXIBIR
        # =====================================================

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.dataframe(df)

        # =====================================================
        # EXPORTAR EXCEL
        # =====================================================

        def to_excel(df):

            output = BytesIO()

            with pd.ExcelWriter(output) as writer:

                df.to_excel(
                    writer,
                    index=False,
                    sheet_name='Dados'
                )

            return output.getvalue()

        excel_file = to_excel(df)

        st.download_button(
            label="📥 Baixar Excel",
            data=excel_file,
            file_name="dados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        st.error(f"Erro: {e}")

# =========================================================
# SEM ARQUIVO
# =========================================================

else:

    st.info(
        "Faça upload de um arquivo para iniciar."
    )
