import streamlit as st
import pandas as pd
import plotly.express as px

from db import GAME_CONFIG, insert_draw, bulk_import, load_draws, delete_last
import stats

st.set_page_config(page_title="Predicciones Lotería", page_icon="🎱", layout="wide")

st.title("🎱 Euromillones & Eurodreams — Panel de estadísticas")
st.caption(
    "⚠️ Aviso importante: cada sorteo es un evento independiente y equiprobable. "
    "Ninguna estadística de este panel predice el próximo resultado — esto es "
    "para analizar el histórico y generar combinaciones por diversión."
)

juego = st.sidebar.radio(
    "Juego",
    options=list(GAME_CONFIG.keys()),
    format_func=lambda k: GAME_CONFIG[k]["label"],
)
cfg = GAME_CONFIG[juego]
df = load_draws(juego)

st.sidebar.metric("Sorteos guardados", len(df))

# ---------------------------------------------------------------- Importar / añadir datos
with st.sidebar.expander("📥 Importar histórico (CSV)", expanded=len(df) == 0):
    st.markdown(
        "Columnas requeridas: **fecha** (AAAA-MM-DD), **numeros** "
        f"({cfg['n_main']} valores separados por comas), **extras** "
        f"({cfg['n_extra']} valor(es), el/los {cfg['extra_label'].lower()}(s))."
    )
    ejemplo = pd.DataFrame(
        {
            "fecha": ["2026-09-19"],
            "numeros": [",".join(str(i) for i in range(1, cfg["n_main"] + 1))],
            "extras": [",".join(str(i) for i in range(1, cfg["n_extra"] + 1))],
        }
    )
    st.download_button(
        "Descargar plantilla CSV",
        ejemplo.to_csv(index=False).encode("utf-8"),
        file_name=f"plantilla_{juego}.csv",
        mime="text/csv",
    )
    archivo = st.file_uploader("Sube tu CSV histórico", type=["csv"], key=f"upload_{juego}")
    if archivo is not None:
        nuevo_df = pd.read_csv(archivo, dtype=str)
        ok, dup = bulk_import(juego, nuevo_df)
        st.success(f"Importados {ok} sorteos nuevos ({dup} ya existían).")
        st.rerun()

with st.sidebar.expander("➕ Añadir sorteo de hoy"):
    fecha = st.date_input("Fecha del sorteo", key=f"fecha_{juego}")
    lo, hi = cfg["main_range"]
    numeros_txt = st.text_input(
        f"{cfg['n_main']} números ({lo}-{hi}), separados por comas", key=f"nums_{juego}"
    )
    elo, ehi = cfg["extra_range"]
    extras_txt = st.text_input(
        f"{cfg['n_extra']} {cfg['extra_label'].lower()}(s) ({elo}-{ehi}), separados por comas",
        key=f"extras_{juego}",
    )
    if st.button("Guardar sorteo", key=f"guardar_{juego}"):
        try:
            numeros = [int(x) for x in numeros_txt.split(",") if x.strip()]
            extras = [int(x) for x in extras_txt.split(",") if x.strip()]
            assert len(numeros) == cfg["n_main"], f"Se esperaban {cfg['n_main']} números"
            assert len(extras) == cfg["n_extra"], f"Se esperaban {cfg['n_extra']} {cfg['extra_label'].lower()}(s)"
            if insert_draw(juego, str(fecha), numeros, extras):
                st.success("Sorteo guardado.")
            else:
                st.warning("Ese sorteo ya estaba guardado.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Deshacer último sorteo", key=f"undo_{juego}"):
        if delete_last(juego):
            st.info("Último sorteo eliminado.")
            st.rerun()

# ---------------------------------------------------------------- Panel principal
if df.empty:
    st.info("Todavía no hay sorteos guardados para este juego. Importa un CSV o añade uno a mano en la barra lateral.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Frecuencias", "⏳ Atraso", "🔗 Parejas frecuentes", "🎲 Generador"]
)

freq_main = stats.frequency_table(df, "numeros", cfg["main_range"])
freq_extra = stats.frequency_table(df, "extras", cfg["extra_range"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Frecuencia de números")
        fig = px.bar(freq_main, x="numero", y="veces", text="porcentaje")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader(f"Frecuencia de {cfg['extra_label'].lower()}s")
        fig2 = px.bar(freq_extra, x="numero", y="veces", text="porcentaje")
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("Números con más sorteos sin salir")
    atraso_main = stats.atraso_table(df, "numeros", cfg["main_range"])
    st.dataframe(atraso_main, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Parejas de números que más veces han coincidido")
    st.dataframe(stats.top_pairs(df, "numeros"), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Generador de combinaciones")
    modo = st.radio(
        "Criterio de ponderación",
        options=["aleatorio", "caliente", "frio"],
        format_func=lambda m: {
            "aleatorio": "Aleatorio puro (recomendado: es como funciona el sorteo real)",
            "caliente": "Favorecer números 'calientes' (más frecuentes históricamente)",
            "frio": "Favorecer números 'fríos' (menos frecuentes / más atraso)",
        }[m],
        key=f"modo_{juego}",
    )
    if st.button("Generar combinación", key=f"gen_{juego}"):
        numeros = stats.weighted_pick(freq_main, cfg["n_main"], modo)
        extras = stats.weighted_pick(freq_extra, cfg["n_extra"], modo)
        st.success(f"Números: {numeros}  —  {cfg['extra_label']}(s): {extras}")
    st.caption(
        "Recuerda: esta ponderación es solo un juego estadístico sobre el pasado. "
        "No aumenta matemáticamente tus probabilidades de acertar el próximo sorteo."
    )

with st.expander("Ver histórico completo"):
    tabla = df.copy()
    tabla["numeros"] = tabla["numeros"].apply(lambda x: ", ".join(map(str, x)))
    tabla["extras"] = tabla["extras"].apply(lambda x: ", ".join(map(str, x)))
    st.dataframe(tabla.sort_values("fecha", ascending=False), use_container_width=True, hide_index=True)
