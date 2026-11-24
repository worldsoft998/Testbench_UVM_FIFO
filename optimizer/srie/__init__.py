"""SRIE — Simulator Runtime Introspection Engine agent.

Event-driven, runtime/introspective optimizer that observes the running
simulator via a VPI/DPI bridge and pushes optimized stimulus back instantly.
"""

__all__ = ["agent", "vpi_client", "discovery", "introspection", "event_listener"]
