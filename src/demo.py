"""
KrishiMandal — Interactive CLI Demo
Run: python -m src.demo
Lets you type queries and see the multi-agent system respond.
"""
from __future__ import annotations

import json
import sys

from src.orchestrator import SupervisorOrchestrator


BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║              🌾  KrishiMandal — Farm Intelligence  🌾        ║
║         Multi-Agent AI for Smallholder Farmers (India)        ║
╠═══════════════════════════════════════════════════════════════╣
║  Type a query in English or Hindi and press Enter.            ║
║  Type 'agents' to see registered agents.                      ║
║  Type 'examples' to see sample queries.                       ║
║  Type 'quit' to exit.                                         ║
╚═══════════════════════════════════════════════════════════════╝
"""

EXAMPLES = [
    "What is the current price of wheat?",
    "When should I harvest my crop?",
    "Show me government schemes I am eligible for",
    "My crop has spots on the leaves — what disease is this?",
    "Should I sell my soybean now or wait?",
    "What is the weather forecast for my farm?",
    "Tell me about organic farming practices",
    "What fertilizer should I use for cotton?",
    "What is PM-KISAN and am I eligible?",
    "Generate a harvest plan for my farm",
    "What is my credit score?",
    "Show me the best mandi to sell wheat",
    "मेरे गेहूं का भाव क्या है?",
    "मेरी फसल में कीट लगा है, क्या करूं?",
]


def main():
    print(BANNER)
    orchestrator = SupervisorOrchestrator()
    farmer_id = "F1001"

    while True:
        try:
            query = input("\n🧑‍🌾 You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue

        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye! Happy farming! 🌾")
            break

        if query.lower() == "agents":
            agents = orchestrator.list_agents()
            print("\nRegistered agents:")
            for a in agents:
                print(f"  • {a['name']}: {a['description']}")
            continue

        if query.lower() == "examples":
            print("\nSample queries you can try:")
            for i, ex in enumerate(EXAMPLES, 1):
                print(f"  {i:2d}. {ex}")
            continue

        # Route through the Supervisor Orchestrator
        result = orchestrator.route_query(query=query, farmer_id=farmer_id)

        print(f"\n🤖 KrishiMandal [{', '.join(result.agents_invoked)}] ({result.processing_time_ms}ms)")
        print("─" * 60)
        print(result.final_response)
        print("─" * 60)


if __name__ == "__main__":
    main()
