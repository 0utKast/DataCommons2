import os
import asyncio
import json
import sys
import traceback
from flask import Flask, request, jsonify, send_from_directory
from mcp import ClientSession
import google.generativeai as genai
from google.generativeai import protos
from google.generativeai.types import FunctionDeclaration, Tool

# Fix for Windows Asyncio Subprocess issues
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = Flask(__name__, static_folder='static')

# Configuration
# We will use stdio transport instead of SSE to avoid network issues
MCP_SERVER_COMMAND = "python"
MCP_SERVER_ARGS = ["run_mcp_server.py"] # We will modify run_mcp_server.py to use stdio

# Global variable to store the API Key (in memory for this session)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def configure_genai(api_key):
    global GEMINI_API_KEY
    GEMINI_API_KEY = api_key
    genai.configure(api_key=GEMINI_API_KEY)

# --- MCP Client Helpers ---

import mcp.client.stdio
from mcp.client.stdio import stdio_client

def run_async(coro):
    """Helper to run async code in a sync Flask route"""
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "This event loop is already running" in str(e):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        raise e

async def _get_mcp_tools_schema():
    """Fetches tools from MCP and converts them to Gemini Function Declarations."""
    print(f"Connecting to MCP via stdio...")
    try:
        # Use stdio client
        server_params = mcp.client.stdio.StdioServerParameters(
            command="python",
            args=["run_mcp_server.py"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                
                gemini_tools = []
                for tool in result.tools:
                    # Sanitize Schema for Gemini
                    # Gemini (Protobuf Schema) doesn't support 'anyOf', 'oneOf', etc. well in all cases
                    # We need to simplify the schema or remove unsupported fields.
                    
                    schema = tool.inputSchema.copy()
                    
                    def sanitize_schema(s):
                        if isinstance(s, dict):
                            # Remove unsupported keys for Gemini Protobuf Schema
                            # 'default' is NOT supported in the FunctionDeclaration Schema
                            keys_to_remove = [
                                'anyOf', 'oneOf', 'allOf', '$schema', 
                                'additionalProperties', 'default', 'title'
                            ]
                            for key in keys_to_remove:
                                if key in s:
                                    del s[key]
                            
                            # Recursively clean properties
                            if 'properties' in s:
                                for prop_name, prop_val in s['properties'].items():
                                    sanitize_schema(prop_val)
                            if 'items' in s:
                                sanitize_schema(s['items'])
                        return s

                    sanitized_schema = sanitize_schema(schema)

                    func_decl = FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=sanitized_schema
                    )
                    gemini_tools.append(func_decl)
                
                print(f"Successfully loaded {len(gemini_tools)} tools.")
                return gemini_tools
    except Exception as e:
        print(f"Error fetching MCP tools: {e}")
        traceback.print_exc()
        raise e

async def _call_mcp_tool(tool_name, arguments):
    print(f"Executing Tool: {tool_name} with args: {arguments}")
    try:
        server_params = mcp.client.stdio.StdioServerParameters(
            command="python",
            args=["run_mcp_server.py"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                
                output_text = ""
                if result.content:
                    for content in result.content:
                        if hasattr(content, 'text'):
                            output_text += content.text
                return output_text
    except Exception as e:
        print(f"Error calling tool: {e}")
        raise e

# --- Chat Logic ---

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/config', methods=['POST'])
def config_api():
    data = request.json
    api_key = data.get('apiKey')
    if api_key:
        configure_genai(api_key)
        return jsonify({"status": "ok"})
    return jsonify({"error": "API Key required"}), 400

@app.route('/api/test_mcp', methods=['GET'])
def test_mcp():
    try:
        tools = run_async(_get_mcp_tools_schema())
        return jsonify({"status": "ok", "tools_count": len(tools)})
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    if not GEMINI_API_KEY:
        return jsonify({"error": "API_KEY_MISSING", "message": "Por favor configura tu Gemini API Key primero."}), 401

    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "Message required"}), 400

    try:
        # 1. Get Tools
        try:
            tools_schema = run_async(_get_mcp_tools_schema())
        except Exception as e:
            return jsonify({"error": "MCP_ERROR", "message": f"Error conectando con Data Commons: {str(e)}"}), 503
        
        if not tools_schema:
            return jsonify({"error": "MCP_ERROR", "message": "No se encontraron herramientas en Data Commons."}), 503

        # 2. Initialize Model with Tools
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-exp',
            tools=[Tool(function_declarations=tools_schema)],
            system_instruction="Eres un asistente experto en datos. Tu objetivo es obtener los datos estadísticos solicitados por el usuario.\n\nREGLAS IMPORTANTES:\n1. NO te detengas en pasos intermedios. Si encuentras los códigos necesarios, EJECUTA inmediatamente la herramienta de obtención de datos (get_observations).\n2. FORMATO DE SALIDA: Cuando presentes listas de datos (como poblaciones, PIB, etc.), DEBES usar SIEMPRE una TABLA MARKDOWN.\n   CRÍTICO: Debes poner un SALTO DE LÍNEA (\\n) al final de cada fila de la tabla. No escribas la tabla en una sola línea.\n\n   Ejemplo CORRECTO:\n   | Provincia | Población |\n   | :--- | :--- |\n   | Madrid | 6,000,000 |\n   | Barcelona | 5,000,000 |\n\n3. Si el usuario pregunta por provincias de España, usa 'AdministrativeArea2'."
        )

        # 3. Start Chat Session
        chat_session = model.start_chat(enable_automatic_function_calling=False)
        
        # 4. Send Message to Model
        response = chat_session.send_message(user_message)
        
        # 5. Handle Tool Calls (The Agent Loop)
        final_response_text = ""
        tool_calls_info = []

        # Loop to handle multiple tool calls if needed (max depth 10)
        for _ in range(10):
            # Check for function calls in ANY part of the response
            function_calls = []
            text_parts = []
            
            if response.parts:
                for part in response.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    if part.text:
                        text_parts.append(part.text)
            
            if function_calls:
                # We have tools to execute!
                tool_outputs = []
                
                for fc in function_calls:
                    tool_name = fc.name
                    # Convert Protobuf Map/RepeatedComposite to native Python dict/list
                    tool_args = {}
                    for k, v in fc.args.items():
                        if hasattr(v, '__iter__') and not isinstance(v, (str, bytes, dict)):
                            tool_args[k] = list(v)
                        else:
                            tool_args[k] = v
                    
                    tool_calls_info.append({"tool": tool_name, "args": tool_args})
                    
                    # Execute Tool
                    try:
                        tool_result = run_async(_call_mcp_tool(tool_name, tool_args))
                    except Exception as e:
                        tool_result = f"Error executing tool: {str(e)}"
                    
                    # Create function response part
                    tool_outputs.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={'result': tool_result}
                            )
                        )
                    )
                
                # Send ALL results back to the model
                response = chat_session.send_message(
                    genai.protos.Content(parts=tool_outputs)
                )
            else:
                # No function calls, this is the final answer
                final_response_text = "".join(text_parts)
                if not final_response_text:
                    final_response_text = "..."
                
                # Post-process: Fix compressed tables (replace "| |" with "|\n|")
                # This handles cases where the model outputs tables in a single line
                if "| |" in final_response_text:
                    final_response_text = final_response_text.replace("| |", "|\n|")
                
                break
        
        return jsonify({
            "response": final_response_text,
            "tool_calls": tool_calls_info
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

if __name__ == '__main__':
    print("Starting Smart Data Commons App...")
    app.run(debug=True, port=5000)
