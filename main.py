# ============================================
# 📌 IMPORTS
# ============================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
areas = ['C', 'H', 'A', 'S', 'I', 'D', 'E']

intereses_items = {
    'C': [1, 12, 20, 53, 64, 71, 78, 85, 91, 98],
    'H': [9, 25, 34, 41, 56, 67, 74, 80, 89, 95],
    'A': [3, 11, 21, 28, 36, 45, 50, 57, 81, 96],
    'S': [8, 16, 23, 33, 44, 52, 62, 70, 87, 92],
    'I': [6, 19, 27, 38, 47, 54, 60, 75, 83, 97],
    'D': [5, 14, 24, 31, 37, 48, 58, 65, 73, 84],
    'E': [17, 32, 35, 42, 49, 61, 68, 77, 88, 93]
}

aptitudes_items = {
    'C': [2, 15, 46, 51],
    'H': [30, 63, 72, 86],
    'A': [22, 39, 76, 82],
    'S': [4, 29, 40, 69],
    'I': [10, 26, 59, 90],
    'D': [13, 18, 43, 66],
    'E': [7, 55, 79, 94]
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
        df[f'INTERES_{area}'] * peso_intereses +
        df[f'APTITUD_{area}'] * peso_aptitudes
    )
    df[f'TOTAL_{area}'] = df[f'INTERES_{area}'] + df[f'APTITUD_{area}']

df['Area_Fuerte_Ponderada'] = df.apply(
    lambda fila: max(areas, key=lambda a: fila[f'PUNTAJE_COMBINADO_{a}']),
    axis=1
)

# ============================================
# 📌 PERFILES DE CARRERAS
# ============================================
perfil_carreras = {
    'Arquitectura': {'Fuerte': ['A', 'I', 'C']},
    'Contador Público': {'Fuerte': ['C', 'D']},
    'Licenciatura en Administración': {'Fuerte': ['C', 'D']},
    'Ingeniería Ambiental': {'Fuerte': ['I', 'C', 'E']},
    'Ingeniería Bioquímica': {'Fuerte': ['I', 'C', 'E']},
    'Ingeniería en Gestión Empresarial': {'Fuerte': ['C', 'D', 'H']},
    'Ingeniería Industrial': {'Fuerte': ['C', 'D', 'H']},
    'Ingeniería en Inteligencia Artificial': {'Fuerte': ['I', 'E']},
    'Ingeniería Mecatrónica': {'Fuerte': ['I', 'E']},
    'Ingeniería en Sistemas Computacionales': {'Fuerte': ['I', 'E']}
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
# 📌 DISTRIBUCIÓN DE RESPUESTAS DEL ESTUDIANTADO
# ============================================
st.subheader("📊 Distribución de respuestas del estudiantado")

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

# Calcular porcentajes
total_estudiantes = int(resumen['N'].sum())
resumen['Porcentaje'] = np.where(
    total_estudiantes == 0,
    0,
    resumen['N'] / total_estudiantes * 100
)

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

fig.update_traces(
    textposition='inside',
    texttemplate='%{percent:.1%}',
    hovertemplate='<b>%{label}</b><br>Porcentaje: %{percent}<br>N: %{value}<extra></extra>'
)

fig.update_layout(
    legend_title_text="Categoría",
    legend=dict(
        orientation="h",
        y=-0.15,
        yanchor="top",
        x=0.5,
        xanchor="center"
    ),
    margin=dict(t=40, b=120)
)

st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📌 REPORTE AUTOMÁTICO DEL DIAGRAMA DE PASTEL
# ============================================
conteos = resumen.set_index('Categoría')['N'].to_dict()
porcentajes = resumen.set_index('Categoría')['Porcentaje'].to_dict()

n_coincide = conteos.get('El perfil coincide con la carrera elegida', 0)
p_coincide = porcentajes.get('El perfil coincide con la carrera elegida', 0)

n_no_accorde = conteos.get('El perfil NO va acorde con la carrera elegida', 0)
p_no_accorde = porcentajes.get('El perfil NO va acorde con la carrera elegida', 0)

n_sin_prioritario = conteos.get('No se observa un perfil prioritario', 0)
p_sin_prioritario = porcentajes.get('No se observa un perfil prioritario', 0)

n_azar = conteos.get('Respondió siempre igual', 0)
p_azar = porcentajes.get('Respondió siempre igual', 0)

("### 📝 Reporte del diagnóstico general")

(
    f"""
Esta escala tuvo una participación de **{total_estudiantes} estudiantes**. 
De ellos, **{n_coincide} ({p_coincide:.1f}%)** muestran que el perfil CHASIDE 
**coincide con la carrera elegida**, por lo que constituyen el grupo mayormente alineado con su decisión vocacional.

Por otro lado, **{n_no_accorde} ({p_no_accorde:.1f}%)** presentan un perfil que **no va acorde con la carrera seleccionada**, 
lo que sugiere la necesidad de acompañamiento y orientación para prevenir dificultades de ajuste académico o vocacional.

Asimismo, **{n_sin_prioritario} ({p_sin_prioritario:.1f}%)** no muestran un **perfil prioritario claramente definido**, 
lo cual podría reflejar indecisión vocacional o un patrón de intereses y aptitudes todavía poco consolidado.

Finalmente, **{n_azar} ({p_azar:.1f}%)** fueron clasificados como **respondió siempre igual**, 
por lo que sus respuestas deben interpretarse con cautela al no ofrecer evidencia suficiente de un perfil vocacional confiable.
"""
)
# ============================================
# 📊 Distribución por carrera y categoría
# ============================================
st.header("📊 Distribución por carrera y categoría")

st.caption(
    "Se realizó un filtro por carrera para observar cómo respondieron los estudiantes "
    "de cada programa educativo respecto a su ajuste vocacional."
)

# Etiquetas largas para visualización
mapa_categorias_barras = {
    'Verde': 'El perfil coincide con la carrera elegida',
    'Amarillo': 'El perfil NO va acorde con la carrera elegida',
    'Sin sugerencia': 'No se observa un perfil prioritario',
    'Respondió siempre igual': 'Respondió siempre igual',
    'Rojo': 'No se observa un perfil prioritario'
}

# Copia de trabajo
df_barras = df.copy()
df_barras['Categoría_Barras'] = df_barras['Semáforo Vocacional'].replace(mapa_categorias_barras)

# Abreviar "Ingeniería" por "Ing."
df_barras['Carrera_Corta'] = (
    df_barras[columna_carrera]
    .astype(str)
    .str.replace('Ingeniería', 'Ing.', regex=False)
)

cats_order_largo = [
    'El perfil coincide con la carrera elegida',
    'El perfil NO va acorde con la carrera elegida',
    'No se observa un perfil prioritario',
    'Respondió siempre igual'
]

color_map_largo = {
    'El perfil coincide con la carrera elegida': '#22c55e',
    'El perfil NO va acorde con la carrera elegida': '#f59e0b',
    'No se observa un perfil prioritario': '#6b7280',
    'Respondió siempre igual': '#ef4444'
}

stacked = (
    df_barras[df_barras['Categoría_Barras'].isin(cats_order_largo)]
    .groupby(['Carrera_Corta', 'Categoría_Barras'], dropna=False)
    .size()
    .reset_index(name='N')
    .rename(columns={'Categoría_Barras': 'Categoría'})
)

stacked['Categoría'] = pd.Categorical(
    stacked['Categoría'],
    categories=cats_order_largo,
    ordered=True
)

modo = st.radio(
    "Modo de visualización",
    options=["Proporción (100% apilado)", "Valores absolutos"],
    horizontal=True,
    index=0,
    key="modo_barras_carrera"
)

if modo == "Proporción (100% apilado)":
    stacked['%'] = (
        stacked.groupby('Carrera_Corta')['N']
        .transform(lambda x: 0 if x.sum() == 0 else (x / x.sum() * 100))
    )

    fig_stacked = px.bar(
        stacked,
        x='Carrera_Corta',
        y='%',
        color='Categoría',
        category_orders={'Categoría': cats_order_largo},
        color_discrete_map=color_map_largo,
        barmode='stack',
        text=stacked['%'].round(1).astype(str) + '%',
        title="Proporción (%) de estudiantes por carrera y categoría"
    )

    fig_stacked.update_layout(
        yaxis_title="Proporción (%)",
        xaxis_title="Carrera",
        xaxis_tickangle=-30,
        height=680,
        legend_title_text="Categoría",
        legend=dict(
            orientation="h",
            y=-0.22,
            yanchor="top",
            x=0.5,
            xanchor="center"
        ),
        margin=dict(t=60, b=140)
    )
else:
    fig_stacked = px.bar(
        stacked,
        x='Carrera_Corta',
        y='N',
        color='Categoría',
        category_orders={'Categoría': cats_order_largo},
        color_discrete_map=color_map_largo,
        barmode='stack',
        text='N',
        title="Estudiantes por carrera y categoría (valores absolutos)"
    )

    fig_stacked.update_layout(
        yaxis_title="Número de estudiantes",
        xaxis_title="Carrera",
        xaxis_tickangle=-30,
        height=680,
        legend_title_text="Categoría",
        legend=dict(
            orientation="h",
            y=-0.22,
            yanchor="top",
            x=0.5,
            xanchor="center"
        ),
        margin=dict(t=60, b=140)
    )

    fig_stacked.update_traces(textposition='inside', cliponaxis=False)

st.plotly_chart(fig_stacked, use_container_width=True)

# ============================================
# 📝 REPORTE AUTOMÁTICO DEL SUBMÓDULO
# ============================================
("### 📝 Reporte por carrera")

# Tabla base por carrera con categorías ya unificadas
resumen_carreras = (
    df_barras.groupby(['Carrera_Corta', 'Categoría_Barras'])
    .size()
    .unstack(fill_value=0)
)

# Asegurar columnas
for c in cats_order_largo:
    if c not in resumen_carreras.columns:
        resumen_carreras[c] = 0

resumen_carreras = resumen_carreras[cats_order_largo].copy()
resumen_carreras['Total'] = resumen_carreras.sum(axis=1)

# Porcentajes
for c in cats_order_largo:
    resumen_carreras[f'%_{c}'] = np.where(
        resumen_carreras['Total'] == 0,
        0,
        resumen_carreras[c] / resumen_carreras['Total'] * 100
    )

# Top 2 verde
top_verde = resumen_carreras.sort_values(
    by='El perfil coincide con la carrera elegida',
    ascending=False
).head(2)

# Top 2 amarillo
top_amarillo = resumen_carreras.sort_values(
    by='El perfil NO va acorde con la carrera elegida',
    ascending=False
).head(2)

# Top 2 rojo/no prioritario
top_rojo = resumen_carreras.sort_values(
    by='No se observa un perfil prioritario',
    ascending=False
).head(2)

st.markdown("**Carreras con mayor proporción de ajuste vocacional (verde):**")
for carrera, row in top_verde.iterrows():
    st.markdown(
        f"- **{carrera}**: {int(row['El perfil coincide con la carrera elegida'])} estudiantes "
        f"({row['%_El perfil coincide con la carrera elegida']:.1f}%) con perfil acorde a la carrera elegida."
    )

st.markdown("**Carreras con mayor proporción de perfil no acorde (amarillo):**")
for carrera, row in top_amarillo.iterrows():
    st.markdown(
        f"- **{carrera}**: {int(row['El perfil NO va acorde con la carrera elegida'])} estudiantes "
        f"({row['%_El perfil NO va acorde con la carrera elegida']:.1f}%) cuyo perfil no va acorde con la carrera elegida."
    )

st.markdown("**Carreras con mayor proporción de perfil no prioritario (rojo/sin sugerencia):**")
for carrera, row in top_rojo.iterrows():
    st.markdown(
        f"- **{carrera}**: {int(row['No se observa un perfil prioritario'])} estudiantes "
        f"({row['%_No se observa un perfil prioritario']:.1f}%) sin un perfil prioritario claramente definido."
    )
# ============================================
# 📊 Intensidad del perfil vocacional por carrera
# ============================================
st.header("📊 Intensidad del perfil vocacional por carrera")

st.caption(
    "Se construyeron dos distribuciones conceptuales: la primera corresponde a los estudiantes "
    "cuyo perfil vocacional coincide con su elección de carrera (niveles verde fuerte y medio fuerte), "
    "y la segunda agrupa a aquellos estudiantes cuya elección de carrera no coincide con su perfil vocacional. "
    "Esto permite visualizar la intensidad del ajuste vocacional dentro de cada programa educativo."
)

df_intensidad = df.copy()
df_intensidad['Score'] = df_intensidad[[f'PUNTAJE_COMBINADO_{a}' for a in areas]].max(axis=1)

# Abreviar carreras
df_intensidad['Carrera_Corta'] = (
    df_intensidad[columna_carrera]
    .astype(str)
    .str.replace('Ingeniería', 'Ing.', regex=False)
)

# Solo Verde y Amarillo
df_intensidad = df_intensidad[
    df_intensidad['Semáforo Vocacional'].isin(['Verde', 'Amarillo'])
].copy()

if df_intensidad.empty:
    st.info("No hay estudiantes en categorías Verde o Amarillo para construir la barra de intensidad.")
else:
    def asignar_niveles_por_carrera(grupo):
        grupo = grupo.copy()
        grupo['Nivel_Intensidad'] = np.nan

        amar = grupo[grupo['Semáforo Vocacional'] == 'Amarillo'].copy()
        ver = grupo[grupo['Semáforo Vocacional'] == 'Verde'].copy()

        # Amarillo → 2 niveles
        if len(amar) > 0:
            amar = amar.sort_values('Score', ascending=True).copy()
            amar['rank_pct'] = (np.arange(len(amar)) + 1) / len(amar)

            amar['Nivel_Intensidad'] = np.where(
                amar['rank_pct'] <= 0.25,
                'Sin perfil',
                'Perfil en riesgo'
            )
            grupo.loc[amar.index, 'Nivel_Intensidad'] = amar['Nivel_Intensidad']

        # Verde → 2 niveles
        if len(ver) > 0:
            ver = ver.sort_values('Score', ascending=True).copy()
            ver['rank_pct'] = (np.arange(len(ver)) + 1) / len(ver)

            ver['Nivel_Intensidad'] = np.where(
                ver['rank_pct'] > 0.75,
                'Jóven promesa',
                'Perfil en transición'
            )
            grupo.loc[ver.index, 'Nivel_Intensidad'] = ver['Nivel_Intensidad']

        return grupo

    df_intensidad = (
        df_intensidad
        .groupby('Carrera_Corta', group_keys=False)
        .apply(asignar_niveles_por_carrera)
        .copy()
    )

    orden_niveles = [
        'Sin perfil',
        'Perfil en riesgo',
        'Perfil en transición',
        'Jóven promesa'
    ]

    colores_niveles = {
        'Sin perfil': '#dc2626',
        'Perfil en riesgo': '#f59e0b',
        'Perfil en transición': '#84cc16',
        'Jóven promesa': '#16a34a'
    }

    resumen_intensidad = (
        df_intensidad
        .groupby(['Carrera_Corta', 'Nivel_Intensidad'], dropna=False)
        .agg(
            N=(columna_nombre, 'count'),
            Estudiantes=(columna_nombre, lambda x: "<br>".join(sorted(x.astype(str).tolist())))
        )
        .reset_index()
    )

    resumen_intensidad['Nivel_Intensidad'] = pd.Categorical(
        resumen_intensidad['Nivel_Intensidad'],
        categories=orden_niveles,
        ordered=True
    )

    resumen_intensidad = resumen_intensidad.sort_values(
        ['Carrera_Corta', 'Nivel_Intensidad']
    )

    resumen_intensidad['%'] = (
        resumen_intensidad.groupby('Carrera_Corta')['N']
        .transform(lambda x: 0 if x.sum() == 0 else (x / x.sum() * 100))
    )

    fig_intensidad = px.bar(
        resumen_intensidad,
        x='Carrera_Corta',
        y='%',
        color='Nivel_Intensidad',
        category_orders={'Nivel_Intensidad': orden_niveles},
        color_discrete_map=colores_niveles,
        barmode='stack',
        text=resumen_intensidad['%'].round(1).astype(str) + '%',
        title="Escala de intensidad vocacional por carrera"
    )

    fig_intensidad.update_layout(
        yaxis_title="Proporción (%)",
        xaxis_title="Carrera",
        xaxis_tickangle=-30,
        height=720,
        legend_title_text="Nivel",
        legend=dict(
            orientation="h",
            y=-0.25,
            yanchor="top",
            x=0.5,
            xanchor="center"
        ),
        margin=dict(t=60, b=150)
    )

    fig_intensidad.update_traces(
        customdata=np.stack(
            [
                resumen_intensidad['Nivel_Intensidad'],
                resumen_intensidad['N'],
                resumen_intensidad['Estudiantes']
            ],
            axis=-1
        ),
        hovertemplate=(
            "<b>Carrera:</b> %{x}<br>"
            "<b>Nivel:</b> %{customdata[0]}<br>"
            "<b>Porcentaje:</b> %{y:.1f}%<br>"
            "<b>Número de estudiantes:</b> %{customdata[1]}<br>"
            "<b>Estudiantes:</b><br>%{customdata[2]}"
            "<extra></extra>"
        )
    )

    st.plotly_chart(fig_intensidad, use_container_width=True)

    # Interpretación
    st.markdown("### Lectura sugerida de la escala")
st.markdown("""
- **Sin perfil**: estudiantes cuya elección de carrera no muestra correspondencia con su perfil vocacional. 
Se recomienda una reevaluación vocacional y posible cambio de carrera.

- **Perfil en riesgo**: estudiantes cuyo perfil vocacional presenta una coincidencia mínima con la carrera elegida. 
Es probable que logren acreditar asignaturas de Ciencias Básicas; sin embargo, existe un alto riesgo de dificultades 
en asignaturas específicas de la carrera.

- **Perfil en transición**: estudiantes cuya elección profesional y perfil vocacional presentan congruencia, 
aunque aún en proceso de consolidación. Se espera un bajo nivel de no acreditación en Ciencias Básicas.

- **Jóven promesa**: estudiantes con una alta congruencia entre su perfil vocacional y la carrera elegida, 
lo que favorece un desempeño académico sólido y sostenido.
""")
# ============================================
# 🌊 Sankey vocacional por carrera
#    Carrera elegida vs carrera con mejor ajuste compatible
# ============================================
st.header("🌊 Transición vocacional compatible por carrera")

st.caption(
    "Seleccione una carrera para analizar si sus estudiantes presentan mejor ajuste "
    "hacia otra carrera con perfil CHASIDE compatible. "
    "Solo se consideran transiciones razonables entre carreras con al menos dos letras CHASIDE en común."
)

# --------------------------------------------
# Base para Sankey
# --------------------------------------------
df_sankey = df.copy()

# Excluir respuestas poco confiables
df_sankey = df_sankey[
    ~df_sankey['Semáforo Vocacional'].isin(['Respondió siempre igual'])
].copy()

df_sankey[columna_carrera] = df_sankey[columna_carrera].astype(str).str.strip()

# --------------------------------------------
# Funciones auxiliares
# --------------------------------------------
def letras_carrera(carrera):
    perfil = perfil_carreras.get(str(carrera).strip(), {})
    return perfil.get('Fuerte', [])

def puntaje_promedio_carrera(row, carrera):
    letras = letras_carrera(carrera)
    if not letras:
        return np.nan
    vals = [row[f'PUNTAJE_COMBINADO_{l}'] for l in letras]
    return np.mean(vals)

def carreras_compatibles(carrera_origen):
    letras_origen = set(letras_carrera(carrera_origen))
    compatibles = []

    for carrera_destino in perfil_carreras.keys():
        if carrera_destino == carrera_origen:
            continue
        letras_destino = set(letras_carrera(carrera_destino))
        inter = letras_origen.intersection(letras_destino)

        # Compatibilidad mínima: al menos 2 letras en común
        if len(inter) >= 2:
            compatibles.append(carrera_destino)

    return compatibles

def mejor_destino_compatible(row, carrera_origen):
    """
    Devuelve la mejor carrera compatible para el estudiante.
    Si ninguna mejora el ajuste respecto a la carrera elegida, se queda en la misma.
    """
    score_origen = puntaje_promedio_carrera(row, carrera_origen)
    candidatas = carreras_compatibles(carrera_origen)

    mejor_carrera = carrera_origen
    mejor_score = score_origen

    for c in candidatas:
        score_c = puntaje_promedio_carrera(row, c)
        if pd.notna(score_c) and score_c > mejor_score:
            mejor_score = score_c
            mejor_carrera = c

    return mejor_carrera, score_origen, mejor_score

# --------------------------------------------
# Selector de carrera
# --------------------------------------------
carreras_disp = sorted(df_sankey[columna_carrera].dropna().unique())

if not carreras_disp:
    st.info("No hay carreras disponibles para construir el Sankey.")
else:
    carrera_sel = st.selectbox("Seleccione la carrera de origen:", carreras_disp)

    sub = df_sankey[df_sankey[columna_carrera] == carrera_sel].copy()

    if sub.empty:
        st.warning("No hay estudiantes para esta carrera.")
    else:
        # --------------------------------------------
        # Calcular destino compatible estudiante por estudiante
        # --------------------------------------------
        destinos = []
        score_origen_list = []
        score_destino_list = []

        for _, row in sub.iterrows():
            destino, score_origen, score_destino = mejor_destino_compatible(row, carrera_sel)
            destinos.append(destino)
            score_origen_list.append(score_origen)
            score_destino_list.append(score_destino)

        sub['Destino_Compatible'] = destinos
        sub['Score_Origen'] = score_origen_list
        sub['Score_Destino'] = score_destino_list
        sub['Migra'] = sub['Destino_Compatible'] != carrera_sel

        # --------------------------------------------
        # Conteos por destino
        # --------------------------------------------
        flujos = (
            sub.groupby('Destino_Compatible')
            .size()
            .reset_index(name='N')
            .sort_values('N', ascending=False)
        )

        n_total = len(sub)
        n_se_quedan = int((sub['Destino_Compatible'] == carrera_sel).sum())
        n_migran = int((sub['Destino_Compatible'] != carrera_sel).sum())

        # --------------------------------------------
        # Etiquetas de nodos
        # --------------------------------------------
        letras_origen_txt = ", ".join(letras_carrera(carrera_sel))
        label_origen = [f"{carrera_sel}<br>Perfil esperado: {letras_origen_txt}<br>Total: {n_total}"]

        label_destinos = []
        for _, row in flujos.iterrows():
            c = row['Destino_Compatible']
            letras_dest = ", ".join(letras_carrera(c))
            label_destinos.append(f"{c}<br>Perfil: {letras_dest}<br>Final: {row['N']}")

        labels = label_origen + label_destinos

        # Índices
        source = [0] * len(flujos)
        target = list(range(1, len(flujos) + 1))
        value = flujos['N'].tolist()

        # --------------------------------------------
        # Colores
        # --------------------------------------------
        palette = px.colors.qualitative.Bold + px.colors.qualitative.Dark24
        destinos_unicos = flujos['Destino_Compatible'].tolist()

        color_map_destino = {
            carrera: palette[i % len(palette)]
            for i, carrera in enumerate(destinos_unicos)
        }

        # La misma carrera en verde
        color_map_destino[carrera_sel] = '#22c55e'

        node_colors = ['#60a5fa'] + [color_map_destino[d] for d in flujos['Destino_Compatible']]
        link_colors = [color_map_destino[d] for d in flujos['Destino_Compatible']]

        porcentajes = (flujos['N'] / n_total * 100).round(1)

        customdata = np.stack(
            [
                [carrera_sel] * len(flujos),
                flujos['Destino_Compatible'],
                flujos['N'],
                porcentajes
            ],
            axis=-1
        )

        # --------------------------------------------
        # Figura Sankey
        # --------------------------------------------
        fig_sankey = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                pad=20,
                thickness=24,
                line=dict(color="black", width=0.3),
                label=labels,
                color=node_colors,
                hoverlabel=dict(font=dict(color="black", size=13))
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color=link_colors,
                customdata=customdata,
                hovertemplate=(
                    "Carrera elegida: %{customdata[0]}<br>"
                    "Carrera sugerida compatible: %{customdata[1]}<br>"
                    "Estudiantes: %{customdata[2]}<br>"
                    "Porcentaje del total: %{customdata[3]}%<extra></extra>"
                )
            )
        )])

        fig_sankey.update_layout(
            title=f"Transición vocacional compatible desde {carrera_sel}",
            font=dict(size=14, color="black", family="Arial"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=760
        )

        st.plotly_chart(fig_sankey, use_container_width=True)

        # --------------------------------------------
        # KPIs
        # --------------------------------------------
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total evaluado", n_total)
        with c2:
            st.metric("Se mantienen", f"{n_se_quedan} ({n_se_quedan / n_total * 100:.1f}%)")
        with c3:
            st.metric("Migrarían", f"{n_migran} ({n_migran / n_total * 100:.1f}%)")

        # --------------------------------------------
        # Resumen numérico
        # --------------------------------------------
        st.markdown("### Resumen numérico")
        for _, row in flujos.iterrows():
            pct = row['N'] / n_total * 100 if n_total else 0
            st.markdown(
                f"- **{carrera_sel} → {row['Destino_Compatible']}**: "
                f"{row['N']} estudiantes ({pct:.1f}%)"
            )

        # --------------------------------------------
        # Tabla de apoyo
        # --------------------------------------------
        st.markdown("### Detalle de estudiantes")
        st.dataframe(
            sub[[columna_nombre, columna_carrera, 'Destino_Compatible', 'Score_Origen', 'Score_Destino', 'Migra']]
            .sort_values(['Migra', 'Score_Destino'], ascending=[False, False]),
            use_container_width=True
        )

# ============================================
# 📊 Prioridades CHASIDE: histograma + Pareto fusionados
#    Perfil en riesgo vs Jóven promesa
# ============================================
st.header("📊 Prioridades CHASIDE por carrera")

st.caption(
    "Seleccione una carrera para comparar el promedio del grupo 'Perfil en riesgo' "
    "contra el promedio del grupo 'Jóven promesa'. "
    "Las barras muestran el error porcentual por letra CHASIDE y la línea acumulada permite "
    "identificar las áreas prioritarias bajo el criterio 80–20."
)

if 'df_intensidad' not in locals():
    st.warning("No se encontró la base de intensidad. Asegúrate de haber generado previamente 'df_intensidad'.")
else:
    df_pareto = df.copy()

    # Totales CHASIDE por letra
    for a in areas:
        df_pareto[a] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

    # Vincular niveles de intensidad
    df_pareto = df_pareto.loc[df_intensidad.index].copy()
    df_pareto['Nivel_Intensidad'] = df_intensidad['Nivel_Intensidad'].values
    df_pareto['Carrera'] = df.loc[df_pareto.index, columna_carrera].values

    # Abreviar Ingeniería -> Ing.
    df_pareto['Carrera_Corta'] = (
        df_pareto['Carrera']
        .astype(str)
        .str.replace('Ingeniería', 'Ing.', regex=False)
    )

    areas_long = {
        "C": "Administrativo",
        "H": "Humanidades y Sociales",
        "A": "Artístico",
        "S": "Ciencias de la Salud",
        "I": "Enseñanzas Técnicas",
        "D": "Defensa y Seguridad",
        "E": "Ciencias Experimentales"
    }

    carreras_disp = sorted(df_pareto['Carrera_Corta'].dropna().unique())
    carrera_sel_corta = st.selectbox("Seleccione una carrera:", carreras_disp, key="select_pareto_fusion")

    sub = df_pareto[df_pareto['Carrera_Corta'] == carrera_sel_corta].copy()

    riesgo = sub[sub['Nivel_Intensidad'] == 'Perfil en riesgo'].copy()
    promesa = sub[sub['Nivel_Intensidad'] == 'Jóven promesa'].copy()

    if riesgo.empty or promesa.empty:
        st.warning(
            "No hay suficientes estudiantes en 'Perfil en riesgo' y 'Jóven promesa' para esta carrera."
        )
    else:
        prom_riesgo = riesgo[areas].mean()
        prom_promesa = promesa[areas].mean()

        resultados = []
        for a in areas:
            meta = prom_promesa[a]
            medido = prom_riesgo[a]

            if meta == 0:
                error_pct = 0.0
            else:
                error_pct = ((meta - medido) / meta) * 100

            # Solo nos interesa déficit real
            error_pct = max(error_pct, 0.0)

            resultados.append({
                'Letra': a,
                'Área': areas_long[a],
                'Meta': float(meta),
                'Medido': float(medido),
                'Error_Porcentual': float(error_pct)
            })

        df_plot = pd.DataFrame(resultados).sort_values('Error_Porcentual', ascending=False).reset_index(drop=True)

        total_error = df_plot['Error_Porcentual'].sum()
        if total_error == 0:
            df_plot['Porcentaje_Relativo'] = 0.0
            df_plot['Acumulado'] = 0.0
        else:
            df_plot['Porcentaje_Relativo'] = df_plot['Error_Porcentual'] / total_error * 100
            df_plot['Acumulado'] = df_plot['Porcentaje_Relativo'].cumsum()

        # Marcar letras críticas hasta cubrir 80%
        df_plot['Dentro_80'] = False
        acumulado_tmp = 0.0
        for idx in df_plot.index:
            if acumulado_tmp < 80:
                df_plot.at[idx, 'Dentro_80'] = True
                acumulado_tmp = df_plot.at[idx, 'Acumulado']

        # Si no hubo error en ninguna letra
        if total_error == 0:
            df_plot['Dentro_80'] = False

        # Figura fusionada
        fig_pareto = go.Figure()

        fig_pareto.add_bar(
            x=df_plot['Letra'],
            y=df_plot['Error_Porcentual'],
            name='Error porcentual',
            marker_color=[
                '#dc2626' if dentro else '#94a3b8'
                for dentro in df_plot['Dentro_80']
            ],
            customdata=np.stack(
                [
                    df_plot['Área'],
                    df_plot['Meta'],
                    df_plot['Medido'],
                    df_plot['Porcentaje_Relativo'],
                    df_plot['Acumulado']
                ],
                axis=-1
            ),
            hovertemplate=(
                "<b>Letra:</b> %{x}<br>"
                "<b>Área:</b> %{customdata[0]}<br>"
                "<b>Valor meta (Jóven promesa):</b> %{customdata[1]:.2f}<br>"
                "<b>Valor medido (Perfil en riesgo):</b> %{customdata[2]:.2f}<br>"
                "<b>Error porcentual:</b> %{y:.2f}%<br>"
                "<b>Peso relativo:</b> %{customdata[3]:.2f}%<br>"
                "<b>Acumulado:</b> %{customdata[4]:.2f}%<extra></extra>"
            )
        )

        fig_pareto.add_scatter(
            x=df_plot['Letra'],
            y=df_plot['Acumulado'],
            name='Acumulado',
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='#16a34a', width=3),
            marker=dict(size=8)
        )

        fig_pareto.add_hline(
            y=80,
            line_dash='dash',
            line_color='orange',
            yref='y2'
        )

        fig_pareto.update_layout(
            title=f"Pareto de prioridades CHASIDE – {carrera_sel_corta}",
            xaxis_title="Letra CHASIDE",
            yaxis_title="Error porcentual (%)",
            yaxis2=dict(
                title="Porcentaje acumulado (%)",
                overlaying='y',
                side='right',
                range=[0, 110]
            ),
            legend=dict(
                orientation='h',
                y=1.08,
                x=0
            ),
            height=650
        )

        st.plotly_chart(fig_pareto, use_container_width=True)

        # --------------------------------------------
        # Resumen ejecutivo 80-20
        # --------------------------------------------
        st.markdown("### 📝 Resumen ejecutivo de prioridades")

        if total_error == 0:
            st.success(
                "No se observaron brechas entre 'Perfil en riesgo' y 'Jóven promesa' en esta carrera. "
                "Por tanto, no se identifican áreas CHASIDE prioritarias de intervención bajo este criterio."
            )
        else:
            criticas = df_plot[df_plot['Dentro_80']].copy()

            letras_criticas = criticas['Letra'].tolist()
            areas_criticas = criticas['Área'].tolist()
            acumulado_final = criticas['Acumulado'].iloc[-1] if not criticas.empty else 0

            st.markdown(
                f"En **{carrera_sel_corta}**, las letras CHASIDE que concentran aproximadamente el "
                f"**80% de la brecha acumulada** son: **{', '.join(letras_criticas)}**."
            )

            st.markdown(
                f"Estas áreas explican en conjunto **{acumulado_final:.1f}%** del problema detectado "
                f"entre el grupo **Perfil en riesgo** y el grupo **Jóven promesa**."
            )

            st.markdown("**Áreas prioritarias de intervención:**")
            for _, row in criticas.iterrows():
                st.markdown(
                    f"- **{row['Letra']} ({row['Área']})**: "
                    f"error porcentual de **{row['Error_Porcentual']:.2f}%**, "
                    f"peso relativo de **{row['Porcentaje_Relativo']:.2f}%**."
                )

        # Tabla de apoyo
        st.markdown("### Resumen numérico")
        st.dataframe(
            df_plot[['Letra', 'Área', 'Meta', 'Medido', 'Error_Porcentual', 'Porcentaje_Relativo', 'Acumulado', 'Dentro_80']],
            use_container_width=True
        )
