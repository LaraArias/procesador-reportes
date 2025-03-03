# Procesador de Reportes

Una aplicación de Streamlit para transformar reportes complejos en artículos fáciles de entender utilizando IA.

## Características

- Múltiples formatos de entrada (Texto, PDF, URL, Notion)
- Lenguaje adaptado a diferentes audiencias
- Extracción de puntos clave
- Formateo en Markdown
- Integración con Google Drive
- Generación de publicaciones para LinkedIn

## Requisitos

- Python 3.9+
- Streamlit
- Otras dependencias (ver `requirements.txt`)

## Instalación

1. Clona este repositorio:
   ```
   git clone https://github.com/LaraArias/procesador-reportes.git
   cd procesador-reportes
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno (ver sección siguiente)

4. Ejecuta la aplicación:
   ```
   streamlit run app.py
   ```

## Configuración de Variables de Entorno

La aplicación requiere varias claves API para funcionar correctamente. Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```
# API Keys
OPENAI_API_KEY=sk-...
SAPTIVA_API_KEY=va-ai-...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
GOOGLE_API_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/tu/archivo-credenciales.json
```

### Obtener la clave API de SAPTIVA

Para obtener una clave API de SAPTIVA:

1. Regístrate en [SAPTIVA](https://saptiva.com)
2. Navega a la sección de API Keys en tu perfil
3. Genera una nueva clave API
4. Copia la clave que comienza con `va-ai-` y agrégala a tu archivo `.env`

### Otras APIs

- **OpenAI API**: Se utiliza como fallback si SAPTIVA no está disponible. [Obtener clave](https://platform.openai.com/account/api-keys)
- **Notion API**: Para extraer contenido de páginas de Notion. [Documentación](https://developers.notion.com/docs/getting-started)
- **Google Drive API**: Para exportar a Google Drive. Requiere un archivo de credenciales JSON.

## Estructura del Proyecto

- `app.py`: Aplicación principal de Streamlit
- `.env`: Archivo de variables de entorno (no incluido en el repositorio)
- `requirements.txt`: Dependencias del proyecto
- `static/`: Archivos estáticos
- `styles/`: Archivos CSS

## Uso

1. Selecciona el tipo de entrada (Texto, PDF, URL, Notion)
2. Proporciona el contenido según el tipo seleccionado
3. Configura las opciones de transformación (audiencia, tono, formato)
4. Haz clic en "Transformar" para procesar el contenido
5. Visualiza y exporta el resultado en varios formatos

## Funcionalidades Principales

### Extracción de Texto

La aplicación puede extraer texto de:
- Archivos PDF
- URLs de artículos
- Páginas de Notion

### Transformación de Texto

El texto extraído se transforma utilizando:
- API de SAPTIVA (método principal)
- OpenAI (método de respaldo)
- Procesamiento local (si ambas APIs fallan)

### Exportación

El contenido transformado puede exportarse como:
- Markdown
- PDF
- Google Docs
- Publicaciones para LinkedIn

## Solución de Problemas

### Problemas con la API de SAPTIVA

Si encuentras errores relacionados con la API de SAPTIVA:
- Verifica que tu clave API comience con `va-ai-`
- Asegúrate de que la clave esté correctamente configurada en el archivo `.env`
- Comprueba que la URL de la API sea correcta (`https://api-dev.saptiva.com/v1/chat/completions`)

### Problemas con la Generación de Publicaciones de LinkedIn

Si la generación de publicaciones para LinkedIn falla:
- Aumenta el tiempo de espera en la configuración
- Reduce la longitud del contenido para procesar
- Verifica los logs para identificar errores específicos

## Contribuir

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir los cambios importantes antes de enviar un pull request.

## Licencia

[MIT](LICENSE) 