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
# 📌 DESVIACIÓN INTRAPERSONA
#    El 10% inferior = "Respondió siempre igual"
# ============================================
df['Desv_Intrapersona'] = df[columnas_items].std(axis=1)
umbral_intrapersonal = df['Desv_Intrapersona'].quantile(0.10)
df['Respondio_Siempre_Igual'] = df['Desv_Intrapersona'] <= umbral_intrapersonal

st.caption(
    f"Criterio de calidad de respuesta: el 10% inferior de la desviación intrapersona "
    f"se clasifica como 'Respondió siempre igual'. Umbral actual = {umbral_intrapersonal:.4f}"
)

# ============================================
# 📌 MAPEO DE ÍTEMS A ÁREAS
# ============================================
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

def col_item(num: int) -> str:
    return columnas_items[num - 1]

for area in areas:
    df[f'INTERES_{area}'] = df[[col_item(i) for i in intereses_items[area]]].sum(axis=1)
    df[f'APTITUD_{area}'] = df[[col_item(i) for i in aptitudes_items[area]]].sum(axis=1)

# ============================================
# 📌 PONDERACIÓN
# ============================================
peso_intereses, peso_aptitudes = 0.8, 0.2
for area in areas:
    df[f'PUNTAJE_COMBINADO_{area}'] = (
        df[f'INTERES_{area}'] * peso_intereses
        + df[f'APTITUD_{area}'] * peso_aptitudes
    )

df['Area_Fuerte_Ponderada'] = df.apply(
    lambda fila: max(areas, key=lambda a: fila[f'PUNTAJE_COMBINADO_{a}']),
    axis=1
)

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
    if not perfil:
        return 'Sin perfil definido'
    if area_chaside in perfil.get('Fuerte', []):
        return 'Coherente'
    if area_chaside in perfil.get('Baja', []):
        return 'Requiere Orientación'
    return 'Neutral'

df['Coincidencia_Ponderada'] = df.apply(
    lambda r: evaluar(r['Area_Fuerte_Ponderada'], r[columna_carrera]),
    axis=1
)

# ============================================
# 📌 DIAGNÓSTICO Y SEMÁFORO
# ============================================
def carrera_mejor(r):
    if r['Respondio_Siempre_Igual']:
        return 'Información no confiable'
    a = r['Area_Fuerte_Ponderada']
    sugeridas = [c for c, p in perfil_carreras.items() if a in p.get('Fuerte', [])]
    return (
        r[columna_carrera]
        if r[columna_carrera] in sugeridas
        else (', '.join(sugeridas) if sugeridas else 'Sin sugerencia clara')
    )

def diagnostico(r):
    if r['Carrera_Mejor_Perfilada'] == 'Información no confiable':
        return 'Información no confiable'
    if str(r[columna_carrera]).strip() == str(r['Carrera_Mejor_Perfilada']).strip():
        return 'Perfil adecuado'
    if r['Carrera_Mejor_Perfilada'] == 'Sin sugerencia clara':
        return 'Sin sugerencia clara'
    return f"Sugerencia: {r['Carrera_Mejor_Perfilada']}"

def semaforo(r):
    diag = r['Diagnóstico Primario Vocacional']
    if diag == 'Información no confiable':
        return 'Respondió siempre igual'
    if diag == 'Sin sugerencia clara':
        return 'Sin sugerencia'
    if diag == 'Perfil adecuado' and r['Coincidencia_Ponderada'] == 'Coherente':
        return 'Verde'
    if diag == 'Perfil adecuado' and r['Coincidencia_Ponderada'] == 'Neutral':
        return 'Amarillo'
    if diag == 'Perfil adecuado' and r['Coincidencia_Ponderada'] == 'Requiere Orientación':
        return 'Rojo'
    if isinstance(diag, str) and diag.startswith('Sugerencia:') and r['Coincidencia_Ponderada'] == 'Coherente':
        return 'Verde'
    if isinstance(diag, str) and diag.startswith('Sugerencia:') and r['Coincidencia_Ponderada'] == 'Neutral':
        return 'Amarillo'
    if isinstance(diag, str) and diag.startswith('Sugerencia:') and r['Coincidencia_Ponderada'] == 'Requiere Orientación':
        return 'Rojo'
    return 'Sin sugerencia'

df['Carrera_Mejor_Perfilada'] = df.apply(carrera_mejor, axis=1)
df['Diagnóstico Primario Vocacional'] = df.apply(diagnostico, axis=1)
df['Semáforo Vocacional'] = df.apply(semaforo, axis=1)
# ============================================

# ============================================
# 📌 DIAGRAMA DE PASTEL
# ============================================
st.subheader("🥧 Diagnóstico general (Pastel)")

# Renombrar categorías para visualización
mapa_categorias_pastel = {
    'Verde': 'El perfil coincide con la carrera elegida',
    'Amarillo': 'El perfil NO va acorde con la carrera elegida',
    'Sin sugerencia': 'No se observa un perfil prioritario',
    'Respondió siempre igual': 'Respondió siempre igual',
    'Rojo': 'No se observa un perfil prioritario'
}

df_pastel = df.copy()
df_pastel['Categoría_Pastel'] = df_pastel['Semáforo Vocacional'].replace(mapa_categorias_pastel)

resumen = (
    df_pastel['Categoría_Pastel']
    .value_counts()
    .reset_index()
)
resumen.columns = ['Categoría', 'N']

orden_pastel = [
    'El perfil coincide con la carrera elegida',
    'El perfil NO va acorde con la carrera elegida',
    'No se observa un perfil prioritario',
    'Respondió siempre igual'
]

resumen['Categoría'] = pd.Categorical(
    resumen['Categoría'],
    categories=orden_pastel,
    ordered=True
)
resumen = resumen.sort_values('Categoría')

fig = px.pie(
    resumen,
    names='Categoría',
    values='N',
    hole=0.35,
    color='Categoría',
    color_discrete_map={
        'El perfil coincide con la carrera elegida': '#22c55e',
        'El perfil NO va acorde con la carrera elegida': '#f59e0b',
        'No se observa un perfil prioritario': '#6b7280',
        'Respondió siempre igual': '#ef4444'
    }
)

# Solo porcentaje dentro del pastel
fig.update_traces(
    textposition='inside',
    texttemplate='%{percent:.1%}',
    hovertemplate='<b>%{label}</b><br>Porcentaje: %{percent}<br>N: %{value}<extra></extra>'
)

fig.update_layout(
    legend_title_text="Categoría",
    legend=dict(
        orientation="v",
        y=0.5,
        yanchor="middle",
        x=1.02,
        xanchor="left"
    )
)

st.plotly_chart(fig, use_container_width=True)
# ============================================
# 📊 Barras apiladas por carrera (porcentaje vs cantidad)
# ============================================
st.header("📊 Distribución por carrera y categoría")

cats_order = ['Verde', 'Amarillo', 'Rojo', 'Respondió siempre igual', 'Sin sugerencia']
color_map = {
    'Verde': '#22c55e',
    'Amarillo': '#f59e0b',
    'Rojo': '#94a3b8',
    'Respondió siempre igual': '#ef4444',
    'Sin sugerencia': '#6b7280'
}

stacked = (
    df[df['Semáforo Vocacional'].isin(cats_order)]
    .groupby([columna_carrera, 'Semáforo Vocacional'], dropna=False)
    .size()
    .reset_index(name='N')
    .rename(columns={'Semáforo Vocacional': 'Categoría'})
)

stacked['Categoría'] = pd.Categorical(stacked['Categoría'], categories=cats_order, ordered=True)

modo = st.radio(
    "Modo de visualización",
    options=["Proporción (100% apilado)", "Valores absolutos"],
    horizontal=True,
    index=0
)

if modo == "Proporción (100% apilado)":
    stacked['%'] = (
        stacked.groupby(columna_carrera)['N']
        .transform(lambda x: 0 if x.sum() == 0 else (x / x.sum() * 100))
    )
    fig_stacked = px.bar(
        stacked,
        x=columna_carrera,
        y='%',
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
        x=columna_carrera,
        y='N',
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
# 🎻 Diagrama de violín – Verde vs Amarillo
# ============================================
# ============================================
# 📊 Barra vertical de intensidad – Amarillo vs Verde
# ============================================
st.header("📊 Intensidad del perfil vocacional por carrera")

st.caption(
    "La barra apilada ordena a los estudiantes desde el nivel más bajo del grupo amarillo "
    "hasta el nivel más alto del grupo verde. El gradiente rojo→verde facilita identificar "
    "riesgo vocacional y potencial de ajuste al perfil."
)

df_intensidad = df.copy()
df_intensidad['Score'] = df_intensidad[[f'PUNTAJE_COMBINADO_{a}' for a in areas]].max(axis=1)

# Solo usamos Verde y Amarillo
df_intensidad = df_intensidad[df_intensidad['Semáforo Vocacional'].isin(['Verde', 'Amarillo'])].copy()

if df_intensidad.empty:
    st.info("No hay estudiantes en categorías Verde o Amarillo para construir la barra de intensidad.")
else:
    def asignar_bloques_por_carrera(grupo):
        grupo = grupo.copy()

        amar = grupo[grupo['Semáforo Vocacional'] == 'Amarillo'].copy()
        ver = grupo[grupo['Semáforo Vocacional'] == 'Verde'].copy()

        # Inicializar
        grupo['Bloque_Intensidad'] = np.nan

        # Amarillo: del peor al mejor
        if len(amar) > 0:
            amar = amar.sort_values('Score', ascending=True).copy()
            amar['rank_pct'] = (np.arange(len(amar)) + 1) / len(amar)

            amar['Bloque_Intensidad'] = np.select(
                [
                    amar['rank_pct'] <= 0.25,
                    amar['rank_pct'] <= 0.50,
                    amar['rank_pct'] <= 0.75,
                    amar['rank_pct'] <= 1.00,
                ],
                ['A4', 'A3', 'A2', 'A1'],
                default='A1'
            )
            grupo.loc[amar.index, 'Bloque_Intensidad'] = amar['Bloque_Intensidad']

        # Verde: del más bajo al más alto
        if len(ver) > 0:
            ver = ver.sort_values('Score', ascending=True).copy()
            ver['rank_pct'] = (np.arange(len(ver)) + 1) / len(ver)

            ver['Bloque_Intensidad'] = np.select(
                [
                    ver['rank_pct'] <= 0.25,
                    ver['rank_pct'] <= 0.50,
                    ver['rank_pct'] <= 0.75,
                    ver['rank_pct'] <= 1.00,
                ],
                ['V4', 'V3', 'V2', 'V1'],
                default='V1'
            )
            grupo.loc[ver.index, 'Bloque_Intensidad'] = ver['Bloque_Intensidad']

        return grupo

    df_intensidad = (
        df_intensidad
        .groupby(columna_carrera, group_keys=False)
        .apply(asignar_bloques_por_carrera)
        .copy()
    )

    orden_bloques = ['A4', 'A3', 'A2', 'A1', 'V4', 'V3', 'V2', 'V1']

    etiquetas_bloques = {
        'A4': 'Sin perfil',
        'A3': 'Amarillo - Cuartil 3',
        'A2': 'Amarillo - Cuartil 2',
        'A1': 'Amarillo - Cuartil 1',
        'V4': 'Verde - Cuartil 4',
        'V3': 'Verde - Cuartil 3',
        'V2': 'Verde - Cuartil 2',
        'V1': 'Jóven promesa'
    }

    colores_bloques = {
        'A4': '#b91c1c',   # rojo intenso
        'A3': '#dc2626',   # rojo
        'A2': '#f97316',   # naranja
        'A1': '#f59e0b',   # ámbar
        'V4': '#a3e635',   # lima
        'V3': '#4ade80',   # verde claro
        'V2': '#22c55e',   # verde
        'V1': '#15803d'    # verde profundo
    }

    resumen_intensidad = (
        df_intensidad
        .groupby([columna_carrera, 'Bloque_Intensidad'], dropna=False)
        .size()
        .reset_index(name='N')
    )

    resumen_intensidad['Bloque_Intensidad'] = pd.Categorical(
        resumen_intensidad['Bloque_Intensidad'],
        categories=orden_bloques,
        ordered=True
    )

    # porcentaje acumulado por carrera
    resumen_intensidad['%'] = (
        resumen_intensidad.groupby(columna_carrera)['N']
        .transform(lambda x: 0 if x.sum() == 0 else (x / x.sum() * 100))
    )

    resumen_intensidad['Etiqueta'] = resumen_intensidad['Bloque_Intensidad'].map(etiquetas_bloques)

    fig_intensidad = px.bar(
        resumen_intensidad,
        x=columna_carrera,
        y='%',
        color='Bloque_Intensidad',
        category_orders={'Bloque_Intensidad': orden_bloques},
        color_discrete_map=colores_bloques,
        barmode='stack',
        text=resumen_intensidad['%'].round(1).astype(str) + '%',
        title="Escala de intensidad vocacional por carrera"
    )

    fig_intensidad.update_layout(
        yaxis_title="Proporción (%)",
        xaxis_title="Carrera",
        xaxis_tickangle=-30,
        height=720,
        legend_title_text="Nivel de intensidad"
    )

    fig_intensidad.update_traces(
        hovertemplate="<b>%{x}</b><br>%{customdata[0]}<br>Porcentaje: %{y:.1f}%<extra></extra>",
        customdata=np.stack([resumen_intensidad['Etiqueta']], axis=-1)
    )

    st.plotly_chart(fig_intensidad, use_container_width=True)

    st.markdown("### Lectura sugerida de la escala")
    st.markdown("""
- **Sin perfil**: estudiantes ubicados en el tramo más bajo del grupo amarillo.  
- **Perfil en riesgo**: estudiantes aún en amarillo, pero con mejor puntaje relativo.  
- **Perfil en transición**: estudiantes ya en verde, aunque todavía en los tramos bajos o medios.  
- **Jóven promesa**: estudiantes en el cuartil más alto del grupo verde.  
""")

# ============================================
# 🕸️ Radar CHASIDE por carrera · Verde vs Amarillo
# ============================================
st.header("🕸️ Radar CHASIDE por carrera – Verde vs Amarillo")

df_radar = df.copy()
for a in areas:
    df_radar[a] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

df_radar['Categoría'] = df['Semáforo Vocacional']
df_radar['Carrera'] = df[columna_carrera]

descripciones_chaside = {
    "C": "Organización, orden, análisis/síntesis, colaboración, cálculo.",
    "H": "Precisión verbal, relación de hechos, justicia, persuasión.",
    "A": "Creatividad, detalle, intuición; habilidades visuales/auditivas/manuales.",
    "S": "Investigación, precisión, percepción, análisis; altruismo y paciencia.",
    "I": "Cálculo, pensamiento científico/crítico, exactitud, planificación.",
    "D": "Justicia, equidad, colaboración, liderazgo; toma de decisiones.",
    "E": "Investigación, análisis y síntesis, cálculo numérico, observación, método."
}

carreras_disp = sorted(df_radar['Carrera'].dropna().unique())
if not carreras_disp:
    st.info("No hay carreras para mostrar en el radar.")
else:
    tabs = st.tabs(carreras_disp)

    for tab, carrera_sel in zip(tabs, carreras_disp):
        with tab:
            sub = df_radar[df_radar['Carrera'] == carrera_sel]
            sub = sub[sub['Categoría'].isin(['Verde', 'Amarillo'])]

            if sub.empty or sub['Categoría'].nunique() < 2:
                st.warning("No hay datos suficientes de Verde y Amarillo en esta carrera.")
                continue

            prom = sub.groupby('Categoría')[areas].mean().reset_index()

            fig = px.line_polar(
                prom.melt(id_vars='Categoría', value_vars=areas, var_name='Área', value_name='Promedio'),
                r='Promedio',
                theta='Área',
                color='Categoría',
                line_close=True,
                markers=True,
                color_discrete_map={'Verde': '#22c55e', 'Amarillo': '#f59e0b'},
                title=f"Perfil CHASIDE – {carrera_sel}"
            )
            fig.update_traces(fill='toself', opacity=0.75)
            st.plotly_chart(fig, use_container_width=True)

            prom_w = sub.groupby('Categoría')[areas].mean()
            diffs = (prom_w.loc['Verde'] - prom_w.loc['Amarillo']).sort_values(ascending=False)
            top3 = diffs.head(3)

            st.markdown("**Áreas a reforzar (donde *Amarillo* está más bajo):**")
            for letra, delta in top3.items():
                st.markdown(f"- **{letra}** (Δ = {delta:.2f}): {descripciones_chaside[letra]}")
