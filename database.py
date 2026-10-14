# საწყისი დეპოზიტის/ტრანზაქციების წამოღება ბაზიდან


def fetch_balance_transactions():
  """ბრუნავს ტრანზაქციების DataFrame-ს ან სიას."""
  try:
    supabase = get_supabase_client()
    response = supabase.table("balance_transactions").select("*").execute()
    return (
        pd.DataFrame(response.data)
        if response.data
        else pd.DataFrame(
            columns=["Transaction ID", "Date", "Amount", "Description"]
        )
    )
  except Exception as e:
    return pd.DataFrame(
        columns=["Transaction ID", "Date", "Amount", "Description"]
    )


def add_balance_transaction(data):
  """ახალი ტრანზაქციის (შევსება/გამოტანა) დამატება ბაზაში."""
  try:
    supabase = get_supabase_client()
    supabase.table("balance_transactions").insert(data).execute()
    return True
  except Exception as e:
    st.error(f"შეცდომა ბაზაში ჩაწერისას: {e}")
    return False


def delete_balance_transaction(txn_id):
  """ტრანზაქციის წაშლა ID-ის მიხედვით."""
  try:
    supabase = get_supabase_client()
    supabase.table("balance_transactions").delete().eq(
        "Transaction ID", txn_id
    ).execute()
    return True
  except Exception as e:
    return False
