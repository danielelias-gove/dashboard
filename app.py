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

# 2. SISTEMA DE SEGURANÇA
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("Acesso Restrito")
    senha = st.text_input("Digite a senha de acesso da equipe:", type="password")
    if st.button("Entrar"):
        if senha == "gove2026": 
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta. Acesso negado.")
    st.stop()

# 3. CONEXÃO COM O SUPABASE
@st.cache_resource
def iniciar_conexao():
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = iniciar_conexao()

# 4. FUNÇÃO PARA PUXAR DADOS REAIS DO BANCO
@st.cache_data(ttl=300)
def carregar_dados_banco():
    dados_completos = []
    chunk_size = 1000
    start_index = 0
    
    while True:
        response = supabase.table("acoes").select(
            "id, chamado, protocolo, inicio, fim, observacoes, "
            "municipios(nome, uf:uf_id(sigla)), "
            "motivos(nome, status), "  
            "funcionalidades(nome, modulos(nome)), "
            "origens(nome), "
            "status(nome), "
            "prioridades(nome), "
            "sentimentos(nome)"  # Removido a busca por emojis do banco
        ).range(start_index, start_index + chunk_size - 1).execute()
        
        if not response.data:
            break
            
        dados_completos.extend(response.data)
        if len(response.data) < chunk_size:
            break
        start_index += chunk_size
    
    if not dados_completos:
        st.error("A tabela de ações retornou vazia. Verifique seu banco de dados.")
        st.stop()
        
    dados = []
    for r in dados_completos:
        muni_obj = r.get("municipios") or {}
        uf_obj = muni_obj.get("uf") if isinstance(muni_obj, dict) and muni_obj.get("uf") else {}
        
        moti_obj = r.get("motivos") or {}
        orig_obj = r.get("origens") or {}
        stat_obj = r.get("status") or {}
        prio_obj = r.get("prioridades") or {}
        sent_obj = r.get("sentimentos") or {}
        
        func_obj = r.get("funcionalidades") or {}
        mod_obj = func_obj.get("modulos") if isinstance(func_obj, dict) else {}
        
        if isinstance(moti_obj, dict) and moti_obj.get("status") == "I":
            continue

        nome_muni = muni_obj.get("nome", "Sem Município")
        sigla_uf = uf_obj.get("sigla", "??")
        localidade_completa = f"{nome_muni} - {sigla_uf}"
        nome_sentimento = sent_obj.get("nome", "Não Informado")

        canal_bruto = orig_obj.get("nome", "Interno")
        if canal_bruto in ["WhatsApp", "Telefonemas", "Emails", "E-mail", "Outros"]:
            canal_tratado = "Outros"
        elif canal_bruto == "Externo":
            canal_tratado = "Externo"
        else:
            canal_tratado = canal_bruto

        dados.append({
            "id": r.get("id"),
            "protocolo": r.get("protocolo") or "Sem Protocolo",
            "municipio_uf": localidade_completa,
            "canal_origem": canal_tratado,
            "status": stat_obj.get("nome", "Sem Status"),
            "prioridade": prio_obj.get("nome", "Sem Prioridade"),
            "Tipo": moti_obj.get("nome", "Não Informado"), 
            "modulo": mod_obj.get("nome", "Outros") if isinstance(mod_obj, dict) else "Outros",
            "funcionalidade": func_obj.get("nome", "Outros"),
            "sentimento": nome_sentimento,
            "data_inicio": r.get("inicio"), 
            "data_fim": r.get("fim"),       
            "historico_conversa": r.get("observacoes") or "Sem observações registradas."
        })
    
    df = pd.DataFrame(dados)
    
    df['data_inicio'] = pd.to_datetime(df['data_inicio'].astype(str).str[:10], format='%Y-%m-%d', errors='coerce').dt.date
    df['data_fim'] = pd.to_datetime(df['data_fim'].astype(str).str[:10], format='%Y-%m-%d', errors='coerce').dt.date
    df = df.dropna(subset=['data_inicio'])
    return df

df_raw = carregar_dados_banco()

# =========================================================================
# FILTROS DA CONTROL PANEL (BARRA LATERAL)
# =========================================================================
st.sidebar.header("Painel de Filtros")

data_min = df_raw["data_inicio"].min()
data_max = df_raw["data_inicio"].max()

datas_selecionadas = st.sidebar.date_input(
    "Selecione o período (Data de Início):",
    value=(data_min, data_max),
    format="DD/MM/YYYY"
)

if not datas_selecionadas:
    data_inicio, data_fim = data_min, data_max
elif len(datas_selecionadas) == 1:
    data_inicio, data_fim = datas_selecionadas[0], datas_selecionadas[0]
else:
    data_inicio, data_fim = datas_selecionadas

municipios_disp = ["Todos"] + sorted(df_raw["municipio_uf"].unique().tolist())
municipio_selecionado = st.sidebar.selectbox("Município:", municipios_disp)

tipos_disp = ['Bug', 'Configuração', 'Criação', 'Dúvida', 'Erro', 'Externo', 'Incidente', 'Reclamação', 'Solicitação']

if "Não Informado" in df_raw["Tipo"].unique().tolist():
    tipos_disp.append("Não Informado")

tipos_selecionados = st.sidebar.multiselect(
    "Tipos:", 
    options=tipos_disp, 
    default=tipos_disp,
    help="Exibindo apenas os motivos marcados com status Ativo na tabela de configurações do banco."
)

# --- APLICAÇÃO DOS FILTROS GLOBAIS NO DATAFRAME ---
df_filtrado = df_raw[
    (df_raw["data_inicio"] >= data_inicio) & 
    (df_raw["data_inicio"] <= data_fim)
]

if municipio_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["municipio_uf"] == municipio_selecionado]

if tipos_selecionados:
    df_filtrado = df_filtrado[df_filtrado["Tipo"].isin(tipos_selecionados)]

# =========================================================================
# RENDERIZAÇÃO DA INTERFACE
# =========================================================================
st.title("Relatório de Engajamento & Suporte")
st.markdown(f"Análise de **{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}** | Município: **{municipio_selecionado}**")
st.divider()

total_abertos = len(df_filtrado)
total_resolvidos = len(df_filtrado.dropna(subset=['data_fim']))

st.subheader("Indicadores")
col1, col2, col3 = st.columns(3)
col1.metric("Atendimentos", total_abertos)
col2.metric("Atendimentos Finalizados (Com Data Fim)", total_resolvidos, delta=f"{total_resolvidos - total_abertos} vs Abertos", delta_color="normal")
col3.metric("Taxa de Conclusão", f"{(total_resolvidos/total_abertos*100):.1f}%" if total_abertos > 0 else "0%")
st.divider()

if not df_filtrado.empty:
    st.subheader("Principais Tipos de Atendimento")
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.markdown("**Distribuição por Tipo**")
        df_tipos_count = df_filtrado['Tipo'].value_counts().reset_index()
        df_tipos_count.columns = ['Tipo', 'Quantidade']
        fig_tipo = px.bar(
            df_tipos_count.sort_values(by="Quantidade", ascending=True), 
            x="Quantidade", y="Tipo", orientation='h', color="Quantidade", color_continuous_scale="Blues"
        )
        fig_tipo.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_tipo, use_container_width=True)

    with col_graf2:
        st.markdown("**Distribuição por Módulo do Software**")
        df_modulos_count = df_filtrado['modulo'].value_counts().reset_index()
        df_modulos_count.columns = ['Módulo', 'Quantidade']
        fig_modulo = px.pie(
            df_modulos_count, values="Quantidade", names="Módulo", hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig_modulo.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_modulo, use_container_width=True)

    st.divider()

    st.subheader("Evolução das Aberturas")
    if len(tipos_selecionados) == len(tipos_disp) or len(tipos_selecionados) == 0:
        df_agrupado = df_filtrado.groupby("data_inicio").size().reset_index(name="Volume")
        df_agrupado["Visão"] = "Todos os Atendimentos"
        fig_linha = px.line(df_agrupado, x="data_inicio", y="Volume", color="Visão", markers=True)
    else:
        df_agrupado = df_filtrado.groupby(["data_inicio", "Tipo"]).size().reset_index(name="Volume")
        fig_linha = px.line(df_agrupado, x="data_inicio", y="Volume", color="Tipo", markers=True)
        
    fig_linha.update_layout(hovermode="x unified", xaxis_title="Data de Início", yaxis_title="Tickets")
    st.plotly_chart(fig_linha, use_container_width=True)

    st.divider()

    st.subheader("Canais e Prioridades", help="Guia Informativo de Canais:\n\n* Interno = Tickets abertos pelo Admin\n* Externo = Vindo do 'Fale com a Gove'\n* Outros = Somatória de WhatsApp + Telefonemas + E-mails")
    col_crit1, col_crit2 = st.columns(2)

    with col_crit1:
        st.markdown("**Distribuição de Prioridades por Atendimento**")
        df_prio_count = df_filtrado['prioridade'].value_counts().reset_index()
        df_prio_count.columns = ['Prioridade', 'Quantidade']
        fig_prio = px.pie(df_prio_count, values="Quantidade", names="Prioridade", hole=0.5)
        fig_prio.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_prio, use_container_width=True)

    with col_crit2:
        st.markdown("**Canais de Origem**")
        df_canais_count = df_filtrado['canal_origem'].value_counts().reset_index()
        df_canais_count.columns = ['Canal', 'Quantidade']
        fig_canal = px.bar(df_canais_count, x="Canal", y="Quantidade", color="Canal", text_auto=True, color_discrete_map={"Interno": "#3498db", "Outros": "#e67e22", "Externo": "#2ecc71"})
        fig_canal.update_layout(height=250, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_canal, use_container_width=True)

    st.divider()

    st.subheader("Tabela Geral de Registros")
    col_tabela, col_inspecao = st.columns([3, 2])

    with col_tabela:
        dados_exibicao = df_filtrado[["protocolo", "municipio_uf", "Tipo", "modulo", "status", "data_inicio"]]
        selecao = st.dataframe(
            dados_exibicao,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

    with col_inspecao:
        st.markdown("### Detalhes do Registro")
        if selecao and "rows" in selecao["selection"] and len(selecao["selection"]["rows"]) > 0:
            idx = selecao["selection"]["rows"][0]
            reg = df_filtrado.iloc[idx]
            
            st.success(f"**Protocolo:** `{reg['protocolo']}` | **Status:** `{reg['status']}`")
            st.markdown(f"**Município:** {reg['municipio_uf']} | **Origem:** {reg['canal_origem']}")
            st.markdown(f"**Tipo:** {reg['Tipo']} | **Módulo:** {reg['modulo']}")
            st.markdown(f"**Funcionalidade:** {reg['funcionalidade']} | **Prioridade:** {reg['prioridade']}")
            st.markdown(f"**Sentimento:** {reg['sentimento']}")
            st.markdown(f"**Início:** {reg['data_inicio']} | **Fim:** {reg['data_fim'] or 'Em aberto'}")
            
            st.text_area("Histórico Completo / Conversa:", value=reg["historico_conversa"], height=250, disabled=True)
        else:
            st.info("Selecione um registro na tabela.")

else:
    st.warning("Nenhum registro encontrado com esses filtros.")

st.divider()
if st.button("Sair/Bloquear Painel"):
    st.session_state.autenticado = False
    st.rerun()