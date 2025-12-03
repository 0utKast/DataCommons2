# Informe Técnico: Asistente Inteligente de Data Commons

Este documento detalla la arquitectura, tecnologías y funcionamiento de la aplicación "Asistente Data Commons". Esta aplicación permite a los usuarios consultar datos estadísticos complejos mediante lenguaje natural, utilizando una Inteligencia Artificial (Gemini) conectada a la inmensa base de datos de Data Commons a través del protocolo MCP.

---

## 1. ¿Qué es Data Commons?

**Data Commons** es una iniciativa de Google que organiza la información pública del mundo. Agrega datos de cientos de fuentes fiables (como el Banco Mundial, la ONU, Eurostat, censos nacionales, CDC, NOAA, etc.) en un único **Grafo de Conocimiento** unificado.

*   **El Problema:** Normalmente, los datos están dispersos en miles de formatos (CSV, PDF, Excel) y sitios web diferentes.
*   **La Solución:** Data Commons normaliza estos datos, vinculando entidades (como "España", "Población", "2024") en un formato estándar.
*   **En esta App:** Usamos Data Commons como nuestra "fuente de verdad" para responder preguntas sobre demografía, economía, salud, clima, etc.

## 2. ¿Qué es MCP (Model Context Protocol)?

El **Model Context Protocol (MCP)** es un estándar abierto que permite conectar modelos de IA (como Gemini o Claude) con fuentes de datos y herramientas externas de manera segura y uniforme.

*   **Antes de MCP:** Cada integración requiera código personalizado ("pegamento") para cada API específica.
*   **Con MCP:** Se crea un "Servidor MCP" que expone sus capacidades (recursos, herramientas, prompts) de forma estandarizada. Cualquier "Cliente MCP" (como nuestra app o un IDE como Cursor) puede conectarse a él y usar esas herramientas sin saber cómo funcionan por dentro.

## 3. Arquitectura de la Aplicación

La aplicación sigue una arquitectura de 3 capas:

1.  **Frontend (Interfaz de Usuario):** HTML/CSS/JS.
2.  **Backend (Orquestador):** Python con Flask.
3.  **Capa de Datos (Herramientas):** Servidor MCP de Data Commons.

### A. El Servidor MCP (`datacommons-mcp`)
Usamos el paquete oficial `datacommons-mcp`. Este actúa como un servidor que expone funciones específicas (Tools) para consultar el grafo de conocimiento.
*   **Transporte:** Usamos `stdio` (entrada/salida estándar). El backend lanza el servidor MCP como un subproceso y se comunica con él mediante tuberías (pipes), lo que es rápido y seguro localmente.
*   **Herramientas Clave:**
    *   `get_observations`: Obtiene el dato numérico real (ej. población de Madrid en 2023).
    *   `validate_child_place_types`: Ayuda a entender la geografía (ej. saber que "Spain" contiene "AdministrativeArea2" que son las provincias).
    *   `get_available_variables`: Permite explorar qué datos existen para un lugar.

### B. El Cerebro: Google Gemini (`google-generativeai`)
Usamos el modelo **Gemini 2.0 Flash Exp** como el motor de razonamiento.
*   **Rol:** No "sabe" los datos de memoria (lo cual evitaría alucinaciones), sino que sabe **cómo buscarlos**.
*   **Function Calling:** Al iniciar el chat, le enviamos a Gemini la lista de herramientas disponibles en el servidor MCP. Gemini decide cuándo y cómo usarlas basándose en la pregunta del usuario.

### C. El Backend (Flask)
Es el intermediario que gestiona el "Bucle del Agente" (Agent Loop).
*   Recibe el mensaje del usuario.
*   Se lo envía a Gemini.
*   Si Gemini pide ejecutar una herramienta (ej. `get_observations`), el backend:
    1.  Intercepta la petición.
    2.  Ejecuta la herramienta en el servidor MCP.
    3.  Toma el resultado (JSON).
    4.  Se lo devuelve a Gemini.
*   Finalmente, envía la respuesta de texto de Gemini al frontend.

## 4. Flujo de una Consulta (Paso a Paso)

Supongamos que el usuario pregunta: *"¿Cuál es la población de España por provincias?"*

1.  **Usuario:** Envía la pregunta desde el navegador.
2.  **Backend:** Inicia una sesión con Gemini y le pasa las definiciones de las herramientas MCP.
3.  **Gemini (Razonamiento):**
    *   "El usuario quiere población de provincias de España."
    *   "Primero necesito saber qué tipo de lugar son las provincias en España."
    *   *Decisión:* Llamar a `validate_child_place_types(parent_place='Spain')`.
4.  **Backend:** Ejecuta esa herramienta vía MCP y devuelve: `['AdministrativeArea1', 'AdministrativeArea2']`.
5.  **Gemini (Razonamiento):**
    *   "Vale, las provincias suelen ser AdministrativeArea2."
    *   "Ahora pido los datos."
    *   *Decisión:* Llamar a `get_observations(variable='Count_Person', entity='Spain', child_type='AdministrativeArea2')`.
6.  **Backend:** Ejecuta la herramienta y obtiene un JSON gigante con las poblaciones.
7.  **Gemini (Respuesta):** Procesa ese JSON y genera una respuesta en lenguaje natural (y Markdown) para el usuario: "Aquí tienes la población... | Provincia | Población | ...".
8.  **Frontend:** Recibe el Markdown y lo renderiza como una tabla bonita.

## 5. Desafíos Técnicos Resueltos

Durante el desarrollo, superamos varios retos interesantes:

*   **Conexión Asíncrona en Flask:** Flask es síncrono por defecto, pero MCP es asíncrono. Implementamos un gestor de bucles de eventos (`asyncio`) personalizado para permitir que convivan.
*   **Compatibilidad de Esquemas:** Data Commons usa esquemas JSON muy complejos (con `anyOf`, `default`) que Gemini no soporta nativamente. Creamos un "sanitizador" de esquemas en el backend para simplificar las definiciones antes de enviarlas a la IA.
*   **Serialización Protobuf:** Las respuestas de Gemini vienen en formato Protobuf (Google). Tuvimos que implementar convertidores para transformar estos objetos en diccionarios Python estándar y JSON.
*   **Formato de Salida:** Para asegurar tablas legibles, implementamos instrucciones de sistema estrictas ("System Prompts") y un post-procesador de texto para corregir errores de formato en las tablas Markdown.

## 6. Conclusión

Esta aplicación es un ejemplo perfecto de la **IA Agéntica**: la IA no es solo un generador de texto, sino un operador de sistemas. Usa herramientas reales para acceder a datos veraces y actualizados, combinando la flexibilidad del lenguaje natural con la precisión de una base de datos estructurada como Data Commons.
