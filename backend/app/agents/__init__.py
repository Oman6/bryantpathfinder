"""Multi-agent orchestration layer for BryantPathfinder.

Four specialized agents that run in parallel to enrich schedule results:
1. ProfessorMatchAgent — professor recommendations based on RMP + preferences
2. WorkloadAgent — estimates weekly study hours and flags overloaded days
3. NegotiatorAgent — analyzes over-constrained problems and proposes trades
4. MultiSemesterAgent — plans 4-semester roadmaps with prerequisite chains
"""
