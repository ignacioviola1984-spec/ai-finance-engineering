"""
app.py - Version liviana para deploy (solo FX Agent).

Pensada para hostear en un servicio gratuito (ej: Streamlit Community Cloud)
con una URL publica. Usa solo el FX Agent porque es liviano (no arrastra
PyTorch), asi entra sin problemas en planes gratuitos.

Secrets en produccion: la API key NO va en el codigo. En el host se carga
como secret (ANTHROPIC_API_KEY) y aca la pasamos al entorno antes de
importar el agente.
"""

import os
import sys

import streamlit as st

# Secret en produccion -> variable de entorno (antes de importar el agente).
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

# Reusamos el agente FX ya construido (no duplicamos logica).
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "api-integration"))
import agent_fx  # noqa: E402

st.set_page_config(page_title="AI Finance — FX Agent", layout="centered")
st.title("AI Finance Engineering — FX Agent")
st.caption(
    "Un agente con tool use: el modelo decide cuando llamar una herramienta de "
    "tipos de cambio; el codigo la ejecuta contra una API real. El numero lo "
    "trae el codigo, no el modelo."
)

q = st.text_input("Pregunta sobre tipos de cambio", "Cuanto son 1500 dolares en euros?")
if st.button("Preguntar"):
    with st.spinner("El agente esta pensando..."):
        out = agent_fx.run(q)
    if out["tool"]:
        st.markdown(f"**Herramienta pedida:** `{out['tool']}`  ·  argumentos: `{out['args']}`")
        st.markdown(f"**Dato real de la API:** `{out['rate']}`")
    st.success(out["answer"])

st.divider()
st.caption("Parte del portfolio: github.com/ignacioviola1984-spec/ai-finance-engineering")
