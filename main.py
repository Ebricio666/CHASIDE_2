# ============================================
# 📌 IMPORTS
# ============================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ============================================
# 📌 CONFIGURACIÓN INICIAL
# ============================================
st.set_page_config(layout="wide")

st.title("Diagnóstico Vocacional - Escala CHASIDE")

# ============================================
# 📌 LECTURA DESDE GOOGLE SHEETS (como CSV)
# ============================================
url = "https://docs.google.com/spreadsheets/d/1BNAeOSj2F378vcJE5-T8iJ8hvoseOleOHr-I7mVfYu4/export?format=csv"
df = pd.read_csv(url)

# ============================================
# 📌 SELECCIÓN DE COLUMNAS
# ============================================
columnas_items = df.columns[5:103]
columna_carrera = '¿A qué carrera desea ingresar?'
columna_nombre = 'Ingrese su nombre completo'

# ============================================
# 📌 CONVERSIÓN Sí/No → 1/0
# ============================================
df_items = (
    df[columnas_items]
      .astype(str).apply(lambda col: col.str.strip().str.lower())
      .replace({
          'sí': 1, 'si': 1, 's': 1, '1': 1, 'true': 1, 'verdadero': 1, 'x': 1,
          'no': 0, 'n': 0, '0': 0, 'false': 0, 'falso': 0, '': 0, 'nan': 0
      })
      .apply(pd.to_numeric, errors='coerce')
      .fillna(0)
      .astype(int)
)
df[columnas_items] = df_items

# ============================================
# 📌 COINCIDENCIA SOSPECHOSA
# ============================================
suma_si = df[columnas_items].sum(axis=1)
total_items = len(columnas_items)
porcentaje_si = np.where(total_items == 0, 0, suma_si / total_items)
porcentaje_no = 1 - porcentaje_si
df['Coincidencia'] = np.maximum(porcentaje_si, porcentaje_no)

# ============================================
# 📌 MAPEO DE ÍTEMS A ÁREAS
# ============================================
areas = ['C','H','A','S','I','D','E']
intereses_items = {'C':[1,12,20,53,64,71,78,85,91,98],'H':[9,25,34,41,56,67,74,80,89,95],
    'A':[3,11,21,28,36,45,50,57,81,96],'S':[8,16,23,33,44,52,62,70,87,92],
    'I':[6,19,27,38,47,54,60,75,83,97],'D':[5,14,24,31,37,48,58,65,73,84],
    'E':[17,32,35,42,49,61,68,77,88,93]}
aptitudes_items = {'C':[2,15,46,51],'H':[30,63,72,86],'A':[22,39,76,82],
    'S':[4,29,40,69],'I':[10,26,59,90],'D':[13,18,43,66],'E':[7,55,79,94]}

def col_item(num:int)->str: return columnas_items[num-1]

for area in areas:
    df[f'INTERES_{area}'] = df[[col_item(i) for i in intereses_items[area]]].sum(axis=1)
    df[f'APTITUD_{area}'] = df[[col_item(i) for i in aptitudes_items[area]]].sum(axis=1)

# ============================================
# 📌 PONDERACIÓN
# ============================================
peso_intereses, peso_aptitudes = 0.8, 0.2
for area in areas:
    df[f'PUNTAJE_COMBINADO_{area}'] = df[f'INTERES_{area}']*peso_intereses + df[f'APTITUD_{area}']*peso_aptitudes
df['Area_Fuerte_Ponderada'] = df.apply(lambda fila: max(areas, key=lambda a: fila[f'PUNTAJE_COMBINADO_{a}']), axis=1)

# ============================================
# 📌 PERFILES DE CARRERAS
# ============================================
perfil_carreras = {
    'Arquitectura': {'Fuerte': ['A','I','C']},
    'Contador Público': {'Fuerte': ['C','D']},
    'Licenciatura en Administración': {'Fuerte': ['C','D']},
    'Ingeniería Ambiental': {'Fuerte': ['I','C','E']},
    'Ingeniería Bioquímica': {'Fuerte': ['I','C','E']},
    'Ingeniería en Gestión Empresarial': {'Fuerte': ['C','D','H']},
    'Ingeniería Industrial': {'Fuerte': ['C','D','H']},
    'Ingeniería en Inteligencia Artificial': {'Fuerte': ['I','E']},
    'Ingeniería Mecatrónica': {'Fuerte': ['I','E']},
    'Ingeniería en Sistemas Computacionales': {'Fuerte': ['I','E']}
}

def evaluar(area_chaside, carrera):
    perfil = perfil_carreras.get(str(carrera).strip())
    if not perfil: return 'Sin perfil definido'
    if area_chaside in perfil.get('Fuerte',[]): return 'Coherente'
    if area_chaside in perfil.get('Baja',[]): return 'Requiere Orientación'
    return 'Neutral'

df['Coincidencia_Ponderada'] = df.apply(lambda r: evaluar(r['Area_Fuerte_Ponderada'], r[columna_carrera]), axis=1)

# ============================================
# 📌 DIAGNÓSTICO Y SEMÁFORO
# ============================================
def carrera_mejor(r):
    if r['Coincidencia'] >= 0.75: return 'Información no aceptable'
    a = r['Area_Fuerte_Ponderada']
    sugeridas = [c for c,p in perfil_carreras.items() if a in p.get('Fuerte',[])]
    return r[columna_carrera] if r[columna_carrera] in sugeridas else (', '.join(sugeridas) if sugeridas else 'Sin sugerencia clara')

def diagnostico(r):
    if r['Carrera_Mejor_Perfilada']=='Información no aceptable': return 'Información no aceptable'
    if str(r[columna_carrera]).strip()==str(r['Carrera_Mejor_Perfilada']).strip(): return 'Perfil adecuado'
    if r['Carrera_Mejor_Perfilada']=='Sin sugerencia clara': return 'Sin sugerencia clara'
    return f"Sugerencia: {r['Carrera_Mejor_Perfilada']}"

def semaforo(r):
    diag=r['Diagnóstico Primario Vocacional']
    if diag=='Información no aceptable': return 'No aceptable'
    if diag=='Sin sugerencia clara': return 'Sin sugerencia'
    if diag=='Perfil adecuado' and r['Coincidencia_Ponderada']=='Coherente': return 'Verde'
    if diag=='Perfil adecuado' and r['Coincidencia_Ponderada']=='Neutral': return 'Amarillo'
    if diag=='Perfil adecuado' and r['Coincidencia_Ponderada']=='Requiere Orientación': return 'Rojo'
    if diag.startswith('Sugerencia:') and r['Coincidencia_Ponderada']=='Coherente': return 'Verde'
    if diag.startswith('Sugerencia:') and r['Coincidencia_Ponderada']=='Neutral': return 'Amarillo'
    if diag.startswith('Sugerencia:') and r['Coincidencia_Ponderada']=='Requiere Orientación': return 'Rojo'
    return 'Sin sugerencia'

df['Carrera_Mejor_Perfilada']=df.apply(carrera_mejor,axis=1)
df['Diagnóstico Primario Vocacional']=df.apply(diagnostico,axis=1)
df['Semáforo Vocacional']=df.apply(semaforo,axis=1)

# ============================================
# 📌 DIAGRAMA DE PASTEL
# ============================================
st.subheader("🥧 Diagnóstico general (Pastel)")
resumen = df['Semáforo Vocacional'].value_counts().reset_index()
resumen.columns=['Categoría','N']
fig = px.pie(
    resumen,
    names='Categoría',
    values='N',
    hole=0.35,
    color='Categoría',
    color_discrete_map={
        'Verde':'#22c55e','Amarillo':'#f59e0b','Rojo':'#ef4444',
        'No aceptable':'#6b7280','Sin sugerencia':'#94a3b8'
    }
)
fig.update_traces(textposition='inside', texttemplate='%{label}<br>%{percent:.1%} (%{value})')
st.plotly_chart(fig,use_container_width=True)

# ============================================
# 📊 Barras apiladas por carrera (porcentaje vs cantidad)
#    Categorías: Verde, Amarillo, No aceptable, Sin sugerencia
# ============================================
st.header("📊 Distribución por carrera y categoría")

cats_order = ['Verde', 'Amarillo', 'No aceptable', 'Sin sugerencia']
color_map = {
    'Verde': '#22c55e',
    'Amarillo': '#f59e0b',
    'No aceptable': '#ef4444',
    'Sin sugerencia': '#94a3b8'
}

# Agregado base
stacked = (
    df[df['Semáforo Vocacional'].isin(cats_order)]
    .groupby([columna_carrera, 'Semáforo Vocacional'], dropna=False)
    .size()
    .reset_index(name='N')
    .rename(columns={'Semáforo Vocacional': 'Categoría'})
)

# Asegurar orden categórico
stacked['Categoría'] = pd.Categorical(stacked['Categoría'], categories=cats_order, ordered=True)

# Selector de modo
modo = st.radio(
    "Modo de visualización",
    options=["Proporción (100% apilado)", "Valores absolutos"],
    horizontal=True,
    index=0
)

if modo == "Proporción (100% apilado)":
    # porcentaje dentro de cada carrera
    stacked['%'] = (
        stacked.groupby(columna_carrera)['N']
        .transform(lambda x: 0 if x.sum()==0 else (x / x.sum() * 100))
    )
    fig_stacked = px.bar(
        stacked,
        x=columna_carrera, y='%',
        color='Categoría',
        category_orders={'Categoría': cats_order},
        color_discrete_map=color_map,
        barmode='stack',
        text=stacked['%'].round(1).astype(str) + '%',
        title="Proporción (%) de estudiantes por carrera y categoría"
    )
    fig_stacked.update_layout(
        yaxis_title="Proporción (%)",
        xaxis_title="Carrera",
        xaxis_tickangle=-30,
        height=620
    )
else:
    fig_stacked = px.bar(
        stacked,
        x=columna_carrera, y='N',
        color='Categoría',
        category_orders={'Categoría': cats_order},
        color_discrete_map=color_map,
        barmode='stack',
        text='N',
        title="Estudiantes por carrera y categoría (valores absolutos)"
    )
    fig_stacked.update_layout(
        yaxis_title="Número de estudiantes",
        xaxis_title="Carrera",
        xaxis_tickangle=-30,
        height=620
    )
    fig_stacked.update_traces(textposition='inside', cliponaxis=False)

st.plotly_chart(fig_stacked, use_container_width=True)

# ============================================
# 🎻 Diagrama de violín – Verde vs Amarillo (sin puntos)
# ============================================
st.header("🎻 Distribución de puntajes (Violin plot) – Verde vs Amarillo")

# Score máximo ponderado
score_cols = [f'PUNTAJE_COMBINADO_{a}' for a in areas]
df_scores = df.copy()
df_scores['Score'] = df_scores[score_cols].max(axis=1)

# Filtrar solo Verde y Amarillo
df_violin = df_scores[df_scores['Semáforo Vocacional'].isin(['Verde','Amarillo'])].copy()

if df_violin.empty:
    st.info("No hay estudiantes en categorías Verde o Amarillo para graficar.")
else:
    fig_violin = px.violin(
        df_violin,
        x=columna_carrera,
        y="Score",
        color="Semáforo Vocacional",
        box=True,            # añade boxplot interno
        points=False,        # 🔹 sin puntos
        color_discrete_map={"Verde":"#22c55e","Amarillo":"#f59e0b"},
        title="Distribución de puntajes por carrera (Verde vs Amarillo)"
    )

    fig_violin.update_layout(
        xaxis_title="Carrera",
        yaxis_title="Score combinado",
        xaxis_tickangle=-30,
        height=720
    )
    st.plotly_chart(fig_violin, use_container_width=True)
