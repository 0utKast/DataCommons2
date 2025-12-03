# Asistente Inteligente de Data Commons

Este proyecto es una aplicación web que permite a los usuarios consultar datos estadísticos complejos mediante lenguaje natural. Utiliza Inteligencia Artificial (**Google Gemini**) conectada a la inmensa base de datos de **Data Commons** a través del **Model Context Protocol (MCP)**.

## 🚀 Características

*   **Consultas en Lenguaje Natural**: Pregunta sobre demografía, economía, salud, clima, etc., como si hablaras con un experto.
*   **Datos Veraces**: La IA no "alucina" los datos; los consulta en tiempo real desde Data Commons (agregador de Google con fuentes como Banco Mundial, ONU, Eurostat, etc.).
*   **Visualización Clara**: Las respuestas se presentan con tablas formateadas en Markdown para facilitar la lectura de grandes volúmenes de datos.
*   **Arquitectura Agéntica**: Implementación real de un agente de IA que utiliza herramientas (Function Calling) para investigar antes de responder.

## 🛠️ Arquitectura

La aplicación sigue una arquitectura moderna de 3 capas:

1.  **Frontend**: Interfaz web limpia construida con HTML, CSS y JavaScript.
2.  **Backend (Orquestador)**: Servidor Python con **Flask** que gestiona la sesión y el bucle del agente.
3.  **Capa de Datos (MCP)**: Servidor **MCP** (`datacommons-mcp`) que expone herramientas estandarizadas para consultar el Grafo de Conocimiento.

### Flujo de Trabajo
1.  El usuario hace una pregunta (ej. "¿Población de España por provincias?").
2.  El backend envía la pregunta a **Gemini 2.0 Flash** junto con las definiciones de las herramientas disponibles.
3.  Gemini razona y decide qué herramientas usar (ej. `get_observations`).
4.  El backend ejecuta las herramientas en el servidor MCP y devuelve los resultados a Gemini.
5.  Gemini procesa los datos y genera una respuesta final para el usuario.

## 📋 Requisitos

*   Python 3.10 o superior.
*   Una API Key de Google Gemini (puedes obtenerla en [Google AI Studio](https://aistudio.google.com/)).
*   Git.

## 🔧 Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/0utKast/DataCommons2.git
    cd DataCommons2
    ```

2.  **Crear y activar un entorno virtual (recomendado):**
    ```bash
    python -m venv .venv
    # En Windows:
    .venv\Scripts\activate
    # En macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno:**
    Crea un archivo `.env` en la raíz del proyecto (puedes copiar `.env.example`) y añade tu clave de API:
    ```env
    GEMINI_API_KEY=tu_clave_api_aqui
    ```

## ▶️ Uso

1.  **Iniciar la aplicación:**
    ```bash
    python app.py
    ```

2.  **Abrir en el navegador:**
    Visita `http://localhost:5000` en tu navegador web.

3.  **Interactuar:**
    Escribe tus preguntas en el chat. Ejemplos:
    *   *"¿Cuál es la esperanza de vida en Japón vs España?"*
    *   *"Dime la población de los condados de California."*
    *   *"¿Cómo ha evolucionado el PIB de Argentina en los últimos 10 años?"*

## 🧠 Detalles Técnicos

Este proyecto resuelve varios desafíos de integración interesantes:
*   **Integración Síncrona/Asíncrona**: Puente entre Flask (WSGI) y el cliente MCP (Asyncio).
*   **Sanitización de Esquemas**: Adaptación de esquemas JSON complejos de Data Commons para ser compatibles con la API de Gemini.
*   **Transporte Stdio**: Comunicación segura y rápida entre el servidor web y el servidor MCP mediante tuberías locales.

## 📄 Licencia

Este proyecto está bajo la Licencia Apache 2.0. Consulta el archivo LICENSE para más detalles.
