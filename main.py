# ============================
# MÓDULO 2 · INFORMACIÓN GENERAL
# ============================
# Uso standalone: streamlit run informacion_general.py
# Uso modular: from informacion_general import render_informacion_general; render_informacion_general()

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# -----------------------------------
# CONFIG STREAMLIT (solo si es standalone)
# -----------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="Información general • CHASIDE", layout="wide")

# -----------------------------------
# FUNCIÓN PRINCIPAL DEL MÓDULO
# -----------------------------------
def render_informacion_general():
    st.title("📊 Información general – Escala CHASIDE")

    # ============================================
    # 📌 LECTURA DE DATOS
    # ============================================
    st.subheader("Carga de datos")
    url = st.text_input("URL de Google Sheets (CSV export)", 
                        "https://docs.google.com/spreadsheets/d/1BNAeOSj2F378vcJE5-T8iJ8hvoseOleOHr-I7mVfYu4/export?format=csv")

    try:
        df = pd.read_csv(url)
        st.success("✅ Datos cargados correctamente")
        st.dataframe(df.head(), use_container_width=True)
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {e}")
        return

    # ============================================
    # 📌 PROCESAMIENTO CHASIDE
    # ============================================
    # columnas esperadas
    columnas_items = df.columns[5:103]
    columna_carrera = '¿A qué carrera desea ingresar?'
    columna_nombre = 'Ingrese su nombre completo'

    if columna_carrera not in df.columns or columna_nombre not in df.columns:
        st.error(f"❌ No se encuentran las columnas '{columna_carrera}' y '{columna_nombre}' en el archivo.")
        return

    # convertir Sí/No → 1/0
    df_items = (
        df[columnas_items]
        .astype(str).apply(lambda col: col.str.strip().str.lower())
        .replace({'sí':1,'si':1,'s':1,'1':1,'true':1,'no':0,'n':0,'0':0,'false':0})
        .apply(pd.to_numeric, errors='coerce')
        .fillna(0).astype(int)
    )
    df[columnas_items] = df_items

    # áreas y mapeo de ítems
    areas = ['C','H','A','S','I','D','E']
    intereses_items = {
        'C':[1,12,20,53,64,71,78,85,91,98],
        'H':[9,25,34,41,56,67,74,80,89,95],
        'A':[3,11,21,28,36,45,50,57,81,96],
        'S':[8,16,23,33,44,52,62,70,87,92],
        'I':[6,19,27,38,47,54,60,75,83,97],
        'D':[5,14,24,31,37,48,58,65,73,84],
        'E':[17,32,35,42,49,61,68,77,88,93]
    }
    aptitudes_items = {
        'C':[2,15,46,51],
        'H':[30,63,72,86],
        'A':[22,39,76,82],
        'S':[4,29,40,69],
        'I':[10,26,59,90],
        'D':[13,18,43,66],
        'E':[7,55,79,94]
    }
    def col_item(num): return columnas_items[num-1]

    for a in areas:
        df[f'INTERES_{a}']  = df[[col_item(i) for i in intereses_items[a]]].sum(axis=1)
        df[f'APTITUD_{a}'] = df[[col_item(i) for i in aptitudes_items[a]]].sum(axis=1)

    # ponderación configurable
    peso_intereses = st.slider("Peso Intereses", 0.0, 1.0, 0.8, 0.05)
    peso_aptitudes = 1.0 - peso_intereses
    st.caption(f"Ponderación actual: Intereses {peso_intereses:.2f} – Aptitudes {peso_aptitudes:.2f}")

    for a in areas:
        df[f'PUNTAJE_COMBINADO_{a}'] = (
            df[f'INTERES_{a}']*peso_intereses + df[f'APTITUD_{a}']*peso_aptitudes
        )
    df['Area_Fuerte_Ponderada'] = df.apply(lambda r: max(areas, key=lambda a: r[f'PUNTAJE_COMBINADO_{a}']), axis=1)

    # diagnóstico simple
    perfil_carreras = {
        'Arquitectura':['A','I','C'],
        'Contador Público':['C','D'],
        'Licenciatura en Administración':['C','D'],
        'Ingeniería Ambiental':['I','C','E'],
        'Ingeniería Bioquímica':['I','C','E'],
        'Ingeniería en Gestión Empresarial':['C','D','H'],
        'Ingeniería Industrial':['C','D','H'],
        'Ingeniería en Inteligencia Artificial':['I','E'],
        'Ingeniería Mecatrónica':['I','E'],
        'Ingeniería en Sistemas Computacionales':['I','E']
    }

    def evaluar(area, carrera):
        return 'Coherente' if area in perfil_carreras.get(str(carrera).strip(),[]) else 'Neutral'

    df['Coincidencia_Ponderada'] = df.apply(lambda r: evaluar(r['Area_Fuerte_Ponderada'], r[columna_carrera]), axis=1)

    def semaforo(r):
        if r['Coincidencia_Ponderada']=='Coherente': return 'Verde'
        return 'Amarillo' if r['Coincidencia_Ponderada']=='Neutral' else 'Sin sugerencia'

    df['Semáforo Vocacional'] = df.apply(semaforo, axis=1)

    # ============================================
    # 📌 DIAGRAMA DE PASTEL
    # ============================================
    st.subheader("🥧 Diagnóstico general (todas las carreras)")

    cats_pie = ['Verde','Amarillo','Sin sugerencia','No aceptable']
    resumen_pie = (
        df['Semáforo Vocacional']
        .value_counts()
        .reindex(cats_pie, fill_value=0)
        .reset_index()
    )
    resumen_pie.columns = ['Categoría','N']
    total = resumen_pie['N'].sum()
    resumen_pie['%'] = (resumen_pie['N']/total*100).round(1)

    fig_pie = px.pie(
        resumen_pie, names='Categoría', values='N',
        hole=0.35, color='Categoría',
        color_discrete_map={'Verde':'#22c55e','Amarillo':'#f59e0b',
                            'Sin sugerencia':'#94a3b8','No aceptable':'#ef4444'},
        title="Distribución global de diagnósticos"
    )
    fig_pie.update_traces(textposition='inside', texttemplate='%{label}<br>%{percent:.1%} (%{value})')
    st.plotly_chart(fig_pie, use_container_width=True)

    st.dataframe(resumen_pie, use_container_width=True)

# -----------------------------------
# MODO STANDALONE
# -----------------------------------
if __name__ == "__main__":
    render_informacion_general()
