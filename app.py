"""
Votação de modalidades — Interclasses escolar
Feito para uso em tablets: todas as escolhas são botões grandes.

Fluxo do aluno: Ano → Sala → Modalidade → Gênero → Salvar
Resultados: protegidos por senha.
"""

import hmac
import os
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


st.set_page_config(
    page_title="Votação Interclasses",
    page_icon="🏆",
    layout="centered",
)


# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------

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

ICONES = {
    "Futsal": "⚽",
    "Basquete": "🏀",
    "Handebol": "🤾",
    "Voleibol": "🏐",
}

GENEROS = ["Masculino", "Feminino"]

COLUNAS_VOTOS = [
    "sala",
    "faixa",
    "modalidade",
    "genero",
    "criado_em",
]


def faixa_da_sala(sala: str) -> str:
    return FAIXA_FUND_2 if sala[0] in ("6", "7") else FAIXA_FUND_3


def senha_dos_resultados() -> str:
    """Lê a senha da Área do Professor."""
    try:
        return str(st.secrets["admin"]["password"])
    except Exception:
        try:
            return str(st.secrets["RESULTADOS_SENHA"])
        except Exception:
            return os.environ.get(
                "RESULTADOS_SENHA",
                "interclasses2026",
            )


# ----------------------------------------------------------------------------
# Google Planilhas
# ----------------------------------------------------------------------------

@st.cache_resource
def cliente_google():
    """Cria a conexão com o Google Sheets."""

    info = dict(st.secrets["gcp_service_account"])

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credenciais = Credentials.from_service_account_info(
        info,
        scopes=scopes,
    )

    return gspread.authorize(credenciais)


@st.cache_resource
def planilha_google():
    """Abre a planilha configurada no Streamlit Secrets."""

    spreadsheet_id = str(
        st.secrets["google_sheets"]["spreadsheet_id"]
    )

    return cliente_google().open_by_key(spreadsheet_id)


def planilha_votos():
    """Abre a aba onde os votos serão armazenados."""

    nome_aba = str(
        st.secrets["google_sheets"].get(
            "worksheet",
            "Página1",
        )
    )

    return planilha_google().worksheet(nome_aba)


def preparar_planilha():
    """
    Cria o cabeçalho automaticamente
    caso a planilha esteja vazia.
    """

    ws = planilha_votos()

    primeira_linha = ws.row_values(1)

    if not primeira_linha:
        ws.append_row(
            COLUNAS_VOTOS,
            value_input_option="RAW",
        )

    elif primeira_linha[:5] != COLUNAS_VOTOS:
        raise RuntimeError(
            "O cabeçalho da planilha não corresponde "
            "ao formato esperado."
        )


def salvar_voto(
    sala: str,
    modalidade: str,
    genero: str,
) -> None:

    preparar_planilha()

    criado_em = datetime.now().isoformat(
        timespec="seconds"
    )

    planilha_votos().append_row(
        [
            sala,
            faixa_da_sala(sala),
            modalidade,
            genero,
            criado_em,
        ],
        value_input_option="RAW",
    )


def carregar_votos() -> pd.DataFrame:

    preparar_planilha()

    registros = planilha_votos().get_all_records(
        expected_headers=COLUNAS_VOTOS
    )

    if not registros:
        return pd.DataFrame(
            columns=COLUNAS_VOTOS
        )

    df = pd.DataFrame(registros)

    for coluna in COLUNAS_VOTOS:
        if coluna not in df.columns:
            df[coluna] = ""

    return df[COLUNAS_VOTOS]


def zerar_votos() -> None:

    ws = planilha_votos()

    ws.clear()

    ws.append_row(
        COLUNAS_VOTOS,
        value_input_option="RAW",
    )


# ----------------------------------------------------------------------------
# Estilo
# ----------------------------------------------------------------------------

st.markdown(
    """
    <style>

    #MainMenu, footer, header {
        visibility: hidden;
    }

    .block-container {
        padding-top: 1.5rem;
        max-width: 760px;
    }

    div.stButton > button {
        min-height: 4.5rem;
        font-size: 1.5rem;
        font-weight: 600;
        border-radius: 1rem;
        border: 2px solid #c9d3df;
    }

    div.stButton > button[kind="primary"] {
        background-color: #0b5fa5;
        border-color: #0b5fa5;
        color: #fff;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #094a82;
        border-color: #094a82;
    }

    div.stButton > button[kind="tertiary"] {
        min-height: 2.6rem;
        font-size: 1rem;
        font-weight: 500;
        border: none;
    }

    h1 {
        text-align: center;
    }

    .passo {
        text-align: center;
        color: #5b6b7c;
        font-size: 1.1rem;
        margin-bottom: .5rem;
    }

    .resumo {
        background: #eef4fa;
        border-radius: 1rem;
        padding: 1rem 1.25rem;
        font-size: 1.3rem;
        text-align: center;
        margin: 1rem 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Estado
# ----------------------------------------------------------------------------

ss = st.session_state

ss.setdefault("tela", "votar")
ss.setdefault("passo", 1)
ss.setdefault("ano", None)
ss.setdefault("sala", None)
ss.setdefault("modalidade", None)
ss.setdefault("genero", None)
ss.setdefault("autenticado", False)


def novo_voto() -> None:

    ss.update(
        passo=1,
        ano=None,
        sala=None,
        modalidade=None,
        genero=None,
    )

    ss.pop("erro_salvar", None)


def escolher_ano(ano: str) -> None:

    ss.update(
        ano=ano,
        sala=None,
        modalidade=None,
        genero=None,
        passo=2,
    )


def escolher_sala(sala: str) -> None:

    ss.update(
        sala=sala,
        modalidade=None,
        genero=None,
        passo=3,
    )


def escolher_modalidade(
    modalidade: str,
) -> None:

    ss.update(
        modalidade=modalidade,
        genero=None,
        passo=4,
    )


def escolher_genero(genero: str) -> None:
    ss.genero = genero


def voltar() -> None:
    ss.passo = max(1, ss.passo - 1)


def salvar() -> None:

    try:

        salvar_voto(
            ss.sala,
            ss.modalidade,
            ss.genero,
        )

        ss.pop("erro_salvar", None)

        ss.passo = 5

    except Exception as exc:

        ss.erro_salvar = (
            "Não foi possível registrar o voto "
            "no Google Planilhas. "
            "Tente novamente ou avise o professor."
        )

        print(
            f"Erro ao salvar voto: {exc!r}"
        )


def ir_para(tela: str) -> None:
    ss.tela = tela


def sair_dos_resultados() -> None:

    ss.update(
        autenticado=False,
        tela="votar",
    )

    novo_voto()


def linhas_de_botoes(
    itens,
    por_linha,
    criar_botao,
):

    for i in range(
        0,
        len(itens),
        por_linha,
    ):

        cols = st.columns(por_linha)

        for col, item in zip(
            cols,
            itens[i:i + por_linha],
        ):

            with col:
                criar_botao(item)


# ----------------------------------------------------------------------------
# Tela: votação
# ----------------------------------------------------------------------------

def tela_votar() -> None:

    st.title("🏆 Votação do Interclasses")

    # Passo 1 — ano
    if ss.passo == 1:

        st.markdown(
            '<div class="passo">'
            'Passo 1 de 4 · Qual é o seu ano?'
            '</div>',
            unsafe_allow_html=True,
        )

        linhas_de_botoes(
            list(SALAS),
            2,
            lambda a: st.button(
                a,
                key=f"ano_{a}",
                width="stretch",
                on_click=escolher_ano,
                args=(a,),
            ),
        )

    # Passo 2 — sala
    elif ss.passo == 2:

        st.markdown(
            f'<div class="passo">'
            f'Passo 2 de 4 · {ss.ano} · '
            f'Qual é a sua sala?'
            f'</div>',
            unsafe_allow_html=True,
        )

        linhas_de_botoes(
            SALAS[ss.ano],
            4,
            lambda s: st.button(
                s,
                key=f"sala_{s}",
                width="stretch",
                type=(
                    "primary"
                    if ss.sala == s
                    else "secondary"
                ),
                on_click=escolher_sala,
                args=(s,),
            ),
        )

        st.button(
            "← Voltar",
            key="voltar_2",
            type="tertiary",
            on_click=voltar,
        )

    # Passo 3 — modalidade
    elif ss.passo == 3:

        faixa = faixa_da_sala(
            ss.sala
        )

        st.markdown(
            f'<div class="passo">'
            f'Passo 3 de 4 · '
            f'Sala {ss.sala} · '
            f'Qual modalidade você quer?'
            f'</div>',
            unsafe_allow_html=True,
        )

        for m in MODALIDADES[faixa]:

            st.button(
                f"{ICONES[m]}  {m}",
                key=f"mod_{m}",
                width="stretch",
                type=(
                    "primary"
                    if ss.modalidade == m
                    else "secondary"
                ),
                on_click=escolher_modalidade,
                args=(m,),
            )

        st.button(
            "← Voltar",
            key="voltar_3",
            type="tertiary",
            on_click=voltar,
        )

    # Passo 4 — gênero
    elif ss.passo == 4:

        st.markdown(
            f'<div class="passo">'
            f'Passo 4 de 4 · '
            f'Sala {ss.sala} · '
            f'{ICONES[ss.modalidade]} '
            f'{ss.modalidade} · '
            f'Para qual gênero?'
            f'</div>',
            unsafe_allow_html=True,
        )

        for g in GENEROS:

            st.button(
                g,
                key=f"gen_{g}",
                width="stretch",
                type=(
                    "primary"
                    if ss.genero == g
                    else "secondary"
                ),
                on_click=escolher_genero,
                args=(g,),
            )

        if ss.get("erro_salvar"):
            st.error(
                ss.erro_salvar
            )

        if ss.genero:

            st.markdown(
                f'<div class="resumo">'
                f'Sala <b>{ss.sala}</b> · '
                f'{ICONES[ss.modalidade]} '
                f'<b>{ss.modalidade}</b> · '
                f'<b>{ss.genero}</b>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.button(
                "✅ Salvar voto",
                key="salvar",
                width="stretch",
                on_click=salvar,
            )

        st.button(
            "← Voltar",
            key="voltar_4",
            type="tertiary",
            on_click=voltar,
        )

    # Passo 5 — agradecimento
    else:

        st.success(
            "Voto salvo! "
            "Obrigado por participar. 🎉",
            icon="✅",
        )

        st.button(
            "Próximo aluno",
            key="novo_voto",
            type="primary",
            width="stretch",
            on_click=novo_voto,
        )

    st.write("")

    st.button(
        "🔒 Resultados",
        key="ir_login",
        type="tertiary",
        on_click=ir_para,
        args=("login",),
    )


# ----------------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------------

def tela_login() -> None:

    st.title("🔒 Resultados")

    st.write(
        "Acesso restrito. "
        "Digite a senha para ver os resultados."
    )

    with st.form("form_login"):

        senha = st.text_input(
            "Senha",
            type="password",
        )

        entrar = st.form_submit_button(
            "Entrar",
            type="primary",
            width="stretch",
        )

    if entrar:

        if hmac.compare_digest(
            senha.encode(),
            senha_dos_resultados().encode(),
        ):

            ss.update(
                autenticado=True,
                tela="resultados",
            )

            st.rerun()

        else:
            st.error("Senha incorreta.")

    st.button(
        "← Voltar para a votação",
        key="voltar_login",
        type="tertiary",
        on_click=ir_para,
        args=("votar",),
    )


# ----------------------------------------------------------------------------
# Resultados
# ----------------------------------------------------------------------------

def bloco_resultado(
    df_faixa: pd.DataFrame,
    faixa: str,
    genero: str,
) -> None:

    st.markdown(
        f"**{genero}**"
    )

    sub = df_faixa[
        df_faixa["genero"] == genero
    ]

    contagem = (
        sub["modalidade"]
        .value_counts()
        .reindex(
            MODALIDADES[faixa],
            fill_value=0,
        )
    )

    maximo = int(
        contagem.max()
    )

    if maximo == 0:

        st.info(
            "Ainda sem votos."
        )

    else:

        lideres = [
            m
            for m, n
            in contagem.items()
            if n == maximo
        ]

        nomes = " e ".join(
            f"{ICONES[m]} {m}"
            for m in lideres
        )

        rotulo = (
            "Mais votada"
            if len(lideres) == 1
            else "Empate"
        )

        st.success(
            f"🏆 {rotulo}: "
            f"{nomes} "
            f"({maximo} "
            f"voto{'s' if maximo != 1 else ''})"
        )

    tabela = (
        contagem
        .rename("Votos")
        .to_frame()
    )

    tabela.index = [
        f"{ICONES[m]} {m}"
        for m in tabela.index
    ]

    st.bar_chart(
        tabela,
        horizontal=True,
        height=200,
    )


def tela_resultados() -> None:

    if not ss.autenticado:

        ir_para("login")

        st.rerun()

    st.title("📊 Resultados")

    try:

        df = carregar_votos()

    except Exception as exc:

        st.error(
            "Não foi possível carregar "
            "os votos do Google Planilhas."
        )

        st.caption(
            "Verifique os Secrets, "
            "o nome da aba e o compartilhamento "
            "da planilha."
        )

        print(
            f"Erro ao carregar votos: {exc!r}"
        )

        st.button(
            "Sair",
            key="sair_erro",
            type="tertiary",
            on_click=sair_dos_resultados,
        )

        return

    st.caption(
        f"Total de votos registrados: "
        f"{len(df)}"
    )

    for faixa in (
        FAIXA_FUND_2,
        FAIXA_FUND_3,
    ):

        st.header(faixa)

        df_faixa = df[
            df["faixa"] == faixa
        ]

        col_m, col_f = st.columns(2)

        with col_m:

            bloco_resultado(
                df_faixa,
                faixa,
                "Masculino",
            )

        with col_f:

            bloco_resultado(
                df_faixa,
                faixa,
                "Feminino",
            )

    with st.expander(
        "Votos por sala"
    ):

        todas = [
            s
            for salas in SALAS.values()
            for s in salas
        ]

        por_sala = (
            df["sala"]
            .value_counts()
            .reindex(
                todas,
                fill_value=0,
            )
        )

        st.dataframe(
            por_sala
            .rename("Votos")
            .to_frame(),
            width="stretch",
        )

    with st.expander(
        "Exportar / administração"
    ):

        st.download_button(
            "Baixar todos os votos (CSV)",
            df.to_csv(
                index=False
            ).encode(
                "utf-8-sig"
            ),
            file_name=(
                "votos_interclasses.csv"
            ),
            mime="text/csv",
        )

        st.divider()

        confirmar = st.checkbox(
            "Quero apagar TODOS os votos "
            "(não dá para desfazer)"
        )

        if st.button(
            "Apagar todos os votos",
            disabled=not confirmar,
        ):

            try:

                zerar_votos()

                st.success(
                    "Todos os votos "
                    "foram apagados."
                )

                st.rerun()

            except Exception as exc:

                st.error(
                    "Não foi possível apagar "
                    "os votos da planilha."
                )

                print(
                    f"Erro ao zerar votos: "
                    f"{exc!r}"
                )

    st.button(
        "Sair",
        key="sair",
        type="tertiary",
        on_click=sair_dos_resultados,
    )


# ----------------------------------------------------------------------------
# Roteamento
# ----------------------------------------------------------------------------

if ss.tela == "login":

    tela_login()

elif ss.tela == "resultados":

    tela_resultados()

else:

    tela_votar()
