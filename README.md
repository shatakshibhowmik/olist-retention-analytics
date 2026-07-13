# Project 1: SQL + Business Analytics Case Study — Olist Retention & CLV
**Live dashboard:** [Tableau Public](https://public.tableau.com/views/OlistE-CommerceRetentionAnalysis/OlistE-CommerceRepeat-PurchaseRetentionAnalysis_?:language=en-US&publish=yes&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)
**Data source:** Brazilian E-Commerce Public Dataset by Olist — real, anonymized commercial
transaction data, 99,441 orders (2016–2018). Original source: Kaggle
(kaggle.com/datasets/olistbr/brazilian-ecommerce). CSVs included here for convenience.

## Setup (PostgreSQL)

1. Install PostgreSQL locally (or use a free-tier cloud instance — Supabase, Neon, or ElephantSQL
   all work and give you a shareable connection string, useful if you want to demo this live).
2. Create a database: `createdb olist_project`
3. Run the schema: `psql -d olist_project -f schema.sql`
4. Copy the CSVs from `data/` to a path Postgres can read (e.g. `/tmp/`), then run:
   `psql -d olist_project -f load.sql`
   (edit the file paths inside `load.sql` if your CSVs live somewhere else)
5. Run the KPI queries: `psql -d olist_project -f queries.sql`

## Key data-modeling note (put this in your case study)

`customer_id` is unique **per order** in this dataset — Olist assigns a new one every time someone
buys something. `customer_unique_id` is the actual person. Every query here joins through
`customer_unique_id` for anything about repeat behavior. Skipping this is the single most common
mistake in public analyses of this dataset, and produces a fake ~97% "churn rate" that's really
just an artifact of the ID design.

## Real findings (computed, not estimated)

- **Repeat purchase rate: 3.04%** (2,888 of 94,990 unique customers placed more than one order).
  This is a genuine, well-documented characteristic of this marketplace — most buyers are
  one-time. It reframes the whole project: see below.
- **Average CLV, one-time buyers: R$161.19. Average CLV, repeat buyers: R$308.35** — repeat
  buyers are worth 91% more. This is your headline business metric, not the retention curve
  (which is very thin month-over-month, precisely because repeat purchase is rare here).
- **Highest-dissatisfaction category: fashion_male_clothing**, 27.7% of reviews scored ≤2,
  followed by office_furniture (26.1%) and fixed_telephony (24.7%). These are candidate features
  for the prediction model below.

## Why "churn prediction" doesn't fit this dataset — and what to build instead

Classic churn modeling assumes an ongoing relationship (subscriptions, monthly active users).
With a 97% one-time-buyer marketplace, there's no ongoing relationship to churn from. The
defensible, more sophisticated framing:

**Predict which first-time buyers are likely to become repeat buyers**, using signals available
at or shortly after their first order: review score, delivery speed vs. estimate, payment type,
installment count, product category, order value. This is a genuinely harder and more honest
problem than a templated churn model, and it's worth explicitly explaining this judgment call in
interviews — it shows you adapted the technique to the data instead of forcing a standard
tutorial onto it.

## Next steps (not yet built)

1. **Feature engineering**: build a first-order feature table (one row per `customer_unique_id`,
   using only their *first* order's attributes) with a binary label `became_repeat_buyer`.
2. **Model**: scikit-learn — start with logistic regression as a baseline, compare against
   random forest or gradient boosting. Given the ~3% positive class rate, this is also a good
   opportunity to practice handling class imbalance (class weights or SMOTE) — another strong
   interview talking point.
3. **Dashboard**: Tableau Public or Power BI — repeat-purchase rate and CLV uplift by state,
   category, and payment type; feed in the model's top features as an "at-risk vs. high-value"
   segment view.
4. **Memo**: one page — which segments are worth investing retention effort in, and why, backed
   by the CLV gap.

## Files in this folder

- `schema.sql` — table definitions with foreign keys and indexes
- `load.sql` — COPY commands to load the CSVs (FK-safe order)
- `queries.sql` — the 4 KPI queries above, fully commented
- `data/` — the 8 source CSVs
**Live dashboard:** [Tableau Public](https://public.tableau.com/views/OlistE-CommerceRetentionAnalysis/OlistE-CommerceRepeat-PurchaseRetentionAnalysis_?:language=en-US&publish=yes&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)
