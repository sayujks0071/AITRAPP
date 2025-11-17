#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import * as path from "path";

/**
 * Trading Analyst MCP Server
 *
 * High-level analysis and risk monitoring for algo trading stack.
 * Provides digested views of:
 * - Live risk (margins, greeks, tail coverage)
 * - Strategy performance and allocation
 * - Broker vs algo reconciliation
 * - Event/regime context
 * - Config change proposals
 *
 * SAFETY: This server is READ-ONLY. No trading tools exposed.
 */

class TradingAnalystServer {
  private server: Server;
  private pythonAdapterPath: string;

  constructor() {
    this.server = new Server(
      {
        name: "trading-analyst",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Python adapter that talks to FastAPI bot + Kite
    // Adjust this path based on your setup
    this.pythonAdapterPath = path.join(
      __dirname,
      "..",
      "..",
      "..",
      "mcp-adapters",
      "trading_analyst_adapter.py"
    );

    this.setupHandlers();
  }

  private setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "get_live_risk_snapshot",
          description:
            "Get comprehensive live risk snapshot: portfolio greeks (delta/gamma/vega/theta), margin usage, short premium exposure, and tail coverage. Returns single JSON with all key risk metrics and flags.",
          inputSchema: {
            type: "object",
            properties: {},
            required: [],
          },
        },
        {
          name: "get_strategy_summary",
          description:
            "Get per-strategy performance summary: realised/unrealised PnL, hit rate, max drawdown, current allocation, and regime usage. Use this to evaluate which strategies justify more/less capital or should be paused.",
          inputSchema: {
            type: "object",
            properties: {
              lookback_days: {
                type: "number",
                description:
                  "Number of days to look back for hit rate and drawdown calculations (default: 60)",
                default: 60,
              },
            },
            required: [],
          },
        },
        {
          name: "get_broker_vs_algo_reconciliation",
          description:
            "Compare broker (Kite) positions vs algo engine state. Detects mismatches, orphan positions, and reporting delays. Critical safety check for state drift.",
          inputSchema: {
            type: "object",
            properties: {},
            required: [],
          },
        },
        {
          name: "get_event_and_regime_context",
          description:
            "Get current R1 regime classification + E1 event context for each underlying. Shows vol regime (LOW/MEDIUM/HIGH), IV rank, RV/IV, and event day type (PRE_EVENT/EVENT_DAY/POST_EVENT). Use this to understand which strategies are naturally favored today.",
          inputSchema: {
            type: "object",
            properties: {},
            required: [],
          },
        },
        {
          name: "propose_config_tweaks",
          description:
            "Analyze recent performance and propose config changes: allocator weight adjustments, regime band edits, strategy parameter tweaks. Returns patch proposals in JSON format. NEVER applies changes automatically - always requires human review.",
          inputSchema: {
            type: "object",
            properties: {
              analysis_window_days: {
                type: "number",
                description:
                  "Number of days to analyze for proposing changes (default: 30)",
                default: 30,
              },
              focus: {
                type: "string",
                description:
                  "Focus area: 'allocator' (weight changes), 'regimes' (R1 bands), 'strategies' (individual strategy params), or 'all'",
                enum: ["allocator", "regimes", "strategies", "all"],
                default: "all",
              },
            },
            required: [],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "get_live_risk_snapshot":
            return await this.callPythonAdapter("get_live_risk_snapshot", {});

          case "get_strategy_summary":
            return await this.callPythonAdapter("get_strategy_summary", {
              lookback_days: args?.lookback_days || 60,
            });

          case "get_broker_vs_algo_reconciliation":
            return await this.callPythonAdapter(
              "get_broker_vs_algo_reconciliation",
              {}
            );

          case "get_event_and_regime_context":
            return await this.callPythonAdapter(
              "get_event_and_regime_context",
              {}
            );

          case "propose_config_tweaks":
            return await this.callPythonAdapter("propose_config_tweaks", {
              analysis_window_days: args?.analysis_window_days || 30,
              focus: args?.focus || "all",
            });

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text",
              text: `Error calling tool ${name}: ${errorMessage}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  /**
   * Call Python adapter script to fetch data from bot API + Kite
   */
  private async callPythonAdapter(
    toolName: string,
    args: Record<string, any>
  ): Promise<{ content: Array<{ type: string; text: string }> }> {
    return new Promise((resolve, reject) => {
      const pythonProcess = spawn("python3", [
        this.pythonAdapterPath,
        toolName,
        JSON.stringify(args),
      ]);

      let stdout = "";
      let stderr = "";

      pythonProcess.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      pythonProcess.on("close", (code) => {
        if (code !== 0) {
          reject(
            new Error(
              `Python adapter failed (exit ${code}): ${stderr || stdout}`
            )
          );
          return;
        }

        try {
          // Python adapter returns JSON on stdout
          const result = JSON.parse(stdout);

          resolve({
            content: [
              {
                type: "text",
                text: JSON.stringify(result, null, 2),
              },
            ],
          });
        } catch (error) {
          reject(
            new Error(
              `Failed to parse Python adapter output: ${error}\nOutput: ${stdout}`
            )
          );
        }
      });

      pythonProcess.on("error", (error) => {
        reject(new Error(`Failed to spawn Python adapter: ${error.message}`));
      });
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Trading Analyst MCP server running on stdio");
  }
}

// Start server
const server = new TradingAnalystServer();
server.run().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
