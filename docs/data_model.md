# Data Model

## Sources
- `app_events`: product event stream for activation, adoption, and publish behavior
- `users_workspaces`: user and workspace dimension records
- `subscriptions`: plan status and recurring revenue context
- `experiments`: experiment assignment facts
- `support_feedback`: ticket text and resolution metadata

## Silver Entities
- `silver_app_events`: valid event rows with canonical event names and ingestion metadata
- `silver_users_workspaces`: sanitized user dimension with masked PII
- `silver_subscriptions`: normalized subscription facts with standardized plan tiers
- `silver_experiments`: latest assignment per user and experiment
- `silver_support_feedback`: validated support tickets with cleaned text
- `silver_support_feedback_enriched`: ticket-level topic, sentiment, summary, and confidence

## Gold Output Grains
| Table | Grain | Main Measures |
|---|---|---|
| `gold_daily_product_metrics` | `metric_date` | active users, active workspaces, publish events, paid workspaces, MRR |
| `gold_activation_funnel` | `metric_date` | workspaces reaching signup, create, upload, generate, publish |
| `gold_feature_adoption` | `metric_date, event_name` | unique users, unique workspaces, total events |
| `gold_workspace_retention` | `cohort_month, activity_month` | retained workspaces, cohort size, retention rate |
| `gold_experiment_readout` | `experiment_id, variant` | assigned users, generated users, published users, publish conversion |
| `gold_support_topic_trends` | `feedback_date, topic` | ticket count, avg confidence, negative ticket count |

## PII Handling
- `email` is masked in silver
- `full_name` is pseudonymized in silver
- raw PII stays in bronze only for lineage and platform completeness
