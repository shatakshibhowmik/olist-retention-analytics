import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, roc_auc_score,
                             precision_recall_curve, average_precision_score)
from xgboost import XGBClassifier

df = pd.read_csv("first_order_features.csv")

# ============================================================
# FEATURE ENGINEERING ROUND 2
# Rule: every feature must be knowable at/just after the FIRST order.
# ============================================================

# -- missingness as signal (same as before) --
df["order_never_delivered"] = df["delivery_days"].isnull().astype(int)
df["never_reviewed"] = df["review_score"].isnull().astype(int)

# -- NEW: was the order actually late vs. the promise? --
# days_early_vs_estimate < 0 means delivered AFTER the estimate.
df["delivered_late"] = (df["days_early_vs_estimate"] < 0).astype(int)

# -- NEW: purchase timing --
ts = pd.to_datetime(df["order_purchase_timestamp"])
df["purchase_month"] = ts.dt.month
df["purchase_dow"] = ts.dt.dayofweek
df["is_weekend"] = (df["purchase_dow"] >= 5).astype(int)

# -- NEW: order-composition signals --
df["avg_item_value"] = df["order_value"] / df["num_items"].replace(0, np.nan)
df["paid_in_installments"] = (df["payment_installments"] > 1).astype(int)

# -- NEW: low review flag (a 1-2 star first experience is a different signal
#    than the continuous score alone) --
df["bad_first_review"] = (df["review_score"] <= 2).astype(int)

# -- imputation (after flags are built, so the signal is preserved) --
df["delivery_days"] = df["delivery_days"].fillna(df["delivery_days"].median())
df["days_early_vs_estimate"] = df["days_early_vs_estimate"].fillna(0)
df["review_score"] = df["review_score"].fillna(df["review_score"].median())
df["avg_item_value"] = df["avg_item_value"].fillna(df["avg_item_value"].median())
df["product_category"] = df["product_category"].fillna("unknown")
df["payment_type"] = df["payment_type"].fillna("unknown")
df = df.dropna(subset=["order_value", "num_items", "payment_installments"])

top_categories = df["product_category"].value_counts().nlargest(15).index
df["product_category"] = df["product_category"].where(df["product_category"].isin(top_categories), "other")

categorical_cols = ["customer_state", "product_category", "payment_type"]
df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

feature_cols = [c for c in df_encoded.columns if c not in
                ["customer_unique_id", "order_id", "order_purchase_timestamp", "became_repeat_buyer"]]
X = df_encoded[feature_cols]
y = df_encoded["became_repeat_buyer"]
print(f"Feature matrix: {X.shape[0]} rows, {X.shape[1]} features (was 52)")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# ============================================================
# MODEL 1: Logistic Regression (re-run on richer features, as anchor)
# ============================================================
numeric_cols = ["delivery_days", "days_early_vs_estimate", "order_value", "num_items",
                 "payment_installments", "review_score", "avg_item_value",
                 "purchase_month", "purchase_dow"]
scaler = StandardScaler()
X_train_s, X_test_s = X_train.copy(), X_test.copy()
X_train_s[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
X_test_s[numeric_cols] = scaler.transform(X_test[numeric_cols])

logreg = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
logreg.fit(X_train_s, y_train)
logreg_probs = logreg.predict_proba(X_test_s)[:, 1]
print(f"\nLogistic Regression  ROC-AUC: {roc_auc_score(y_test, logreg_probs):.4f} | PR-AUC: {average_precision_score(y_test, logreg_probs):.4f}")

# ============================================================
# MODEL 2: XGBoost
# scale_pos_weight = (neg/pos) is XGBoost's class imbalance handle
# ============================================================
spw = (y_train == 0).sum() / (y_train == 1).sum()
xgb = XGBClassifier(
    n_estimators=400, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=spw, eval_metric="aucpr",
    random_state=42, n_jobs=-1,
)
xgb.fit(X_train, y_train)
xgb_probs = xgb.predict_proba(X_test)[:, 1]
print(f"XGBoost              ROC-AUC: {roc_auc_score(y_test, xgb_probs):.4f} | PR-AUC: {average_precision_score(y_test, xgb_probs):.4f}")
print(f"(Random baseline PR-AUC would be {y_test.mean():.4f} — the positive class rate)")

# ============================================================
# THRESHOLD TUNING — the business-scenario part
# ============================================================
best_probs = xgb_probs if roc_auc_score(y_test, xgb_probs) >= roc_auc_score(y_test, logreg_probs) else logreg_probs
best_name = "XGBoost" if best_probs is xgb_probs else "LogisticRegression"
precision, recall, thresholds = precision_recall_curve(y_test, best_probs)

print(f"\n=== Threshold scenarios ({best_name}) ===")
print(f"{'threshold':>10} {'precision':>10} {'recall':>8} {'flagged':>9}  scenario")
scenarios = [
    ("Cheap action (email nudge): maximize recall, accept low precision", 0.60),
    ("Moderate action (discount code): balance", 0.30),
    ("Expensive action (call/VIP perk): precision priority", 0.10),
]
for label, target_recall in scenarios:
    idx = np.argmin(np.abs(recall[:-1] - target_recall))
    thr = thresholds[idx]
    n_flagged = (best_probs >= thr).sum()
    print(f"{thr:>10.3f} {precision[idx]:>10.3f} {recall[idx]:>8.3f} {n_flagged:>9}  {label}")

# ============================================================
# FEATURE IMPORTANCE (XGBoost)
# ============================================================
imp = pd.Series(xgb.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop 12 features (XGBoost):")
print(imp.head(12).round(4))
imp.to_csv("feature_importance_xgb.csv")
