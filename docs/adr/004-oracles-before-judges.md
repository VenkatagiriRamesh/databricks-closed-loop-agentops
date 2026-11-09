# ADR-004: Deterministic oracles decide first; an LLM judge only sees what they cannot

Each attack category has a pure-Python oracle (regex for PII, the copilot's own SQL guard, the
authority matrix, the decision line). It returns success, failure or *undetermined*. Only
undetermined cases go to the LLM judge, and a judge parse failure stays undetermined and is left
out of the attack success rate. So a rate can be disputed by reading the oracle, not a prompt.
