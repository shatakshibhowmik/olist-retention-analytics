import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

df = pd.read_csv("first_order_features.csv")

# ---- Step 2a: turn missingness into explicit signal, not silent imputation ----
df["order_never_delivered"] = df["delivery_days"].isnull().astype(int)
df["never_reviewed"] = df["review_score"].isnull().astype(int)

df["delivery_days"] = df["delivery_days"].fillna(df["delivery_days"].median())
df["days_early_vs_estimate"] = df["days_early_vs_estimate"].fillna(0)
df["review_score"] = df["review_score"].fillna(df["review_score"].median())
df["product_category"] = df["product_category"].fillna("unknown")
df["payment_type"] = df["payment_type"].fillna("unknown")

# drop the handful of rows with no order_value/num_items/payment info — genuine gaps, negligible count
df = df.dropna(subset=["order_value", "num_items", "payment_installments"])

# ---- Step 2b: bucket high-cardinality category into top N + "other" ----
top_categories = df["product_category"].value_counts().nlargest(15).index
df["product_category"] = df["product_category"].where(df["product_category"].isin(top_categories), "other")

# ---- Step 2c: one-hot encode categoricals ----
categorical_cols = ["customer_state", "product_category", "payment_type"]
df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

feature_cols = [c for c in df_encoded.columns if c not in
                ["customer_unique_id", "order_id", "order_purchase_timestamp", "became_repeat_buyer"]]
X = df_encoded[feature_cols]
y = df_encoded["became_repeat_buyer"]

print(f"Feature matrix: {X.shape[0]} rows, {X.shape[1]} features")
print(f"Positive class rate: {y.mean():.4f}")

# ---- Step 3: stratified train/test split ----
# Stratify is essential here — with only 3% positives, a random split could easily
# under- or over-represent them in the test set and give you a misleading score.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)
print(f"\nTrain: {X_train.shape[0]} rows ({y_train.mean():.4f} positive)")
print(f"Test:  {X_test.shape[0]} rows ({y_test.mean():.4f} positive)")

# scale numeric features for logistic regression
numeric_cols = ["delivery_days", "days_early_vs_estimate", "order_value", "num_items",
                 "payment_installments", "review_score"]
scaler = StandardScaler()
X_train_scaled = X_train.copy()
X_test_scaled = X_test.copy()
X_train_scaled[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
X_test_scaled[numeric_cols] = scaler.transform(X_test[numeric_cols])

# ---- Step 4: Baseline — Logistic Regression, class_weight='balanced' ----
# class_weight='balanced' matters a lot here: with 97/3 imbalance, an unweighted
# model can get 97% "accuracy" by just always predicting "no repeat" — completely useless.
# Balancing forces the model to actually try to separate the classes.
logreg = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
logreg.fit(X_train_scaled, y_train)
logreg_probs = logreg.predict_proba(X_test_scaled)[:, 1]
logreg_preds = logreg.predict(X_test_scaled)

print("\n" + "=" * 60)
print("LOGISTIC REGRESSION (baseline)")
print("=" * 60)
print(classification_report(y_test, logreg_preds, target_names=["no repeat", "repeat"]))
print(f"ROC-AUC: {roc_auc_score(y_test, logreg_probs):.4f}")
print("Confusion matrix:\n", confusion_matrix(y_test, logreg_preds))

# ---- Step 5: comparison model — Random Forest ----
rf = RandomForestClassifier(n_estimators=200, class_weight="balanced", max_depth=8, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
rf_probs = rf.predict_proba(X_test)[:, 1]
rf_preds = rf.predict(X_test)

print("\n" + "=" * 60)
print("RANDOM FOREST (comparison)")
print("=" * 60)
print(classification_report(y_test, rf_preds, target_names=["no repeat", "repeat"]))
print(f"ROC-AUC: {roc_auc_score(y_test, rf_probs):.4f}")
print("Confusion matrix:\n", confusion_matrix(y_test, rf_preds))

# ---- Step 6: feature importance from the Random Forest ----
importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop 10 features by importance (Random Forest):")
print(importances.head(10))

importances.head(15).to_csv("feature_importance.csv")
