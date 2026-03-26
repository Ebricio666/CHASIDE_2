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
# 📌 DIAGRAMA DE PASTEL
# ============================================
st.subheader("🥧 Diagnóstico general (Pastel)")

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
# 📊 Barras apiladas por carrera
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
# 📊 Barra vertical de intensidad – 4 niveles
# ============================================
st.header("📊 Intensidad del perfil vocacional por carrera")

st.caption(
    "La barra apilada ordena a los estudiantes desde los niveles más alejados del perfil esperado "
    "hasta los de mayor congruencia vocacional. El gradiente rojo→verde facilita identificar "
    "riesgo vocacional y potencial de ajuste al perfil."
)

df_intensidad = df.copy()
df_intensidad['Score'] = df_intensidad[[f'PUNTAJE_COMBINADO_{a}' for a in areas]].max(axis=1)
df_intensidad = df_intensidad[df_intensidad['Semáforo Vocacional'].isin(['Verde', 'Amarillo'])].copy()

if df_intensidad.empty:
    st.info("No hay estudiantes en categorías Verde o Amarillo para construir la barra de intensidad.")
else:
    def asignar_niveles_por_carrera(grupo):
        grupo = grupo.copy()
        grupo['Nivel_Intensidad'] = np.nan

        amar = grupo[grupo['Semáforo Vocacional'] == 'Amarillo'].copy()
        ver = grupo[grupo['Semáforo Vocacional'] == 'Verde'].copy()

        if len(amar) > 0:
            amar = amar.sort_values('Score', ascending=True).copy()
            amar['rank_pct'] = (np.arange(len(amar)) + 1) / len(amar)
            amar['Nivel_Intensidad'] = np.where(
                amar['rank_pct'] <= 0.25,
                'Sin perfil',
                'Perfil en riesgo'
            )
            grupo.loc[amar.index, 'Nivel_Intensidad'] = amar['Nivel_Intensidad']

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
        .groupby(columna_carrera, group_keys=False)
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
        .groupby([columna_carrera, 'Nivel_Intensidad'], dropna=False)
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

    resumen_intensidad = resumen_intensidad.sort_values([columna_carrera, 'Nivel_Intensidad'])

    resumen_intensidad['%'] = (
        resumen_intensidad.groupby(columna_carrera)['N']
        .transform(lambda x: 0 if x.sum() == 0 else (x / x.sum() * 100))
    )

    fig_intensidad = px.bar(
        resumen_intensidad,
        x=columna_carrera,
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
        legend_title_text="Nivel"
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

# ============================================
# 🌊 Sankey global: migración hacia Arquitectura
# ============================================
st.header("🌊 Migración potencial hacia Arquitectura")

st.caption(
    "El diagrama muestra, para todas las carreras, cuántos estudiantes eligieron una carrera "
    "distinta pero su perfil CHASIDE sugiere Arquitectura como mejor ajuste. "
    "Solo se consideran estudiantes con carrera sugerida única."
)

df_sankey = df.copy()
df_sankey = df_sankey[
    ~df_sankey['Carrera_Mejor_Perfilada'].isin([
        'Información no confiable',
        'Sin sugerencia clara'
    ])
].copy()

df_sankey[columna_carrera] = df_sankey[columna_carrera].astype(str).str.strip()
df_sankey['Carrera_Mejor_Perfilada'] = df_sankey['Carrera_Mejor_Perfilada'].astype(str).str.strip()

df_sankey = df_sankey[
    ~df_sankey['Carrera_Mejor_Perfilada'].str.contains(',', regex=False)
].copy()

df_sankey = df_sankey[
    (df_sankey['Carrera_Mejor_Perfilada'] == 'Arquitectura') &
    (df_sankey[columna_carrera] != 'Arquitectura')
].copy()

if df_sankey.empty:
    st.info("No se encontraron estudiantes que migren hacia Arquitectura bajo este criterio.")
else:
    flujos = (
        df_sankey
        .groupby(columna_carrera)
        .size()
        .reset_index(name='N')
        .sort_values('N', ascending=False)
    )

    total_migran = flujos['N'].sum()
    carreras_origen = flujos[columna_carrera].tolist()

    labels_origen = [
        f"{carrera}<br>Origen: {n}"
        for carrera, n in zip(flujos[columna_carrera], flujos['N'])
    ]
    label_destino = [f"Arquitectura<br>Recibe: {total_migran}"]
    labels = labels_origen + label_destino

    source = list(range(len(carreras_origen)))
    target = [len(carreras_origen)] * len(carreras_origen)
    value = flujos['N'].tolist()

    palette = px.colors.qualitative.Bold + px.colors.qualitative.Dark24
    color_map_origen = {
        carrera: palette[i % len(palette)]
        for i, carrera in enumerate(carreras_origen)
    }

    node_colors = [color_map_origen[c] for c in carreras_origen] + ['#22c55e']
    link_colors = [color_map_origen[c] for c in carreras_origen]

    porcentajes = (flujos['N'] / total_migran * 100).round(1)
    customdata = np.stack(
        [
            flujos[columna_carrera],
            ['Arquitectura'] * len(flujos),
            flujos['N'],
            porcentajes
        ],
        axis=-1
    )

    fig_sankey = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=22,
            line=dict(color="black", width=0.3),
            label=labels,
            color=node_colors,
            hoverlabel=dict(
                font=dict(color="black", size=13)
            )
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=link_colors,
            customdata=customdata,
            hovertemplate=(
                "Carrera elegida: %{customdata[0]}<br>"
                "Carrera sugerida: %{customdata[1]}<br>"
                "Estudiantes: %{customdata[2]}<br>"
                "Porcentaje del total: %{customdata[3]}%<extra></extra>"
            )
        )
    )])

    fig_sankey.update_layout(
        title="Migración potencial de todas las carreras hacia Arquitectura",
        font=dict(size=14, color="black", family="Arial"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=750
    )

    st.plotly_chart(fig_sankey, use_container_width=True)

# ============================================
# 📊 PRUEBA FINAL: error porcentual por letra CHASIDE
#    Perfil en riesgo vs Jóvenes promesa
# ============================================
st.header("📊 Error porcentual por letra CHASIDE")

st.caption(
    "Seleccione una carrera para comparar el promedio del grupo 'Perfil en riesgo' "
    "contra el promedio del grupo 'Jóven promesa'. "
    "El error porcentual indica qué letras CHASIDE requieren mayor fomento."
)

if 'df_intensidad' not in locals():
    st.warning("No se encontró la base de intensidad. Asegúrate de haber generado previamente 'df_intensidad'.")
else:
    df_error = df.copy()

    for a in areas:
        df_error[a] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

    # Alinear índices y niveles
    df_error = df_error.loc[df_intensidad.index].copy()
    df_error['Nivel_Intensidad'] = df_intensidad['Nivel_Intensidad'].values
    df_error['Carrera'] = df.loc[df_error.index, columna_carrera].values

    carreras_disp = sorted(df_error['Carrera'].dropna().unique())
    carrera_sel = st.selectbox("Seleccione una carrera:", carreras_disp, key="select_error_chaside")

    sub = df_error[df_error['Carrera'] == carrera_sel].copy()

    riesgo = sub[sub['Nivel_Intensidad'] == 'Perfil en riesgo'].copy()
    promesa = sub[sub['Nivel_Intensidad'] == 'Jóven promesa'].copy()

    if riesgo.empty or promesa.empty:
        st.warning(
            "No hay suficientes estudiantes en 'Perfil en riesgo' y 'Jóven promesa' "
            "para esta carrera."
        )
    else:
        prom_riesgo = riesgo[areas].mean()
        prom_promesa = promesa[areas].mean()

        resultados = []
        for a in areas:
            meta = prom_promesa[a]
            medido = prom_riesgo[a]

            if meta == 0:
                error_pct = 0
            else:
                error_pct = ((meta - medido) / meta) * 100

            error_pct = max(error_pct, 0)

            resultados.append({
                'Letra': a,
                'Meta': meta,
                'Medido': medido,
                'Error_Porcentual': error_pct
            })

        df_plot = pd.DataFrame(resultados).sort_values('Error_Porcentual', ascending=False)

        areas_long = {
            "C": "Administrativo",
            "H": "Humanidades y Sociales",
            "A": "Artístico",
            "S": "Ciencias de la Salud",
            "I": "Enseñanzas Técnicas",
            "D": "Defensa y Seguridad",
            "E": "Ciencias Experimentales"
        }

        df_plot['Área'] = df_plot['Letra'].map(areas_long)

        fig_error = px.bar(
            df_plot,
            x='Letra',
            y='Error_Porcentual',
            color='Letra',
            text=df_plot['Error_Porcentual'].round(1).astype(str) + '%',
            title=f"Error porcentual por letra CHASIDE – {carrera_sel}"
        )

        fig_error.update_layout(
            xaxis_title="Letra CHASIDE",
            yaxis_title="Error porcentual (%)",
            showlegend=False,
            height=620
        )

        fig_error.update_traces(
            hovertemplate=(
                "<b>Letra:</b> %{x}<br>"
                "<b>Área:</b> %{customdata[0]}<br>"
                "<b>Valor meta (jóvenes promesa):</b> %{customdata[1]:.2f}<br>"
                "<b>Valor medido (perfil en riesgo):</b> %{customdata[2]:.2f}<br>"
                "<b>Error porcentual:</b> %{y:.2f}%<extra></extra>"
            ),
            customdata=np.stack(
                [
                    df_plot['Área'],
                    df_plot['Meta'],
                    df_plot['Medido']
                ],
                axis=-1
            )
        )

        st.plotly_chart(fig_error, use_container_width=True)

        st.markdown("### Resumen numérico")
        st.dataframe(
            df_plot[['Letra', 'Área', 'Meta', 'Medido', 'Error_Porcentual']],
            use_container_width=True
        )

        top3 = df_plot.head(3)

        st.markdown("### Áreas prioritarias por atender")
        for _, row in top3.iterrows():
            st.markdown(
                f"- **{row['Letra']} ({row['Área']})**: error porcentual de **{row['Error_Porcentual']:.2f}%**"
            )
