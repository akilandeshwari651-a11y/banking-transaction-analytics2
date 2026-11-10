
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# Find the CSV file in the project data folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "transactions.csv")


def load_data():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError("transactions.csv was not found in the data folder")

    df = pd.read_csv(CSV_PATH)

    # Standardize column names
    df.columns = [column.strip().lower() for column in df.columns]

    return df


@app.route("/")
def home():
    return jsonify({
        "message": "BankSight Banking Analytics API is running",
        "status": "success"
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/dashboard")
def dashboard():
    try:
        df = load_data()

        amount_column = "amount"
        if amount_column not in df.columns:
            return jsonify({"error": "CSV must contain an amount column"}), 400

        df[amount_column] = pd.to_numeric(
            df[amount_column], errors="coerce"
        ).fillna(0)

        total_transactions = len(df)
        total_amount = float(df["amount"].sum())

        # Optional debit and credit totals
        if "type" in df.columns:
            transaction_type = df["type"].astype(str).str.lower()
            total_debit = float(
                df.loc[transaction_type == "debit", "amount"].sum()
            )
            total_credit = float(
                df.loc[transaction_type == "credit", "amount"].sum()
            )
        else:
            total_debit = 0
            total_credit = 0

        if "status" in df.columns:
            successful = int(
                df["status"].astype(str).str.lower().isin(
                    ["success", "successful", "completed"]
                ).sum()
            )
            pending = int(
                df["status"].astype(str).str.lower().isin(
                    ["pending", "review"]
                ).sum()
            )
        else:
            successful = 0
            pending = 0

        return jsonify({
            "total_transactions": total_transactions,
            "total_amount": round(total_amount, 2),
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "successful_transactions": successful,
            "pending_transactions": pending
        })

    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/transactions")
def transactions():
    try:
        df = load_data()

        search_text = request.args.get("search", "").strip().lower()

        if search_text:
            matching_columns = [
                column for column in
                ["transaction_id", "account_id", "type", "status", "channel"]
                if column in df.columns
            ]

            if matching_columns:
                mask = pd.Series(False, index=df.index)

                for column in matching_columns:
                    mask |= df[column].astype(str).str.lower().str.contains(
                        search_text, na=False
                    )

                df = df[mask]

        # Return a maximum of 200 rows
        records = df.head(200).fillna("").to_dict(orient="records")

        return jsonify({
            "count": len(records),
            "transactions": records
        })

    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/analytics/channels")
def channel_analytics():
    try:
        df = load_data()

        if "channel" not in df.columns or "amount" not in df.columns:
            return jsonify({
                "error": "CSV must contain channel and amount columns"
            }), 400

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        result = (
            df.groupby("channel")["amount"]
            .agg(["count", "sum"])
            .reset_index()
        )

        return jsonify(
            result.rename(columns={
                "channel": "channel",
                "count": "transactions",
                "sum": "total_amount"
            }).to_dict(orient="records")
        )

    except Exception as error:
        return jsonify({"error": str(error)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
