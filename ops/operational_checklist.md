# Operational Checklist

- Confirm the batch widget points to the intended raw drop.
- Confirm the correct catalog and schema prefix before the setup notebook creates tables.
- Check pipeline audit rows after every task.
- Check quarantine counts after the silver notebook.
- Check `gold_support_topic_trends` after LLM enrichment.
- Check metric reconciliation and duplicate checks after quality validation.
- Capture screenshots or notebook output for the README after the first successful full run in Databricks.

