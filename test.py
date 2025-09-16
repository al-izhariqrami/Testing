import streamlit as st
import numpy as np
import pandas as pd
from io import BytesIO
import pdfplumber
import re
import plotly.express as px

st.title("Preprocessing & Analytic Data RKA SKPD")

# Upload multiple PDF files
pdf_files = st.file_uploader("Upload file PDF", type="pdf", accept_multiple_files=True)

# Tampilan Logo Streamlit
# set page config (ganti logo, judul, dll)
st.set_page_config(
    page_title="BKD Konkep Preprocessing & Analytic",
    page_icon="images.jpg",  # path lokal logo
    layout="wide"
)

# Proses Cleaning Data
def cleaning_pdf(pdf_file):
    """Fungsi untuk cleaning 1 PDF -> DataFrame"""
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    data.append(row) 
    df = pd.DataFrame(data)

    # fungsi proper_case
    def proper_case(text):
        exceptions = {"dan", "atau", "di", "ke", "dari", "yang", "untuk", "pada", "dengan"}
        if pd.isna(text):
            return text
        words = text.lower().split()
        result = []
        for i, word in enumerate(words):
            if word in exceptions and i != 0:
                result.append(word)
            else:
                result.append(word.capitalize())
        return " ".join(result)

    # Buat Kolom OPD
    opd_elemen = df.iloc[2,2]
    opd_elemen = opd_elemen.title()
    df['OPD'] = opd_elemen

    # Buat Kolom Tahun
    tahun_elemen = df.iloc[1,0]
    tahun_elemen = int(re.search(r'\d{4}', tahun_elemen).group()) 
    df['Tahun'] = tahun_elemen

    # Hapus baris tidak perlu
    df = df[~df[[0,1,2,3,4]].isnull().all(axis=1)]
    df = df[~df.iloc[:,0].str.contains("Kode", case=False, na=False)]
    idx = df[df.iloc[:,0].str.contains("Jumlah", case=False, na=False)].index
    if not idx.empty:
        df = df.loc[:idx[0]-1].reset_index(drop=True)

    # Ganti Kolom 0,1,2,3,4 yang kosong dengan NaN
    df[[0,1,2,3,4]] = df[[0,1,2,3,4]].replace('', pd.NA)

    # Buat Kolom yang Diperlukan
    df["Urusan"] = np.where((df[[1,2,3,4]].replace('', np.nan).isna().all(axis=1)) & (df[0].notna()),df[5],np.nan)        # Urusan
    df["Sub Urusan"] = np.where((df[[2,3,4]].replace('', np.nan).isna().all(axis=1)) & (df[1].notnull()),df[5],np.nan)    # Sub Urusan
    df["Program"] = np.where((df[[3,4]].replace('', np.nan).isna().all(axis=1)) & (df[2].notnull()),df[5],np.nan)         # Program
    df["Kegiatan"] = np.where((df[[4]].replace('', np.nan).isna().all(axis=1)) & (df[3].notnull()),df[5],np.nan)          # Kegiatan
    df["Sub Kegiatan"] = np.where((df[[1,2,3,4]]!='').all(axis=1), df[5], np.nan)                                         # Sub Kegiatan

    # Buat Fungsi untuk menggabungkan lembaran pdf yang terpisah halaman agar terbaca menjadi 1
    for i in range(1, len(df)):
        if df.loc[i, [0,1,2,3,4]].isna().all():  # cek jika kolom 0-4 semuanya NaN
            for col in df.columns:
                if col not in ["OPD", "Tahun"]:  # jangan gabungkan OPD & Tahun
                    if pd.notna(df.loc[i, col]):  # jika ada isi di baris sekarang
                        # gabungkan dengan isi baris sebelumnya
                        df.loc[i-1, col] = (
                            (str(df.loc[i-1, col]) if pd.notna(df.loc[i-1, col]) else "")
                            + " " +
                            str(df.loc[i, col])
                        ).strip()

    # Buat fungsi lowercase untuk menstandarisasi kolom                    
    for col in ["Urusan","Sub Urusan","Program","Kegiatan","Sub Kegiatan"]:
        df[col] = df[col].apply(proper_case).ffill()
        
    # # Isi Nilai NaN Kolom Urusan dengan nilai sebelumnya (dari atas)
    df["Urusan"]=df["Urusan"].ffill()
    df["Sub Urusan"]=df["Sub Urusan"].ffill()
    df["Program"]=df["Program"].ffill()
    df["Kegiatan"]=df["Kegiatan"].ffill()
    df["Sub Kegiatan"]=df["Sub Kegiatan"].ffill()

    # Hapus baris awal
    df = df.drop(df.index[0:8]).reset_index(drop=True)

    df[[0,1,2,3,4]] = df[[0,1,2,3,4]].replace('', pd.NA)  
    df = df.dropna(subset=[0,1,2,3,4])

    # Gabungkan kode
    df["Kode"] = df[[0,1,2,3,4]].astype(str).agg(".".join, axis=1)
    df = df.drop(columns=[0,1,2,3,4])

    df.drop(columns=[5], inplace=True)

    df.rename(columns={6:'Sumber Dana',
                        7:'Lokasi',
                        8:'Tahun - 1',
                        9:'Belanja Operasi',
                        10:'Belanja Modal',
                        11:'Belanja Tak Terduga',
                        12:'Belanja Transfer',
                        13:'Jumlah (Rp)',
                        14:'Tahun + 1',
                        }, inplace=True)

    df = df[['Kode','OPD','Urusan','Sub Urusan','Program','Kegiatan','Sub Kegiatan',
            'Sumber Dana','Lokasi','Tahun','Tahun - 1','Belanja Operasi',
            'Belanja Modal','Belanja Tak Terduga','Belanja Transfer','Jumlah (Rp)','Tahun + 1']]

    return df


if pdf_files:
    try:
        all_dfs = []
        for pdf_file in pdf_files:
            df_clean = cleaning_pdf(pdf_file)
            all_dfs.append(df_clean)

        # Merge semua dataframe
        final_df = pd.concat(all_dfs, ignore_index=True)

        # =============== CHART DENGAN STREAMLIT =================
        df2 = final_df.copy()
        df2 = df2.rename(columns={
            'Sub Urusan': 'sub_urusan',
            'Sub Kegiatan': 'sub_kegiatan',
            'Sumber Dana': 'sumber_dana',
            'Tahun - 1': 'tahun-1',
            'Belanja Operasi': 'belanja_operasi',
            'Belanja Modal': 'belanja_modal',
            'Belanja Tak Terduga': 'belanja_tak_terduga',
            'Belanja Transfer': 'belanja_transfer',
            'Jumlah (Rp)': 'jumlah',
            'Tahun + 1': 'tahun+1'
        })

        ubah_jenis = ['belanja_operasi','belanja_modal','belanja_tak_terduga',
                    'belanja_transfer','jumlah','tahun+1']

        for kol in ubah_jenis:
            df2[kol] = (
                df2[kol]
                .astype(str)
                .str.replace('Rp.', '', regex=False)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.strip()
                .astype('float')
                .astype(int)
            )

        # Dropdown untuk filter OPD
        opd_list = df2["OPD"].unique().tolist()  # pastikan ada kolom "OPD"
        selected_opd = st.selectbox("Pilih OPD:", ["Semua OPD"] + opd_list)

        if selected_opd != "Semua OPD":
            df2 = df2[df2["OPD"] == selected_opd]

        # Barchart
        kategori = ['belanja_operasi','belanja_modal','belanja_tak_terduga','belanja_transfer']
        totals = {kol: df2[kol].sum() for kol in kategori if kol in df2.columns}

        df_chart = pd.DataFrame({
            "Kategori": totals.keys(),
            "Total": totals.values()
        })

        fig = px.bar(df_chart, x="Kategori", y="Total", text="Total",
                    title=f"Total Belanja per Kategori ({selected_opd})", color="Kategori")

        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside")
        st.plotly_chart(fig, use_container_width=True)



        # =============== DOWNLOAD EXCEL =================
        output = BytesIO()
        df2.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)


        #==== Preview Cleaning 
        st.markdown(f"<p style='font-size:16px; font-weight:bold;'>Preview Data Cleaning ({selected_opd})</p>", unsafe_allow_html=True)
        st.dataframe(df2)


        #==== Tombol Download Data Cleaning
        st.download_button(
            label="Download Excel File",
            data=output,
            file_name="output_cleaned_merge.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Terjadi error saat membaca PDF: {e}")
