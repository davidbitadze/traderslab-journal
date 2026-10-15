import uuid
from datetime import datetime
from database import delete_trade, insert_trade, update_trade
import pandas as pd
import streamlit as st
from utils.formulas import calculate_trade_pnl

# 🪟 Streamlit-ის ოფიციალური ოვერლეი ფანჯარა (Dialog) დეტალებისა და მართვისთვის
@st.dialog("🔍 გარიგების დეტალები და მართვა")
def show_trade_details_dialog(trade, df):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_price = trade.get("Entry Price", 0)

  is_finalized = trade.get("Finalized", False)
  if isinstance(is_finalized, str):
    is_finalized = is_finalized.lower() == "true"

  sub_actions = df[df["Parent Trade ID"] == trade_id]

  st.markdown(f"### {pair} — **{side}**")
  st.divider()

  # 1. არსებული ისტორია წაშლისა და ედიტირების ღილაკებით
  if not sub_actions.empty:
    st.markdown("**📋 ეტაპების ისტორია:**")
    for _, sub in sub_actions.iterrows():
      sub_id = sub.get("Trade ID")
      col_h1, col_h2, col_h3 = st.columns([7, 1, 1])
      with col_h1:
        st.info(
            f"• **{sub.get('ActionType')}** | ფასი: {sub.get('Entry Price')} |"
            f" მოც.: {sub.get('Qty')} | დრო: {sub.get('Entry Date')}"
        )
      with col_h2:
        if st.button("✏️", key=f"edit_sub_{sub_id}", help="ამ ეტაპის ჩასწორება"):
          st.session_state["active_edit_sub"] = sub_id
      with col_h3:
        if st.button("🗑️", key=f"del_sub_{sub_id}", help="ამ ეტაპის წაშლა"):
          if delete_trade(sub_id):
            st.toast("ჩანაწერი წაიშალა!", icon="🗑️")
            st.rerun()

      # თუ ზუსტად ამ სუბ-ჩანაწერის ედიტირებაა არჩეული
      if st.session_state.get("active_edit_sub") == sub_id:
        with st.form(f"form_edit_sub_inline_{sub_id}"):
          st.markdown(f"**✏️ ჩასწორება: {sub.get('ActionType')}**")
          is_start_row = "Start Row" in str(sub.get("ActionType", ""))

          edit_price = st.number_input(
              "ფასი",
              value=float(sub.get("Entry Price", 1.0850))
              if str(sub.get("Entry Price", "1.0850"))
              .replace(".", "", 1)
              .isdigit()
              else 1.0850,
              format="%.5f",
          )
          edit_qty = st.number_input(
              "მოცულობა",
              value=float(sub.get("Qty", 1000.0))
              if str(sub.get("Qty", "1000")).replace(".", "", 1).isdigit()
              else 1000.0,
              step=100.0,
          )

          edit_risk = 10.0
          if is_start_row:
            edit_risk = st.number_input(
                "რისკი დოლარში (Risk $)",
                value=float(sub.get("Risk ($)", 10.0))
                if str(sub.get("Risk ($)", "10")).replace(".", "", 1).isdigit()
                else 10.0,
                step=1.0,
            )

          edit_date = st.text_input(
              "თარიღი და დრო", value=sub.get("Entry Date", "")
          )

          
          col_es1, col_es2 = st.columns(2)
          with col_es1:
            if st.form_submit_button("💾 შენახვა", use_container_width=True):
              update_data = {
                  "Entry Price": str(edit_price),
                  "Qty": str(edit_qty),
                  "Entry Date": edit_date,
              }
              if is_start_row:
                update_data["Risk ($)"] = str(edit_risk)

                if update_trade(sub_id, update_data):
                # ამოვიღოთ ზუსტად მთავარი გარიგების ID მიმდინარე დიალოგიდან
                parent_main_id = trade.get("Trade ID") or sub.get("Parent Trade ID")
                
                # ვკრიბავთ ამ მთავარი გარიგების ყველა ეტაპს
                all_subs = df[(df["Parent Trade ID"] == parent_main_id) | (df["Trade ID"] == parent_main_id)]
                
                # ვპოვოთ მთავარი რიგი ბაზის მონაცემებიდან
                main_row = df[df["Trade ID"] == parent_main_id]
                entry_p = float(entry_price or 0)
                risk_v = 5.85
                if not main_row.empty:
                  entry_p = float(main_row.iloc[0].get("Entry Price", 0) or 0)
                  risk_v = float(main_row.iloc[0].get("Risk ($)", 5.85) or 5.85)

                total_pnl = 0.0
                for _, ex in all_subs.iterrows():
                  if "Exit" in str(ex.get("ActionType", "")):
                    ex_p = edit_price if ex.get("Trade ID") == sub_id else float(ex.get("Entry Price", entry_p) or entry_p)
                    total_pnl += calculate_trade_pnl(entry_p, ex_p, risk_v, side)

                # ვწერთ Net P/L-ს პირდაპირ მთავარ გარიგებაზე
                update_trade(parent_main_id, {"Net P/L": str(round(total_pnl, 2))})

                st.success("წარმატებით განახლდა!")
                st.session_state["active_edit_sub"] = None
                st.rerun()
          
          with col_es2:
            if st.form_submit_button("❌ გაუქმება", use_container_width=True):
              st.session_state["active_edit_sub"] = None
              st.rerun()
  else:
    st.caption("ამ გარიგებაზე დამატებითი ეტაპები ჯერ არ არის.")

  st.markdown("---")

  # 2. ახალი ეტაპის დამატება მოთავსებულია Expander-ში
  with st.expander("➕ ახალი ეტაპის დამატება"):
    sub_action_type = st.selectbox(
        "მოქმედების ტიპი",
        [
            "Full Exit (გამოსვლა)",
            "Partial Exit (ნაწილობრივ გამოსვლა)",
            "Scale In (დამატება)",
        ],
        key=f"dialog_act_{trade_id}",
    )

    with st.form(f"form_sub_dialog_{trade_id}"):
      col_f1, col_f2 = st.columns(2)
      with col_f1:
        default_sub_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sub_date = st.text_input(
            "თარიღი და დრო",
            value=default_sub_time,
            key=f"dialog_date_{trade_id}",
        )
        sub_price = st.number_input(
            "ფასი",
            value=float(entry_price)
            if str(entry_price).replace(".", "", 1).isdigit()
            else 1.0850,
            format="%.5f",
            key=f"dialog_price_{trade_id}",
        )
      with col_f2:
        sub_qty = st.number_input(
            "მოცულობა", value=1000.0, step=100.0, key=f"dialog_qty_{trade_id}"
        )

      sub_desc = st.text_input(
          "შენიშვნა / კომენტარი", key=f"dialog_desc_{trade_id}"
      )
      sub_screenshot = st.file_uploader(
          "სკრინშოტი (დადარებისთვის)",
          type=["png", "jpg", "jpeg"],
          key=f"dialog_file_{trade_id}",
      )

      col_sub_btn1, col_sub_btn2 = st.columns(2)
      with col_sub_btn1:
        submitted = st.form_submit_button(
            "💾 შენახვა", use_container_width=True
        )
      with col_sub_btn2:
        cancelled = st.form_submit_button(
            "❌ გაუქმება", use_container_width=True
        )
      if cancelled:
        st.rerun()

      if submitted:
        screenshot_name = (
            sub_screenshot.name if sub_screenshot else "No Screenshot"
        )
        child_trade_data = {
            "Trade ID": str(uuid.uuid4()),
            "Parent Trade ID": trade_id,
            "Entry Date": sub_date,
            "Pair": pair,
            "Side": side,
            "Entry Price": str(sub_price),
            "Qty": str(sub_qty),
            "ActionType": sub_action_type,
            "Description": sub_desc,
            "Screenshot": screenshot_name,
        }
        if insert_trade(child_trade_data):
          entry_p = float(entry_price or 0)
          risk_v = float(trade.get("Risk ($)", 5.85) or 5.85)

          all_exits_list = []
          for _, ex in sub_actions.iterrows():
            if "Exit" in str(ex.get("ActionType", "")):
              all_exits_list.append(ex)
          if "Exit" in str(sub_action_type):
            all_exits_list.append(child_trade_data)

          total_pnl = 0.0
          if all_exits_list:
            for ex in all_exits_list:
              ex_p = float(ex.get("Entry Price", entry_p) or entry_p)
              total_pnl += calculate_trade_pnl(entry_p, ex_p, risk_v, side)

          update_trade(trade_id, {"Net P/L": str(round(total_pnl, 2))})

          st.success("წარმატებით დაემატა!")
          st.rerun()
# ქოლბექი ტოიგლის ცვლილებისთვის
def handle_toggle_change(t_id):
  new_val = st.session_state.get(f"toggle_fin_{t_id}", False)

  # ვწერთ ბაზაში Finalized სტატუსს
  update_trade(t_id, {"Finalized": str(new_val)})

def render_trade_card(trade, df):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_date = trade.get("Entry Date", "N/A")
  entry_price = trade.get("Entry Price", 0)
  formation = trade.get("Formation", "N/A")
  risk_val = trade.get("Risk ($)", 5.85)
  screenshot = trade.get("Screenshot", "No Screenshot")

  is_finalized = trade.get("Finalized", False)
  if isinstance(is_finalized, str):
    is_finalized = is_finalized.lower() == "true"

  sub_actions = df[df["Parent Trade ID"] == trade_id]
  exit_price = entry_price

  exits = sub_actions[
      sub_actions["ActionType"].str.contains("Exit", case=False, na=False)
  ]
  if not exits.empty:
    exit_price = exits.iloc[-1].get("Entry Price", entry_price)
  else:
    if is_finalized:
      exit_price = entry_price

  pnl = calculate_trade_pnl(entry_price, exit_price, risk_val, side)
  status_icon = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")

  state_key = f"mode_{trade_id}"
  current_mode = st.session_state.get(state_key, None)

  # სუპერ-კომპაქტური ჰორიზონტალური ბარათი სტატუსის გადამრთველით
  with st.container(border=True):
    col_img, col_info, col_toggle, col_menu = st.columns([0.6, 5.4, 3.0, 1.0])

    with col_img:
      st.markdown(
          "🖼️" if screenshot != "No Screenshot" else "📁",
          help="სკრინშოტი არსებობს",
      )

    with col_info:
      st.markdown(
          f"<span style='font-size: 1.1rem;'>{status_icon} <b>{pair}</b></span>"
          f" &nbsp; <code style='font-size: 0.85rem;'>{side}</code> &nbsp;"
          f" <span style='font-size: 1.1rem;'><b>{pnl:+.2f}$</b></span>",
          unsafe_allow_html=True,
      )
      st.caption(
          f"📅 {entry_date} &nbsp;•&nbsp; 🏷️ {formation} &nbsp;•&nbsp; 💵 შესვლა:"
          f" {entry_price}"
      )

    with col_toggle:
      current_toggle_state = st.session_state.get(
          f"toggle_fin_{trade_id}", is_finalized
      )
      toggle_label = "დასრულებული" if current_toggle_state else "მიმდინარე"

      # ერთადერთი სწორი ტოიგლი ქოლბექით
      st.toggle(
          toggle_label,
          value=is_finalized,
          key=f"toggle_fin_{trade_id}",
          on_change=handle_toggle_change,
          args=(trade_id,),
      )

      # თუ დასრულებულზე გადაიყვანა და Exit არ აქვს, ვატყობინებთ
      if current_toggle_state and exits.empty:
        st.toast(
            f"⚠️{pair} გარიგება დასრულებულია, თუმცა გამოსვლის (Exit) დეტალები არ არის გაწერილი."
            "\nშესაბამისად, მითითებულია (PnL = 0$)",
            icon="ℹ️",
        )

    with col_menu:
      with st.popover("⋯"):
        st.write(f"**მართვა: {pair}**")

        if st.button("🔍 დეტალები / ჩასწორება", key=f"det_menu_{trade_id}"):
          show_trade_details_dialog(trade, df)

        if st.button("🗑️ გარიგების წაშლა", key=f"del_menu_{trade_id}"):
          st.session_state[state_key] = "delete"
          st.rerun()

    if current_mode == "delete":
      st.divider()
      st.error(
          "⚠️ ნამდვილად გსურთ გარიგებისა და მისი ისტორიის წაშლა? მონაცემები"
          " ვეღარ აღდგება!"
      )
      col_d1, col_d2 = st.columns(2)
      with col_d1:
        if st.button(
            "დიახ, წაშლა", key=f"conf_del_{trade_id}", use_container_width=True
        ):
          if delete_trade(trade_id):
            st.success("წაიშალა!")
            del st.session_state[state_key]
            st.rerun()
      with col_d2:
        if st.button(
            "გაუქმება", key=f"canc_del_{trade_id}", use_container_width=True
        ):
          del st.session_state[state_key]
          st.rerun()
