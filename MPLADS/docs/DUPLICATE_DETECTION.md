# Duplicate candidate analysis

Only real active-release work descriptions with at least four tokens are considered. Candidates are blocked by the supplied State and District / IDA values, vectorized with word-and-bigram TF-IDF, and compared through bounded nearest-neighbour cosine similarity. Self-matches are excluded and pairs are fingerprinted in canonical key order.

Similarity >=0.88 produces a potential duplicate candidate. High review priority additionally requires >=0.95 similarity, the same District / IDA, and (when present) >=0.80 sanction-amount similarity. This does not confirm a duplicate.
