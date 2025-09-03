import streamlit as st
import numpy as np
import pandas as pd
from io import BytesIO
import re
# import pdfplumber
# import tabula  # pip install tabula-py
# import plotly.express as px

st.title("Preprocessing & Analytic Data RKA SKPD")
pdf_file = st.file_uploader("Upload file PDF", type="pdf")

if pdf_file:
    try:
        # Membaca PDF menjadi DataFrame (semua halaman)
        # dfs = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True)
        data = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # Ekstrak tabel dari halaman
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        data.append(row) 
        df = pd.DataFrame(data)

        # Gabungkan semua tabel menjadi satu DataFrame
        # df = pd.concat(dfs, ignore_index=True)

        # st.write("Preview Data Sebelum cleaning:")
        # st.dataframe(df)

        ################### PROSES CLEANING DATA

        def fungsi_lowercase(text):
            exceptions = {"dan", "atau", "di", "ke", "dari", "yang", "untuk"}  # kata penghubung
            words = text.lower().split()
            result = []
            for i, word in enumerate(words):
                if word in exceptions and i != 0:  # biarkan lowercase kecuali kata pertama
                    result.append(word)
                else:
                    result.append(word.capitalize())
            return " ".join(result)

        # Fungsi Lowercase untuk elemen kolom
        def proper_case(text):
            # daftar kata penghubung yang dikecualikan
            exceptions = {"dan", "atau", "di", "ke", "dari", "yang", "untuk", "pada", "dengan"}
            
            if pd.isna(text):  # kalau NaN biarkan saja
                return text
            
            words = text.lower().split()
            result = []
            for i, word in enumerate(words):
                # kapitalisasi hanya kalau bukan kata penghubung
                # kecuali kalau kata pertama, tetap kapital
                if word in exceptions and i != 0:
                    result.append(word)
                else:
                    result.append(word.capitalize())
            return " ".join(result)
        
        # Buat Kolom OPD
        opd_elemen = df.iloc[2,2]
        opd_elemen = fungsi_lowercase(opd_elemen)
        df['OPD'] = opd_elemen

        # Buat Kolom Tahun
        tahun_elemen = df.iloc[1,0]
        tahun_elemen = int(re.search(r'\d{4}', tahun_elemen).group()) 
        df['Tahun'] = tahun_elemen

        # Hapus Baris yang Tidak diperlukan
        df = df[~df[[0,1,2,3,4]].isnull().all(axis=1)]                              # Jika kolom 0 sampai 4 adalah Null maka hapuslah baris tersebut
        df = df[~df.iloc[:,0].str.contains("Kode", case=False, na=False)]           # Jika pada kolom 1 terdapat kata Kode maka hapuslah baris tersebut
        idx = df[df.iloc[:,0].str.contains("Jumlah", case=False, na=False)].index   # Jika pada kolom 1 terdapat kata Jumlah maka hapus seluruh baris di bawahnya termasuk baris Jumlah
        if not idx.empty:
            # ambil baris sebelum 'Jumlah'
            df = df.loc[:idx[0]-1].reset_index(drop=True)

        df["Urusan"] = np.where((df[[1,2,3,4]].isnull() | (df[[1,2,3,4]] == '')).all(axis=1),df[5],np.nan)
        df["Sub Urusan"] = np.where((df[[2,3,4]]=='').all(axis=1) & (df[[1]]!='').all(axis=1), df[5], np.nan) # Sub Urusan
        df["Program"] = np.where((df[[3,4]]=='').all(axis=1) & (df[[2]]!='').all(axis=1), df[5], np.nan) # Sub Urusan
        df["Kegiatan"] = np.where((df[[4]]=='').all(axis=1) & (df[[3]]!='').all(axis=1), df[5], np.nan) # Sub Urusan
        df["Sub Kegiatan"] = np.where((df[[1,2,3,4]]!='').all(axis=1), df[5], np.nan) # Sub Urusan

        df["Urusan"] = df["Urusan"].apply(proper_case)
        df["Sub Urusan"] = df["Sub Urusan"].apply(proper_case)
        df["Program"] = df["Program"].apply(proper_case)
        df["Kegiatan"] = df["Kegiatan"].apply(proper_case)
        df["Sub Kegiatan"] = df["Sub Kegiatan"].apply(proper_case)

        # Isi Nilai NaN Kolom Urusan dengan nilai sebelumnya (dari atas)
        df["Urusan"]=df["Urusan"].ffill()
        df["Sub Urusan"]=df["Sub Urusan"].ffill()
        df["Program"]=df["Program"].ffill()
        df["Kegiatan"]=df["Kegiatan"].ffill()
        df["Sub Kegiatan"]=df["Sub Kegiatan"].ffill()

        # Hapus baris 1 sampai 7 dan reset index
        df = df.drop(df.index[0:8]).reset_index(drop=True)

        # Habus Baris Jika Salah satu kolomnya null
        df[[0,1,2,3,4]] = df[[0,1,2,3,4]].replace('', pd.NA)
        df = df.dropna(subset=[0,1,2,3,4])


        # Gabungkan Kolom dan beri pemisah '.'
        df["Kode"] = df[[0,1,2,3,4]].astype(str).agg(".".join, axis=1)      # Gabungkan kolom 0-4 jadi satu kolom string (pakai titik sebagai pemisah)
        df = df.drop(columns=[0,1,2,3,4])                                   # Hapus kolom lama 0-4
        cols = ["Kode"] + [c for c in df.columns if c != "Kode"]            # Susun ulang kolom agar "Kode" ada di depan
        df = df[cols]

        # Hapus Kolom dan baris yang tidak diperlukan
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

        df = df[['Kode','OPD','Urusan','Sub Urusan','Program','Kegiatan','Sub Kegiatan','Sumber Dana','Lokasi','Tahun','Tahun - 1','Belanja Operasi',
                'Belanja Modal','Belanja Tak Terduga','Belanja Transfer','Jumlah (Rp)','Tahun + 1']]



        ################### CHART DENGAN STREAMLIT
        df2 = df.copy()
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
                .astype(str)                        # pastikan string
                .str.replace('Rp.', '', regex=False) # hapus Rp.
                .str.replace('.', '', regex=False)   # hapus titik ribuan
                .str.replace(',', '.', regex=False)  # ganti koma ke titik
                .str.strip()
                .astype('float')                       # ubah ke float
                .astype(int)                            # ubah lagi ke integer (hilangkan koma)
            )

        # st.subheader("Jumlah Urusan")
        # # Hitung Jumlah Belanja
        # jumlah_belanja = df2['jumlah'].sum()
        # jumlah_belanja_str = f"Rp {jumlah_belanja:,}".replace(",",".") # Konversi ke Indo
        # st.metric(label="Jumlah Belanja", value=jumlah_belanja_str) # Hitung jumlah belanja

        # # Hitung Jumlah Belanja Operasi
        # belanja_operasi = df2['belanja_operasi'].sum()
        # belanja_operasi_str = f"Rp {belanja_operasi:,}".replace(",",".") # Konversi ke Indo
        # st.metric(label="Belanja Operasi", value=belanja_operasi_str) # Hitung jumlah belanja

        # # Hitung Jumlah Belanja Modal
        # belanja_modal = df2['belanja_modal'].sum()
        # belanja_modal_str = f"Rp {belanja_modal:,}".replace(",",".") # Konversi ke Indo
        # st.metric(label="Belanja Operasi", value=belanja_modal_str) # Hitung jumlah belanja

        # Barchart
        kategori = ['belanja_operasi','belanja_modal','belanja_tak_terduga','belanja_transfer']
        totals = {kol: df2[kol].astype(str).str.replace("Rp ", "").str.replace(".", "").astype(float).sum() 
              for kol in kategori if kol in df2.columns}
        
        df_chart = pd.DataFrame({
            "Kategori": totals.keys(),
            "Total": totals.values()
            })
        
        fig = px.bar(df_chart, x="Kategori", y="Total", text="Total",
             title="Total Belanja per Kategori", color="Kategori")

        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside")
        st.plotly_chart(fig, use_container_width=True)


        ################### PREVIEW SETELAH CLEANING      
          
        st.write("Preview Data Cleaning:")
        st.dataframe(df2)

        # Convert DataFrame ke Excel
        output = BytesIO()
        df2.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        # Tombol download
        st.download_button(
            label="Download Excel",
            data=output,
            file_name="output_cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Terjadi error saat membaca PDF: {e}")







