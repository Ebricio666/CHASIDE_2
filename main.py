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

# Solo Verde y Amarillo
df_intensidad = df_intensidad[df_intensidad['Semáforo Vocacional'].isin(['Verde', 'Amarillo'])].copy()

if df_intensidad.empty:
    st.info("No hay estudiantes en categorías Verde o Amarillo para construir la barra de intensidad.")
else:
    def asignar_niveles_por_carrera(grupo):
        grupo = grupo.copy()
        grupo['Nivel_Intensidad'] = np.nan

        amar = grupo[grupo['Semáforo Vocacional'] == 'Amarillo'].copy()
        ver = grupo[grupo['Semáforo Vocacional'] == 'Verde'].copy()

        # -------------------------
        # Amarillo → 2 niveles
        # -------------------------
        if len(amar) > 0:
            amar = amar.sort_values('Score', ascending=True).copy()
            amar['rank_pct'] = (np.arange(len(amar)) + 1) / len(amar)

            amar['Nivel_Intensidad'] = np.where(
                amar['rank_pct'] <= 0.25,
                'Sin perfil',
                'Perfil en riesgo'
            )
            grupo.loc[amar.index, 'Nivel_Intensidad'] = amar['Nivel_Intensidad']

        # -------------------------
        # Verde → 2 niveles
        # -------------------------
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
        'Sin perfil': '#dc2626',             # rojo
        'Perfil en riesgo': '#f59e0b',       # amarillo/naranja
        'Perfil en transición': '#84cc16',   # verde amarillento
        'Jóven promesa': '#16a34a'           # verde fuerte
    }

    # Resumen por carrera y nivel
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

    st.markdown("### Lectura sugerida de la escala")
    st.markdown("""
- **Sin perfil**: estudiantes con el nivel más bajo dentro del grupo amarillo.  
- **Perfil en riesgo**: estudiantes cuyo perfil no va acorde con la carrera elegida, aunque con mejor puntaje relativo que el nivel anterior.  
- **Perfil en transición**: estudiantes que sí muestran congruencia con la carrera, pero aún sin ubicarse en los niveles más altos del grupo verde.  
- **Jóven promesa**: estudiantes en el cuartil superior del grupo verde, con el mejor ajuste vocacional relativo dentro de su carrera.  
""")
# ============================================
# 📊 Barras CHASIDE por área (Verde vs Amarillo)
# ============================================
st.header("📊 Áreas prioritarias CHASIDE (Verde vs Amarillo)")

st.caption(
    "Comparación del perfil promedio entre estudiantes cuyo perfil coincide con la carrera (Verde) "
    "y aquellos cuyo perfil no es acorde (Amarillo). "
    "Las áreas se ordenan por brecha, facilitando la identificación de prioridades de intervención."
)

# --------------------------------------------
# Preparar datos
# --------------------------------------------
df_bar = df.copy()

for a in areas:
    df_bar[a] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

df_bar = df_bar[df_bar['Semáforo Vocacional'].isin(['Verde', 'Amarillo'])].copy()

if df_bar.empty:
    st.info("No hay datos suficientes de Verde y Amarillo.")
else:

    carreras_disp = sorted(df_bar[columna_carrera].dropna().unique())
    carrera_sel = st.selectbox("Selecciona una carrera:", carreras_disp)

    sub = df_bar[df_bar[columna_carrera] == carrera_sel]

    if sub.empty or sub['Semáforo Vocacional'].nunique() < 2:
        st.warning("No hay suficientes datos para comparar en esta carrera.")
    else:

        # --------------------------------------------
        # Promedios por grupo
        # --------------------------------------------
        prom = sub.groupby('Semáforo Vocacional')[areas].mean()

        # --------------------------------------------
        # Calcular brecha (Verde - Amarillo)
        # --------------------------------------------
        brechas = (prom.loc['Verde'] - prom.loc['Amarillo']).sort_values(ascending=False)

        # --------------------------------------------
        # DataFrame para gráfico
        # --------------------------------------------
        df_plot = pd.DataFrame({
            'Área': brechas.index,
            'Verde': prom.loc['Verde'][brechas.index],
            'Amarillo': prom.loc['Amarillo'][brechas.index],
            'Brecha': brechas.values
        })

        # nombres largos
        areas_long = {
            "C": "Administrativo",
            "H": "Humanidades y Sociales",
            "A": "Artístico",
            "S": "Ciencias de la Salud",
            "I": "Enseñanzas Técnicas",
            "D": "Defensa y Seguridad",
            "E": "Ciencias Experimentales"
        }

        df_plot['Área'] = df_plot['Área'].map(areas_long)

        # --------------------------------------------
        # Formato largo para stacked
        # --------------------------------------------
        df_long = df_plot.melt(
            id_vars='Área',
            value_vars=['Verde', 'Amarillo'],
            var_name='Perfil',
            value_name='Valor'
        )

        # --------------------------------------------
        # GRÁFICA
        # --------------------------------------------
        fig = px.bar(
            df_long,
            y='Área',
            x='Valor',
            color='Perfil',
            barmode='stack',
            orientation='h',
            color_discrete_map={
                'Verde': '#22c55e',
                'Amarillo': '#f59e0b'
            },
            title=f"Perfil CHASIDE por área – {carrera_sel}"
        )

        fig.update_layout(
            xaxis_title="Nivel promedio CHASIDE",
            yaxis_title="Área",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        # --------------------------------------------
        # INTERPRETACIÓN AUTOMÁTICA
        # --------------------------------------------
        st.markdown("### 🔎 Lectura del gráfico")

        top3 = df_plot.head(3)

        st.markdown("**Áreas con mayor diferencia (prioridad de intervención):**")
        for _, row in top3.iterrows():
            st.markdown(
                f"- **{row['Área']}** → Diferencia de {row['Brecha']:.2f} puntos "
                f"(Verde: {row['Verde']:.2f} vs Amarillo: {row['Amarillo']:.2f})"
            )

import plotly.graph_objects as go

# ============================================
# 🌊 Diagrama de Sankey: carrera elegida vs carrera sugerida
# ============================================
st.header("🌊 Migración potencial entre carreras según CHASIDE")

st.caption(
    "El diagrama muestra cómo podrían redistribuirse los estudiantes desde la carrera elegida "
    "hacia la carrera con mejor ajuste al perfil CHASIDE."
)

df_sankey = df.copy()

# Tomar solo casos válidos para sugerencia de migración
df_sankey = df_sankey[
    ~df_sankey['Carrera_Mejor_Perfilada'].isin([
        'Información no confiable',
        'Sin sugerencia clara'
    ])
].copy()

# Convertir a string y limpiar
df_sankey[columna_carrera] = df_sankey[columna_carrera].astype(str).str.strip()
df_sankey['Carrera_Mejor_Perfilada'] = df_sankey['Carrera_Mejor_Perfilada'].astype(str).str.strip()

if df_sankey.empty:
    st.info("No hay datos suficientes para construir el Sankey.")
else:
    # --------------------------------------------
    # Conteos iniciales y finales
    # --------------------------------------------
    iniciales = df_sankey[columna_carrera].value_counts().to_dict()
    finales = df_sankey['Carrera_Mejor_Perfilada'].value_counts().to_dict()

    carreras_origen = sorted(df_sankey[columna_carrera].unique())
    carreras_destino = sorted(df_sankey['Carrera_Mejor_Perfilada'].unique())

    # Etiquetas con n inicial y final
    labels_origen = [
        f"{c}<br>Inicial: {iniciales.get(c, 0)}"
        for c in carreras_origen
    ]
    labels_destino = [
        f"{c}<br>Final: {finales.get(c, 0)}"
        for c in carreras_destino
    ]

    labels = labels_origen + labels_destino

    # Índices de nodos
    source_map = {c: i for i, c in enumerate(carreras_origen)}
    target_map = {c: i + len(carreras_origen) for i, c in enumerate(carreras_destino)}

    # --------------------------------------------
    # Flujos
    # --------------------------------------------
    flujos = (
        df_sankey
        .groupby([columna_carrera, 'Carrera_Mejor_Perfilada'])
        .size()
        .reset_index(name='N')
    )

    source = flujos[columna_carrera].map(source_map).tolist()
    target = flujos['Carrera_Mejor_Perfilada'].map(target_map).tolist()
    value = flujos['N'].tolist()

    # Hover personalizado
    customdata = np.stack(
        [
            flujos[columna_carrera],
            flujos['Carrera_Mejor_Perfilada'],
            flujos['N']
        ],
        axis=-1
    )

    # Colores base por nodo
    node_colors = (
        ['#60a5fa'] * len(carreras_origen) +   # azul lado izquierdo
        ['#34d399'] * len(carreras_destino)    # verde lado derecho
    )

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18,
            thickness=20,
            line=dict(color="gray", width=0.5),
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            customdata=customdata,
            hovertemplate=(
                "Carrera elegida: %{customdata[0]}<br>"
                "Carrera sugerida: %{customdata[1]}<br>"
                "Estudiantes: %{customdata[2]}<extra></extra>"
            )
        )
    )])

    fig.update_layout(
        title="Migración potencial entre carreras",
        font=dict(size=13),
        height=700
    )

    st.plotly_chart(fig, use_container_width=True)
