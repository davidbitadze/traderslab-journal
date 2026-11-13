"""მთავარი ბაზის ფასადატორი (Facade), რომელიც აერთიანებს ქვემოდულებს."""

# იმპორტები ქვემოდულებიდან
from utils.db_trades import (
    fetch_trades,
    insert_trade,
    update_trade,
    update_net_pnl_batch,
    delete_trade,
    invalidate_trades,
)
from utils.db_settings import (
    fetch_settings,
    add_setting_item,
    delete_setting_item,
    update_setting_item,
)
from utils.db_balance import (
    fetch_balance_transactions,
    add_balance_transaction,
    delete_balance_transaction,
)
from utils.db_preferences import (
    fetch_user_preferences,
    upsert_user_preferences,
    update_user_preference_fields,
    ensure_user_preferences,
    fetch_my_staff_role,
)

# დამხმარეები
from utils.db_core import call_rpc, get_data_client, _uid
from utils.db_storage import thumb_url, delete_screenshot, upload_screenshot
