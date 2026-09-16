"""Settings shared by the server, the legacy CLI and the check scripts, so the
answer call and retrieval depth cannot drift between entry points."""

# Sonnet 5 for the answer and the Query Rewrite: fast and cheap enough for a
# chat loop. Kept as separate constants so they can diverge later.
ANSWER_MODEL = "claude-sonnet-5"
REWRITE_MODEL = "claude-sonnet-5"

# Sonnet 5 thinks by default and the thinking counts against max_tokens. A
# 2048 cap was fully consumed by thinking on multi-part questions, so the user
# saw an empty answer. The cap is now large enough for thinking plus a long
# answer, with adaptive thinking at medium effort (effort also governs how
# thorough the visible answer is; drop to "low" if the wait before the first
# word feels long).
ANSWER_MAX_TOKENS = 16384
ANSWER_EFFORT = "medium"
ANSWER_THINKING = {"type": "adaptive"}

# Helper calls (Query Rewrite, Fund Fact Sheet descriptions) have small caps,
# so thinking is switched off explicitly rather than left to eat the cap.
NO_THINKING = {"type": "disabled"}

# Chunks handed to the answer model. Ten rather than five so Fund Fact Sheet
# Chunks fit alongside the Article Chunks that dominate dense retrieval.
TOP_CHUNK_COUNT = 10
