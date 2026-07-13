# Memo: What Drives Repeat Purchases on Olist — and What To Do About It

**Author:** Shatakshi Bhowmik
**Data:** Brazilian E-Commerce Public Dataset by Olist — 99,441 orders, 94,990 unique customers, 2016–2018 (real, anonymized commercial data)
**Stack:** PostgreSQL (feature engineering), Python / scikit-learn / XGBoost (modeling)

---

## The problem

Only **3.04%** of Olist customers ever place a second order (2,888 of 94,990). Yet repeat buyers
are worth **91% more** on average — R$308 lifetime revenue vs. R$161 for one-time buyers. Even a
small improvement in repeat-purchase rate is a direct revenue lever. The question this analysis
answers: **can we identify, at the moment of a customer's first order, who is likely to come back —
and what does that tell us about where to invest?**

## Data-quality decision that shaped everything

In this dataset, `customer_id` resets on every order; `customer_unique_id` is the actual person.
All repeat-purchase analysis joins through `customer_unique_id`. Skipping this step — the most
common mistake in public analyses of this data — produces a meaningless ~97% "churn rate" that is
an artifact of the ID design, not customer behavior.

## Reframing the model

A classic "churn" model assumes an ongoing relationship (subscriptions, active users). A
marketplace where 97% of buyers purchase once has no relationship to churn from. The honest
formulation: **predict which first-time buyers will become repeat buyers**, using only signals
available at or shortly after the first order — order value, delivery performance, payment
behavior, product category, review response. No future information is used (no data leakage).

## What the model found

Three model families (logistic regression, random forest, XGBoost) all converge on
**ROC-AUC ≈ 0.60–0.61** (PR-AUC 0.047 vs. a 0.030 random baseline — about 1.6x lift). Two
conclusions follow:

1. **First-order signals carry real but limited predictive power.** The consistency across model
   families indicates an information ceiling, not an algorithm problem: whether someone returns
   is substantially driven by factors outside the transaction record (need recurrence,
   competitor pricing, re-engagement marketing).
2. **The signals that do matter are actionable.** Top predictors: first-purchase product
   category (furniture/décor and bed/bath/table buyers behave differently), payment installment
   behavior, average item value, delivery performance vs. promise, and whether the first review
   was ≤2 stars.

## From model to decision: choosing an operating threshold

The model's value isn't the score — it's targeting. The right threshold depends on the cost of
the retention action:

| Retention action | Threshold | Precision | Recall | Customers flagged (test set) |
|---|---|---|---|---|
| Email nudge (near-zero cost) | 0.41 | 4.1% | 60% | 8,429 |
| Discount code (moderate cost) | 0.53 | 5.1% | 30% | 3,381 |
| VIP perk / outreach (high cost) | 0.64 | 6.0% | 10% | 974 |

At near-zero marginal cost, flagging broadly and catching 60% of future repeat buyers is
rational despite low precision. As action cost rises, the threshold should tighten.

## Recommendations

1. **Deploy the low-cost tier now.** A post-delivery email sequence targeted at the top-scoring
   60%-recall segment risks almost nothing and touches most future repeat buyers.
2. **Fix delivery reliability where it's worst.** Late-vs-promise delivery was a top predictor in
   every model. Categories with the highest dissatisfaction — fashion_male_clothing (27.7% of
   reviews ≤2 stars), office_furniture (26.1%) — are the natural starting point.
3. **Treat a bad first review as a churn event.** A ≤2-star first review is a measurable
   predictor of non-return; a service-recovery workflow (apology + voucher) has a clear target
   population.
4. **Instrument what's missing.** The 0.61 ceiling is an argument for collecting behavioral data
   this dataset lacks — browse sessions, email engagement, app opens — which is where the next
   increment of predictive power lives.

## Limitations

Historical data (2016–2018) from a single marketplace; findings describe this platform, not
e-commerce generally. Precision at all thresholds is low in absolute terms — this model ranks
and targets, it does not confidently identify individuals. Revenue figures are lifetime sums
within the dataset window, not projected CLV.
