import streamlit as st
import numpy as np
import pandas as pd
from io import BytesIO
# import pdfplumber
# import tabula  # pip install tabula-py
import plotly.express as px
import re


st.title("Preprocessing & Analytic Data RKA SKPD")
pdf_file = st.file_uploader("Upload file PDF", type="pdf")




