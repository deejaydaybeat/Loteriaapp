# Euromillones & Eurodreams — Panel de estadísticas

App personal en Streamlit para guardar el histórico de sorteos de
Euromillones y Eurodreams y explorar estadísticas (frecuencias, atraso,
parejas frecuentes) y un generador de combinaciones ponderado.

⚠️ **Aviso**: cada sorteo es un evento independiente y equiprobable.
Esta app es para explorar datos y jugar, no predice el próximo resultado.

## Uso en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sin más configuración, los datos se guardan en `loteria.db` (SQLite) en
la misma carpeta.

## Desplegar en Streamlit Community Cloud

1. Sube este repositorio a GitHub (ver pasos más abajo).
2. Entra en https://share.streamlit.io/ con tu cuenta de GitHub.
3. "New app" → elige el repositorio → archivo principal: `app.py` → Deploy.

### Persistencia de datos en la nube (Turso)

Streamlit Cloud resetea el sistema de archivos en cada reinicio del
contenedor, así que **sin base de datos externa perderás los sorteos
que añadas desde la app publicada**. Para evitarlo, esta app usa
[Turso](https://turso.tech) (gratis) automáticamente si configuras estos
dos "Secrets" en el panel de tu app en Streamlit Cloud
(⚙️ Settings → Secrets):

```toml
TURSO_DATABASE_URL = "libsql://tu-base-de-datos.turso.io"
TURSO_AUTH_TOKEN = "tu-token"
```

Para crear la base de datos en Turso:

```bash
# Instalar la CLI de Turso (una vez)
curl -sSfL https://get.tur.so/install.sh | bash

turso auth signup      # o: turso auth login
turso db create loteria
turso db show --url loteria
turso db tokens create loteria
```

Copia la URL y el token que te dan esos dos últimos comandos en los
Secrets de Streamlit Cloud tal como arriba.

Si **no** configuras estos Secrets, la app sigue funcionando igual pero
usando SQLite local (útil para probar el despliegue rápido, aunque los
datos no persistirán entre reinicios).

## Subir el proyecto a GitHub (si nunca lo has hecho)

```bash
cd loteria_app
git init
git add .
git commit -m "Primera versión de la app de lotería"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/loteria-app.git
git push -u origin main
```

(Crea antes el repositorio vacío en GitHub, sin README ni .gitignore,
desde github.com/new — para que el `git push` no choque con nada.)
