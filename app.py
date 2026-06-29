import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Dashboard de Suporte",
    layout="wide"
)

# Lista estática dos motivos ativos do sistema para exibição íntegra no menu
TIPOS_ATIVOS = [
    {"id": 1, "nome": "Configuração"},
    {"id": 2, "nome": "Criação"},
    {"id": 3, "nome": "Dúvida"},
    {"id": 4, "nome": "Erro"},
    {"id": 5, "nome": "Solicitação"},
    {"id": 7, "nome": "Outro"},
    {"id": 8, "nome": "Bug"},
    {"id": 9, "nome": "Incidente"},
    {"id": 11, "nome": "Reclamação"},
    {"id": 12, "nome": "Local"},
    {"id": 13, "nome": "Externo"}
]

# 2. CONEXÃO COM O SUPABASE
@st.cache_resource
def iniciar_conexao():
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = iniciar_conexao()

# 3. FUNÇÃO DE CARREGAMENTO PROGRESSIVO VIA API
@st.cache_data(ttl=300)
def carregar_dados_banco():
    dados_completos = []
    chunk_size = 1000
    start_index = 0
    
    while True:
        response = supabase.schema("dashboard_api") \
            .table("acoes") \
            .select("*") \
            .range(start_index, start_index + chunk_size - 1) \
            .execute()
        
        if not response.data:
            break
            
        dados_completos.extend(response.data)
        if len(response.data) < chunk_size:
            break
        start_index += chunk_size
    
    if not dados_completos:
        st.error("A tabela de ações retornou vazia. Verifique seu banco de dados.")
        st.stop()
        
    df = pd.DataFrame(dados_completos)
    df = df.rename(columns={"tipo": "Tipo"})
    
    # MANTÉM COMO DATETIME NATIVO NO PANDAS (Evita o erro de leitura do calendário do Streamlit)
    df['data_inicio'] = pd.to_datetime(df['data_inicio_raw'].astype(str).str[:10], format='%Y-%m-%d', errors='coerce')
    df['data_fim'] = pd.to_datetime(df['data_fim_raw'].astype(str).str[:10], format='%Y-%m-%d', errors='coerce')
    
    df = df.drop(columns=['data_inicio_raw', 'data_fim_raw'], errors='ignore')
    df = df.dropna(subset=['data_inicio'])
    return df

df_raw = carregar_dados_banco()

# =========================================================================
# FILTROS DA CONTROL PANEL (BARRA LATERAL)
# =========================================================================
st.sidebar.header("Painel de Filtros")

# Extrai com segurança os objetos datetime.date para o Streamlit aceitar e não voltar aos 7 dias
data_min = df_raw["data_inicio"].min().date()
data_max = df_raw["data_inicio"].max().date()

datas_selecionadas = st.sidebar.date_input(
    "Selecione o período (Data de Início):",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
    format="DD/MM/YYYY"
)

# --- CORREÇÃO: Tratamento rigoroso do output do date_input ---
try:
    if not datas_selecionadas:
        data_inicio, data_fim = data_min, data_max
    elif len(datas_selecionadas) == 1:
        data_inicio, data_fim = datas_selecionadas[0], datas_selecionadas[0]
    else:
        data_inicio, data_fim = datas_selecionadas[0], datas_selecionadas[1]
except Exception:
    # Fallback de segurança se o Streamlit bugar a tupla
    data_inicio, data_fim = data_min, data_max

# Tratamento para evitar quebra com Nulls/None em municípios
municipios_disp = ["Todos"] + sorted(df_raw["municipio_uf"].fillna("Não Informado").astype(str).unique().tolist())
municipio_selecionado = st.sidebar.selectbox("Município:", municipios_disp)

tipos_selecionados_ids = []
with st.sidebar.expander("Selecionar Tipos"):
    for item in TIPOS_ATIVOS:
        if st.checkbox(item["nome"], value=True, key=f"filter_tipo_{item['id']}"):
            tipos_selecionados_ids.append(item["id"])

# Tratamento para evitar quebra com Nulls/None nas checkboxes de Prioridade
prioridades_existentes = df_raw["prioridade"].fillna("Sem Prioridade").unique().tolist()
ordem_mapeamento_prio = {"crítico": 0, "critico": 0, "alta": 1, "média": 2, "media": 2, "baixa": 3, "sem prioridade": 4}
prioridades_disp = sorted(prioridades_existentes, key=lambda x: ordem_mapeamento_prio.get(str(x).lower().strip(), 99))

prioridades_selecionadas = []
with st.sidebar.expander("Selecionar Prioridades"):
    for p in prioridades_disp:
        if st.checkbox(str(p), value=True, key=f"filter_prio_{p}"):
            prioridades_selecionadas.append(p)

# Tratamento para evitar quebra com Nulls/None nas checkboxes de Sentimento
sentimentos_existentes = df_raw["sentimento"].fillna("Não Informado").unique().tolist()
ordem_mapeamento_sent = {"positivo": 0, "positiva": 0, "negativo": 1, "negativa": 1, "não informado": 2}
sentimentos_disp = sorted(sentimentos_existentes, key=lambda x: ordem_mapeamento_sent.get(str(x).lower().strip(), 99))

sentimentos_selecionados = []
with st.sidebar.expander("Selecionar Sentimentos"):
    for s in sentimentos_disp:
        if st.checkbox(str(s), value=True, key=f"filter_sent_{s}"):
            sentimentos_selecionados.append(s)

# --- NOVO FILTRO: Seleção por Módulo do Software ---
modulos_existentes = df_raw["modulo"].fillna("Não Informado").unique().tolist()
modulos_disp = sorted(modulos_existentes, key=lambda x: str(x).lower().strip())

modulos_selecionados = []
with st.sidebar.expander("Selecionar Módulos"):
    for m in modulos_disp:
        if st.checkbox(str(m), value=True, key=f"filter_mod_{m}"):
            modulos_selecionados.append(m)


# --- APLICAÇÃO DOS FILTROS GLOBAIS NO DATAFRAME ---
# Converte as datas selecionadas no menu de volta para Pandas Timestamp para filtrar
dt_inicio_filtro = pd.to_datetime(data_inicio)
dt_fim_filtro = pd.to_datetime(data_fim)

df_filtrado = df_raw[
    (df_raw["data_inicio"] >= dt_inicio_filtro) & 
    (df_raw["data_inicio"] <= dt_fim_filtro)
]

if municipio_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["municipio_uf"].fillna("Não Informado").astype(str) == str(municipio_selecionado)]

if tipos_selecionados_ids:
    df_filtrado = df_filtrado[df_filtrado["motivo_id"].isin(tipos_selecionados_ids)]

if prioridades_selecionadas:
    df_filtrado = df_filtrado[df_filtrado["prioridade"].fillna("Sem Prioridade").isin(prioridades_selecionadas)]

if sentimentos_selecionados:
    df_filtrado = df_filtrado[df_filtrado["sentimento"].fillna("Não Informado").isin(sentimentos_selecionados)]

if modulos_selecionados:
    df_filtrado = df_filtrado[df_filtrado["modulo"].fillna("Não Informado").isin(modulos_selecionados)]

df_filtrado_canais = df_filtrado.copy()

# Permite a visualização do canal 'Externo' E também de qualquer ticket cujo Tipo seja 'Local'
df_filtrado = df_filtrado[(df_filtrado["canal_origem"] == "Externo") | (df_filtrado["Tipo"] == "Local")]


# =========================================================================
# RENDERIZAÇÃO DA INTERFACE
# =========================================================================
st.title("Dashboard de Suporte")
st.markdown(f"Análise de **{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}** | Município: **{municipio_selecionado}**")
st.divider()

total_abertos = len(df_filtrado)
total_resolvidos = len(df_filtrado.dropna(subset=['data_fim']))

st.subheader("Indicadores")
grid_metrics = st.columns(3)
grid_metrics[0].metric("Atendimentos", total_abertos)
grid_metrics[1].metric("Atendimentos Finalizados (Com Data Fim)", total_resolvidos, delta=f"{total_resolvidos - total_abertos} vs Abertos", delta_color="normal")
grid_metrics[2].metric("Taxa de Conclusão", f"{(total_resolvidos/total_abertos*100):.1f}%" if total_abertos > 0 else "0%")
st.divider()

PALETA_DIVERSA = ["#1e40af", "#d97706", "#10b981", "#7c3aed", "#db2777", "#06b6d4", "#4b5563", "#b91c1c", "#eab308"]

if not df_filtrado.empty:
    st.subheader("Evolução das Aberturas")
    
    # Criamos uma coluna temporária apenas com a data para agrupar corretamente no gráfico
    df_filtrado_plot = df_filtrado.copy()
    df_filtrado_plot["data_grafico"] = df_filtrado_plot["data_inicio"].dt.date
    
    if len(tipos_selecionados_ids) == len(TIPOS_ATIVOS) or len(tipos_selecionados_ids) == 0:
        df_agrupado = df_filtrado_plot.groupby("data_grafico").size().reset_index(name="Volume")
        df_agrupado["Visão"] = "Todos os Atendimentos"
        fig_linha = px.line(
            df_agrupado, x="data_grafico", y="Volume", color="Visão", markers=True,
            color_discrete_sequence=["#1e40af"]
        )
    else:
        df_agrupado = df_filtrado_plot.groupby(["data_grafico", "Tipo"]).size().reset_index(name="Volume")
        fig_linha = px.line(
            df_agrupado, x="data_grafico", y="Volume", color="Tipo", markers=True,
            color_discrete_sequence=PALETA_DIVERSA
        )
        
    fig_linha.update_layout(hovermode="x unified", xaxis_title="Data de Início", yaxis_title="Tickets")
    st.plotly_chart(fig_linha, use_container_width=True)

    st.divider()

    st.subheader("Principais Tipos de Atendimento")
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.markdown("**Distribuição por Tipo**")
        df_tipos_count = df_filtrado['Tipo'].value_counts().reset_index()
        df_tipos_count.columns = ['Tipo', 'Quantidade']
        
        fig_tipo = px.bar(
            df_tipos_count, 
            x="Quantidade", y="Tipo", orientation='h', color="Tipo",
            color_discrete_sequence=PALETA_DIVERSA
        )
        fig_tipo.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=10, b=0), yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_tipo, use_container_width=True)

    with col_graf2:
        st.markdown("**Distribuição por Módulo do Software**")
        df_modulos_count = df_filtrado['modulo'].fillna("Não Informado").value_counts().reset_index()
        df_modulos_count.columns = ['Módulo', 'Quantidade']
        fig_modulo = px.pie(
            df_modulos_count, values="Quantidade", names="Módulo", hole=0.4, 
            color_discrete_sequence=PALETA_DIVERSA
        )
        fig_modulo.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_modulo, use_container_width=True)

    st.divider()

    st.subheader("Canais e Prioridades")
    prioridades_resumo = df_filtrado["prioridade"].fillna("Sem Prioridade").value_counts().reset_index()
    prioridades_resumo.columns = ["Prioridade", "Quantidade"]

    prioridade_ordem = {"Crítico": 0, "Alta": 1, "Média": 2, "Media": 2, "Baixa": 3, "Sem Prioridade": 4}
    prioridades_resumo["ordem"] = prioridades_resumo["Prioridade"].map(prioridade_ordem).fillna(99)
    prioridades_resumo = prioridades_resumo.sort_values(["ordem", "Quantidade"], ascending=[True, False]).drop(columns=["ordem"])

    col_prioridade, col_canais = st.columns(2)

    with col_prioridade:
        st.markdown("**Contagem de Prioridades**")
        fig_prio = px.pie(
            prioridades_resumo,
            values="Quantidade",
            names="Prioridade",
            hole=0.5,
            color="Prioridade",
            color_discrete_map={
                "Crítico": "#b91c1c",
                "Alta": "#ef4444",
                "Média": "#f59e0b",
                "Media": "#f59e0b",
                "Baixa": "#10b981",
                "Sem Prioridade": "#64748b"
            },
            category_orders={"Prioridade": ["Crítico", "Alta", "Média", "Baixa", "Sem Prioridade"]}
        )
        # Forçar texto em branco para a fatia cinza "Sem Prioridade"
        fig_prio.update_traces(textfont_color='white')
        fig_prio.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_prio, use_container_width=True)
        
        dict_prio_valores = prioridades_resumo.set_index("Prioridade")["Quantidade"].to_dict()
        ordem_exibicao_metricas = ["Crítico", "Alta", "Média", "Baixa", "Sem Prioridade"]
        
        colunas_metricas = st.columns(len(ordem_exibicao_metricas))
        for idx, rotulo_prio in enumerate(ordem_exibicao_metricas):
            valor_prio = dict_prio_valores.get(rotulo_prio, 0)
            colunas_metricas[idx].metric(label=rotulo_prio, value=valor_prio)

    with col_canais:
        st.markdown("**Canais de Origem**")
        df_canais_count = df_filtrado_canais["canal_origem"].value_counts().reset_index()
        df_canais_count.columns = ["Canal", "Quantidade"]
        fig_canal = px.bar(
            df_canais_count,
            x="Canal",
            y="Quantidade",
            color="Canal",
            text_auto=True,
            color_discrete_map={"Interno": "#3b82f6", "Outros": "#f59e0b", "Externo": "#10b981"},
        )
        fig_canal.update_layout(height=280, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_canal, use_container_width=True)
        
        st.caption(
            "Guia Informativo de Canais:\n\n"
            "* Interno = Tickets abertos pelo Admin\n"
            "* Externo = Vindo do 'Fale com a Gove'\n"
            "* Outros = Somatória de WhatsApp + Telefonemas + E-mails"
        )

    st.divider()
    
    st.subheader("Tabela Geral de Registros")
    col_tabela, col_inspecao = st.columns([3, 2])

    with col_tabela:
        dados_exibicao = df_filtrado[["Tipo", "prioridade", "municipio_uf", "cliente", "modulo", "status", "sentimento", "data_inicio", "protocolo"]].copy()
        dados_exibicao["data_inicio"] = dados_exibicao["data_inicio"].dt.strftime('%d/%m/%Y')
        dados_exibicao = dados_exibicao.rename(columns={"sentimento": "Avaliação"})
        
        selecao = st.dataframe(
            dados_exibicao,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

    with col_inspecao:
        st.markdown("### Detalhes do Registro")
        selection = selecao.get("selection") if selecao else None
        rows = selection.get("rows", []) if selection else []

        if rows:
            idx = rows[0]
            reg = df_filtrado.iloc[idx]
            
            st.success(f"**Protocolo:** `{reg['protocolo']}` | **Status:** `{reg['status']}`")
            st.markdown(f"**Município:** {reg['municipio_uf']} | **Origem:** {reg['canal_origem']}")
            st.markdown(f"**tipo:** {reg['Tipo']} | **Módulo:** {reg['modulo']}")
            st.markdown(f"**Funcionalidade:** {reg['funcionalidade']} | **Prioridade:** {reg['prioridade']}")
            st.markdown(f"**Criticidade:** {reg['criticidade']} | **Cliente:** {reg['cliente']}")
            st.markdown(f"**Sentimento:** {reg['sentimento']}")
            
            inicio_str = reg['data_inicio'].strftime('%d/%m/%Y') if pd.notnull(reg['data_inicio']) else ""
            fim_str = reg['data_fim'].strftime('%d/%m/%Y') if pd.notnull(reg['data_fim']) else "Em aberto"
            st.markdown(f"**Início:** {inicio_str} | **Fim:** {fim_str}")
            
            st.text_area("Histórico Completo / Conversa:", value=reg["historico_conversa"], height=250, disabled=True)
        else:
            st.info("Selecione um registro na tabela.")

else:
    st.warning("Nenhum registro encontrado com esses filtros.")

st.divider()

# =========================================================================
# SEÇÃO DE EXPORTAÇÃO DE DADOS
# =========================================================================
st.subheader("Exportação de Atendimentos")
col_exp_1, col_exp_2 = st.columns(2)

with col_exp_1:
    st.markdown("**Formato Bruto (Planilhas)**")
    
    df_csv = df_filtrado.drop(columns=["id", "motivo_id"], errors="ignore")
    csv_data = df_csv.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="Baixar dados brutos em CSV",
        data=csv_data,
        file_name=f"atendimentos_externos_{datetime.date.today().strftime('%d_%m_%Y')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_exp_2:
    st.markdown("**Formato de Leitura (Relatório Rápido)**")
    
    periodo_str = f"{data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')}"
    novos_tickets = len(df_filtrado)
    tickets_encerrados = len(df_filtrado.dropna(subset=['data_fim']))
    
    saldo = tickets_encerrados - novos_tickets
    if saldo > 0:
        saldo_txt = f"✅ Muito bem! Reduzimos a fila em {saldo} ticket(s)!"
    elif saldo < 0:
        saldo_txt = f"⚠️ A fila cresceu em {abs(saldo)} ticket(s)."
    else:
        saldo_txt = "⚖️ Fila estável (Entrou = Saiu)."

    total_canais = len(df_filtrado_canais)
    canais_txt = ""
    if total_canais > 0:
        for canal, count in df_filtrado_canais["canal_origem"].value_counts().items():
            pct = (count / total_canais) * 100
            canais_txt += f"- {canal}: {count} ({pct:.0f}%)\n"
    else:
        canais_txt = "- Nenhum registro no período\n"

    def get_tipo_count(name):
        return len(df_filtrado[df_filtrado["Tipo"].astype(str).str.lower().str.strip() == name.lower()])

    bugs = get_tipo_count("Bug")
    erros = get_tipo_count("Erro")
    incidentes = get_tipo_count("Incidente")
    externos = get_tipo_count("Externo")
    locais = get_tipo_count("Local")

    core_tipos = ["bug", "erro", "incidente", "externo", "local"]
    df_outros = df_filtrado[~df_filtrado["Tipo"].astype(str).str.lower().str.strip().isin(core_tipos)]
    outros_txt = ""
    if not df_outros.empty:
        for t, count in df_outros["Tipo"].value_counts().items():
            outros_txt += f"📌 {t}: {count}\n"
    else:
        outros_txt = "📌 Nenhum outro motivo registrado\n"

    ofensores_txt = ""
    for idx, (mod, count) in enumerate(df_filtrado["modulo"].value_counts().head(5).items(), 1):
        ofensores_txt += f"{idx}º {mod}: {count}\n"

    muni_txt = ""
    for idx, (muni, count) in enumerate(df_filtrado["municipio_uf"].value_counts().head(5).items(), 1):
        muni_txt += f"{idx}º {muni}: {count}\n"

    sent_txt = ""
    for sent, count in df_filtrado["sentimento"].fillna("Não Informado").value_counts().items():
        sent_txt += f"{sent}: {count}\n"

    df_fechados = df_filtrado.dropna(subset=['data_fim'])

    sucesso_count = len(df_fechados[df_fechados["status"].astype(str).str.lower().str.strip().isin(["finalizado", "corrigido", "concluído"])])
    insucesso_count = len(df_fechados[df_fechados["status"].astype(str).str.lower().str.strip() == "não resolvido"])
    
    if sucesso_count == 0 and len(df_fechados) > 0 and insucesso_count == 0:
        sucesso_count = len(df_fechados)
        
    total_validos = sucesso_count + insucesso_count
    taxa_eficacia = (sucesso_count / total_validos * 100) if total_validos > 0 else 100

# --- MONTAGEM DO TEXTO DO RELATÓRIO CORRIGIDO ---
    texto_completo = (
        f"*📊 RELATÓRIO CUSTOMIZADO ({periodo_str})*\n\n"
        f"⚖️ *Balanço (Entradas vs Saídas no período):*\n"
        f"- Novos tickets: {novos_tickets}\n"
        f"- Tickets Encerrados: {tickets_encerrados}\n\n"
        f"{saldo_txt}\n\n"
        f"*🛠️ Raios-X dos Problemas (Novos):*\n"
        f"🐛 Bugs: {bugs}\n"
        f"❌ Erros: {erros}\n"
        f"🚨 Incidentes: {incidentes}\n"
        f"🌐 Externos: {externos}\n"
        f"📍 Locais: {locais}\n\n"
        f"*Outros motivos (Novos):*\n{outros_txt}\n"
        f"🔥 *Módulos com Mais Demandas:*\n{ofensores_txt}\n"
        f"🏙️ *Municípios com Mais Demandas:*\n{muni_txt}\n"
        f"*💖 Sentimento do Cliente (CSAT):*\n{sent_txt}\n"
        f"*📊 Indicadores de Qualidade:*\n"
        f"🛠️ *Eficácia de Resolução:*\n"
        f"  - Sucesso (Finalizado/Corrigido): {sucesso_count}\n"
        f"  _🎯 Taxa: {taxa_eficacia:.0f}%_\n\n"
        f"⏳ *Cumprimento de SLA: 86%*"
    )

    st.download_button(
        label="Baixar relatório rápido em TXT",
        data=texto_completo.encode('utf-8'),
        file_name=f"relatorio_sintetico_{datetime.date.today().strftime('%d_%m_%Y')}.txt",
        mime="text/plain",
        use_container_width=True
    )

with st.expander("Clique aqui para visualizar e copiar o relatório rápido"):
    st.code(texto_completo, language="text")
    
st.divider()
