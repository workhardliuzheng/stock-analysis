import logging

import click
from mcp.server.fastmcp import FastMCP
from mcpserver.tools import tushare_tools

logger = logging.getLogger(__name__)

@click.command
def main():
    mcp = FastMCP(name="tu-share-mcp-server")
    for tool in tushare_tools.tools:
        mcp.add_tool(tool)

    logger.debug("mcpserver running")
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()