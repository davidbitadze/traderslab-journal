import os
import streamlit as st
# საიდანაც გამოვიძახებთ API-ს (მაგ. OpenAI კლიენტი)
# from openai import OpenAI


def generate_trade_analysis(
    trade_data: dict, sub_actions_df, lacony: str, advice: str
) -> tuple:
  """აგზავნის გარიგების მონაცემებს და სკრინშოტს AI-სთან,

  აბრუნებს (ai_analysis_text, scores_text)
  """
  pair = trade_data.get("Pair", "N/A")
  side = trade_data.get("Side", "N/A")
  screenshot_url = trade_data.get("Screenshot", "")

  # შენი ორიგინალური პრომპტი Glide-დან
  system_prompt = f"""
    ინსტრუქცია AI-სთვის:
    გააანალიზე ეს გარიგება ({pair} - {side}).
    მკაცრი წესები:
    აკრძალულია ციტატების (Citations), წყაროების მითითების (Sources) და მისალმების გამოყენება.
    იყოს {lacony}, {advice}. ენა: პასუხი ყოველთვის დააბრუნე იმავე ენაზე, რა ენაზეც არის მოწოდებული სტუდენტის აღწერა.

    შენ ხარ პროფესიონალი ტრეიდერ-მენტორი. შენი ამოცანაა შეაფასო სტუდენტის გარიგება.
    
    ფორმატი:
    ანალიზი: [დაადასტურე, რამდენად ემთხვევა სტუდენტის აღწერა რეალობას].

    სისტემური მატრიცა:
    📍 დონე: [0-2] - [რეალობა vs აღწერა]
    🧩 პატერნი: [0-2] - [რეალობა vs აღწერა]
    ⚡ ტრიგერი: [0-2] - [რეალობა vs აღწერა]
    📊 მოცულობა/ფონი: [0-2] - [რეალობა vs აღწერა]
    🛡️ მართვა: [0-2] - [რამდენად ლოგიკურია ქმედებები]

    🏆 ობიექტური ქულა: [X/10]

    ტექნიკური ბლოკი (სტატისტიკისთვის):
    [SCORES: {pair},{side}]
    """

  try:
    # --- აქ მოხდება რეალური OpenAI / Anthropic API-ს გამოძახება ---
    # client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))
    # response = client.chat.completions.create(...)

    # ტესტური / საპილოტე პასუხი სანამ API გასაღებს ჩასვამ:
    mock_analysis = (
        f"ანალიზი: გარიგება {pair} ({side}) წარმატებით იქნა გადამოწმებული."
        " დონეები და ტრიგერები ობიექტურად ემთხვევა მოწოდებულ სკრინშოტს.\n\nსისტემური"
        " მატრიცა:\n📍 დონე: 2/2\n🧩 პატერნი: 2/2\n⚡ ტრიგერი: 2/2\n📊"
        " მოცულობა/ფონი: 2/2\n🛡️ მართვა: 2/2\n\n🏆 ობიექტური ქულა: 10/10"
    )
    mock_scores = "SCORES:2,2,2,2,2"

    return mock_analysis, mock_scores

  except Exception as e:
    return f"AI შეცდომა: {str(e)}", ""
