import psycopg2
import pandas as pd

conn = psycopg2.connect(dbname="olist_project", user="postgres", password="olist", host="localhost")

with open("feature_query.sql") as f:
    query = f.read()

df = pd.read_sql(query, conn)
conn.close()

print("Shape:", df.shape)
print("\nClass balance (became_repeat_buyer):")
print(df["became_repeat_buyer"].value_counts(normalize=True).round(4))
print("\nMissing values per column:")
print(df.isnull().sum())
print("\nFirst 5 rows:")
print(df.head())

df.to_csv("first_order_features.csv", index=False)
print("\nSaved to first_order_features.csv")
