# =========================
# NOVO GRÁFICO - NPS EM NEGRITO / BÔNUS CENTRALIZADO COM SOMBRA
# =========================

# Calcular média geral do departamento
media_sn = df["SN"].mean()

# Agrupar por iniciador e calcular média individual
df_grouped_iniciado_SN = df.groupby("Iniciador")["NPS"].mean().reset_index()
df_grouped_iniciado_SN = df_grouped_iniciado_SN.sort_values(by="NPS", ascending=False)

# Função para calcular o bônus de acordo com as regras
def calcular_bonus(sn, media_sn):
    if media_sn < 0.49:
        return 0
    else:
        if sn < 0.49:
            return 200
        elif 0.49 <= sn <= 0.60:
            return 200 + 200
        elif 0.61 <= sn <= 0.70:
            return 200 + 300
        elif 0.71 <= sn <= 0.80:
            return 200 + 400
        elif 0.81 <= sn <= 0.90:
            return 200 + 500
        else:  # acima de 0.90
            return 200 + 1000

# Aplicar cálculo de bônus
df_grouped_iniciado_SN["Bonus"] = df_grouped_iniciado_SN["NPS"].apply(lambda x: calcular_bonus(x, media_sn))

# Formatar valores
df_grouped_iniciado_SN["SN_formatted"] = df_grouped_iniciado_SN["NPS"].apply(lambda x: f"<b>{x:.2f}</b>".replace(".", ","))
df_grouped_iniciado_SN["Bonus_formatted"] = df_grouped_iniciado_SN["Bonus"].apply(
    lambda x: f'R$ {x:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
)

# Criar gráfico de barras
fig = px.bar(
    df_grouped_iniciado_SN,
    x="Iniciador",
    y="NPS",
    title="Média do NPS por Iniciador e Bônus Correspondente"
)

# Adicionar rótulos de SN (em cima da barra, em negrito)
fig.update_traces(
    text=df_grouped_iniciado_SN["SN_formatted"],
    textposition="outside",
    textfont=dict(size=12, color="black")
)

# Adicionar rótulos de Bônus (no centro da barra, com sombra para contraste)
for i, bonus in enumerate(df_grouped_iniciado_SN["Bonus_formatted"]):
    fig.add_annotation(
        x=df_grouped_iniciado_SN["Iniciador"].iloc[i],
        y=df_grouped_iniciado_SN["NPS"].iloc[i] / 2,  # centro da barra
        text=bonus,
        showarrow=False,
        font=dict(size=13, color="white", family="Arial Black"),
        align="center",
        xanchor="center",
        yanchor="middle",
        bgcolor="rgba(0,0,0,0.6)",  # fundo preto semitransparente
        borderpad=4,
        bordercolor="black",
        borderwidth=1,
        opacity=0.9
    )

# Layout do gráfico
fig.update_layout(
    width=1000,
    height=600,
    margin=dict(t=50, b=100, l=50, r=50),
    yaxis=dict(title="NPS Médio"),
    xaxis=dict(title="Iniciador")
)

# Exibir no Streamlit
st.title("NPS por Iniciador com Bônus Calculado")
st.plotly_chart(fig)
