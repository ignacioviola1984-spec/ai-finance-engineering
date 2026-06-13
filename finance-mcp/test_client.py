"""
test_client.py - Cliente MCP minimo para probar el server por el protocolo real.

A diferencia de importar server.py como modulo, esto se conecta al server
por stdio igual que lo haria Claude: hace el handshake (initialize),
descubre las herramientas (list_tools) y las invoca (call_tool).

Correr:  python test_client.py
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Lanzamos nuestro propio server como subproceso, con el mismo Python.
    params = StdioServerParameters(command=sys.executable, args=["server.py"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Descubrir las herramientas que expone el server.
            tools = await session.list_tools()
            print("Herramientas disponibles:")
            for t in tools.tools:
                print(f"  - {t.name}")
            print()

            # 2. Invocar un par, como lo haria un cliente real.
            r = await session.call_tool("get_pnl", {"period": "2026-05", "report_currency": "USD"})
            print(r.content[0].text)
            print()

            r = await session.call_tool("get_cash_position", {"report_currency": "USD"})
            print(r.content[0].text)
            print()

            # 3. Probar el manejo de errores: entidad invalida.
            r = await session.call_tool("get_pnl", {"period": "2026-05", "entity_id": "XX"})
            print("Prueba de error (entidad invalida):")
            print(" ", r.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
