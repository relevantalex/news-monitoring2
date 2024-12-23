"""Entry point for the Streamlit application."""

import streamlit.web.bootstrap
from streamlit import config

if __name__ == "__main__":
    config.set_option("server.headless", True)
    args = []
    streamlit.web.bootstrap.run("streamlit_app.py", "", args, [])
