from datacommons_mcp.server import mcp

if __name__ == "__main__":
    # Use stdio transport for direct process communication
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        import sys
        print(f"Error running server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
