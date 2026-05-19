"""
Conexión a MotherDuck (DuckDB cloud).
Token tomado de:
  - Local:  variable de entorno TOKEN_MATHERDUCK (.env)
  - Cloud:  st.secrets["motherduck_token"]
"""
import duckdb
import os
import streamlit as st
from dotenv import load_dotenv


def get_motherduck_token():
    try:
        if hasattr(st, 'secrets') and "motherduck_token" in st.secrets:
            return st.secrets["motherduck_token"]
    except Exception:
        pass
    load_dotenv()
    return os.getenv("TOKEN_MATHERDUCK")


def get_connection():
    token = get_motherduck_token()
    if not token:
        raise ValueError(
            "TOKEN_MATHERDUCK no encontrado. "
            "Definilo en .env (local) o en st.secrets['motherduck_token'] (cloud)."
        )
    return duckdb.connect(f"md:?motherduck_token={token}")