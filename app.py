"""
Votação de modalidades — Interclasses escolar
Feito para uso em tablets: todas as escolhas são botões grandes.

Fluxo do aluno:  Sala → Modalidade → Gênero → Salvar
Resultados:      protegidos por senha (RESULTADOS_SENHA).
"""

import hmac
import os
import sqlite3
from contextlib import closing
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Votação Interclasses", page_icon="🏆", layout="centered")

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
DB_PATH = os.environ.get(
    "VOTOS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "votos.db"),
)

SALAS = {
    "6º ano": ["6A", "6B", "6C", "6D"],
    "7º ano": ["7A", "7B", "7C"],
    "8º ano": ["8A", "8B", "8C", "8D", "8E", "8F", "8G", "8H"],
    "9º ano": ["9A", "9B", "9C", "9D"],
}

FAIXA_FUND_2 = "6º e 7º anos"
FAIXA_FUND_3 = "8º e 9º anos"

MODALIDADES = {
    FAIXA_FUND_2: ["Futsal", "Basquete", "Handebol"],
    FAIXA_FUND_3: ["Futsal", "Basquete", "Handebol", "Voleibol"],
}
ICONES = {"Futsal": "⚽", "Basquete": "🏀", "Handebol": "🤾", "Voleibol": "🏐"}
GENEROS = ["Masculino", "Feminino"]


def faixa_da_sala(sala: str) -> str:
    return FAIXA_FUND_2 if sala[0] in ("6", "7") else FAIXA_FUND_3


def senha_dos_resultados() -> str:
    """Lê a senha de st.secrets, depois da variável de ambiente."""
    try:
        return str(st.secrets["RESULTADOS_SENHA"])
    except Exception:
        return os.environ.get("RESULTADOS_SENHA", "interclasses2026")


# ----------------------------------------------------------------------------
# Banco de dados (SQLite)
# ----------------------------------------------------------------------------
def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS votos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sala       TEXT NOT NULL,
            faixa      TEXT NOT NULL,
            modalidade TEXT NOT NULL,
            genero     TEXT NOT NULL,
            criado_em  TEXT NOT NULL
        )
        """
    )
    return con


def salvar_voto(sala: str, modalidade: str, genero: str) -> None:
    with closing(conectar()) as con, con:
        con.execute(
            "INSERT INTO votos (sala, faixa, modalidade, genero, criado_em) VALUES (?, ?, ?, ?, ?)",
            (sala, faixa_da_sala(sala), modalidade, genero, datetime.now().isoformat(timespec="seconds")),
        )


def carregar_votos() -> pd.DataFrame:
    with closing(conectar()) as con:
        return pd.read_sql_query(
            "SELECT sala, faixa, modalidade, genero, criado_em FROM votos", con
        )


def zerar_votos() -> None:
    with closing(conectar()) as con, con:
        con.execute("DELETE FROM votos")


# ----------------------------------------------------------------------------
# Estilo (botões grandes para tablet)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; max-width: 760px;}

    /* Botões grandes, fáceis de tocar */
    div.stButton > button {
        min-height: 4.5rem;
        font-size: 1.5rem;
        font-weight: 600;
        border-radius: 1rem;
        border: 2px solid #c9d3df;
    }
    /* Opção selecionada / ação principal */
    div.stButton > button[kind="primary"] {
        background-color: #0b5fa5;
        border-color: #0b5fa5;
        color: #fff;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #094a82;
        border-color: #094a82;
    }
    /* Botão discreto (voltar / resultados) */
    div.stButton > button[kind="tertiary"] {
        min-height: 2.6rem;
        font-size: 1rem;
        font-weight: 500;
        border: none;
    }
    h1 {text-align: center;}
    .passo {text-align: center; color: #5b6b7c; font-size: 1.1rem; margin-bottom: .5rem;}
    .resumo {
        background: #eef4fa; border-radius: 1rem; padding: 1rem 1.25rem;
        font-size: 1.3rem; text-align: center; margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Estado
# ----------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("tela", "votar")  # votar | login | resultados
ss.setdefault("passo", 1)  # 1 ano | 2 sala | 3 modalidade | 4 gênero | 5 obrigado
ss.setdefault("ano", None)
ss.setdefault("sala", None)
ss.setdefault("modalidade", None)
ss.setdefault("genero", None)
ss.setdefault("autenticado", False)


def novo_voto() -> None:
    ss.update(passo=1, ano=None, sala=None, modalidade=None, genero=None)


def escolher_ano(ano: str) -> None:
    ss.update(ano=ano, sala=None, modalidade=None, genero=None, passo=2)


def escolher_sala(sala: str) -> None:
    ss.update(sala=sala, modalidade=None, genero=None, passo=3)


def escolher_modalidade(modalidade: str) -> None:
    ss.update(modalidade=modalidade, genero=None, passo=4)


def escolher_genero(genero: str) -> None:
    ss.genero = genero


def voltar() -> None:
    ss.passo = max(1, ss.passo - 1)


def salvar() -> None:
    salvar_voto(ss.sala, ss.modalidade, ss.genero)
    ss.passo = 5


def ir_para(tela: str) -> None:
    ss.tela = tela


def sair_dos_resultados() -> None:
    ss.update(autenticado=False, tela="votar")
    novo_voto()


def linhas_de_botoes(itens, por_linha, criar_botao):
    """Distribui botões em linhas de `por_linha` colunas."""
    for i in range(0, len(itens), por_linha):
        cols = st.columns(por_linha)
        for col, item in zip(cols, itens[i : i + por_linha]):
            with col:
                criar_botao(item)


# ----------------------------------------------------------------------------
# Tela: votação
# ----------------------------------------------------------------------------
def tela_votar() -> None:
    st.title("🏆 Votação do Interclasses")

    # Passo 1 — ano
    if ss.passo == 1:
        st.markdown('<div class="passo">Passo 1 de 4 · Qual é o seu ano?</div>', unsafe_allow_html=True)
        linhas_de_botoes(
            list(SALAS),
            2,
            lambda a: st.button(
                a, key=f"ano_{a}", width="stretch",
                on_click=escolher_ano, args=(a,),
            ),
        )

    # Passo 2 — sala (do ano escolhido)
    elif ss.passo == 2:
        st.markdown(
            f'<div class="passo">Passo 2 de 4 · {ss.ano} · Qual é a sua sala?</div>',
            unsafe_allow_html=True,
        )
        linhas_de_botoes(
            SALAS[ss.ano],
            4,
            lambda s: st.button(
                s, key=f"sala_{s}", width="stretch",
                type="primary" if ss.sala == s else "secondary",
                on_click=escolher_sala, args=(s,),
            ),
        )
        st.button("← Voltar", key="voltar_2", type="tertiary", on_click=voltar)

    # Passo 3 — modalidade
    elif ss.passo == 3:
        faixa = faixa_da_sala(ss.sala)
        st.markdown(
            f'<div class="passo">Passo 3 de 4 · Sala {ss.sala} · Qual modalidade você quer?</div>',
            unsafe_allow_html=True,
        )
        for m in MODALIDADES[faixa]:
            st.button(
                f"{ICONES[m]}  {m}", key=f"mod_{m}", width="stretch",
                type="primary" if ss.modalidade == m else "secondary",
                on_click=escolher_modalidade, args=(m,),
            )
        st.button("← Voltar", key="voltar_3", type="tertiary", on_click=voltar)

    # Passo 4 — gênero + salvar
    elif ss.passo == 4:
        st.markdown(
            f'<div class="passo">Passo 4 de 4 · Sala {ss.sala} · '
            f'{ICONES[ss.modalidade]} {ss.modalidade} · Para qual gênero?</div>',
            unsafe_allow_html=True,
        )
        for g in GENEROS:
            st.button(
                g, key=f"gen_{g}", width="stretch",
                type="primary" if ss.genero == g else "secondary",
                on_click=escolher_genero, args=(g,),
            )

        if ss.genero:
            st.markdown(
                f'<div class="resumo">Sala <b>{ss.sala}</b> · '
                f'{ICONES[ss.modalidade]} <b>{ss.modalidade}</b> · <b>{ss.genero}</b></div>',
                unsafe_allow_html=True,
            )
            st.button("✅ Salvar voto", key="salvar", width="stretch", on_click=salvar)

        st.button("← Voltar", key="voltar_4", type="tertiary", on_click=voltar)

    # Passo 5 — agradecimento
    else:
        st.success("Voto salvo! Obrigado por participar. 🎉", icon="✅")
        st.button("Próximo aluno", key="novo_voto", type="primary", width="stretch", on_click=novo_voto)

    st.write("")
    st.button("🔒 Resultados", key="ir_login", type="tertiary", on_click=ir_para, args=("login",))


# ----------------------------------------------------------------------------
# Tela: login dos resultados
# ----------------------------------------------------------------------------
def tela_login() -> None:
    st.title("🔒 Resultados")
    st.write("Acesso restrito. Digite a senha para ver os resultados.")

    with st.form("form_login"):
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary", width="stretch")

    if entrar:
        if hmac.compare_digest(senha.encode(), senha_dos_resultados().encode()):
            ss.update(autenticado=True, tela="resultados")
            st.rerun()
        else:
            st.error("Senha incorreta.")

    st.button("← Voltar para a votação", key="voltar_login", type="tertiary",
              on_click=ir_para, args=("votar",))


# ----------------------------------------------------------------------------
# Tela: resultados
# ----------------------------------------------------------------------------
def bloco_resultado(df_faixa: pd.DataFrame, faixa: str, genero: str) -> None:
    st.markdown(f"**{genero}**")
    sub = df_faixa[df_faixa["genero"] == genero]
    contagem = sub["modalidade"].value_counts().reindex(MODALIDADES[faixa], fill_value=0)
    maximo = int(contagem.max())

    if maximo == 0:
        st.info("Ainda sem votos.")
    else:
        lideres = [m for m, n in contagem.items() if n == maximo]
        nomes = " e ".join(f"{ICONES[m]} {m}" for m in lideres)
        rotulo = "Mais votada" if len(lideres) == 1 else "Empate"
        st.success(f"🏆 {rotulo}: {nomes} ({maximo} voto{'s' if maximo != 1 else ''})")

    tabela = contagem.rename("Votos").to_frame()
    tabela.index = [f"{ICONES[m]} {m}" for m in tabela.index]
    st.bar_chart(tabela, horizontal=True, height=200)


def tela_resultados() -> None:
    if not ss.autenticado:
        ir_para("login")
        st.rerun()

    st.title("📊 Resultados")
    df = carregar_votos()
    st.caption(f"Total de votos registrados: {len(df)}")

    for faixa in (FAIXA_FUND_2, FAIXA_FUND_3):
        st.header(faixa)
        df_faixa = df[df["faixa"] == faixa]
        col_m, col_f = st.columns(2)
        with col_m:
            bloco_resultado(df_faixa, faixa, "Masculino")
        with col_f:
            bloco_resultado(df_faixa, faixa, "Feminino")

    with st.expander("Votos por sala"):
        todas = [s for salas in SALAS.values() for s in salas]
        por_sala = df["sala"].value_counts().reindex(todas, fill_value=0)
        st.dataframe(por_sala.rename("Votos").to_frame(), width="stretch")

    with st.expander("Exportar / administração"):
        st.download_button(
            "Baixar todos os votos (CSV)",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="votos_interclasses.csv",
            mime="text/csv",
        )
        st.divider()
        confirmar = st.checkbox("Quero apagar TODOS os votos (não dá para desfazer)")
        if st.button("Apagar todos os votos", disabled=not confirmar):
            zerar_votos()
            st.rerun()

    st.button("Sair", key="sair", type="tertiary", on_click=sair_dos_resultados)


# ----------------------------------------------------------------------------
# Roteamento
# ----------------------------------------------------------------------------
if ss.tela == "login":
    tela_login()
elif ss.tela == "resultados":
    tela_resultados()
else:
    tela_votar()
