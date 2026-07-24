# Post-Experiment Analysis Protocol

Every completed experiment must produce both a frozen scoring artifact and a
separate result-analysis artifact. The analysis exists to synchronize human and
Runtime understanding and to expose observations that may trigger better object
definitions. It cannot alter the experiment that generated it.

The analysis must contain:

1. **Observed facts**: run hashes, failures, costs, arm metrics, gate outcomes,
   and prediction distributions copied from validated artifacts.
2. **Phenomena**: recurring asymmetries, collapses, tradeoffs, clustered errors,
   and unexpected invariances visible in those facts.
3. **Interpretations**: mechanism hypotheses explicitly marked as inference,
   never restated as observations.
4. **Competing explanations**: plausible causes that the current design cannot
   distinguish.
5. **Still unknown**: transfer boundaries and untested downstream claims.
6. **Next cognitive object**: the smallest object whose measurement can resolve
   the most important live uncertainty.
7. **Questions for intuition**: concise questions intended to help the human
   collaborator notice a better coordinate, object, or experiment.

The scoring artifact is produced first and remains immutable. Analysis reads
that artifact by hash. It may propose a future experiment, but it must never
change labels, thresholds, candidate state, or authority in the completed run.
