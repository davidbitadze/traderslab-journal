import os
import streamlit as st


def generate_trade_analysis(
    trade_data: dict, sub_actions_df, opt_detailed: bool, opt_advice: bool
) -> tuple:
  """აგზავნის გარიგების მონაცემებს და სკრინშოტს AI-სთან,

  აბრუნებს (ai_analysis_text, scores_text)
  """
  pair = trade_data.get("Pair", "N/A")
  side = trade_data.get("Side", "N/A")

  # დინამიური ინსტრუქციები ტოგლების მიხედვით
  lacony_instruction = (
      "გააკეთე ვრცელი, დეტალური და ღრმა ანალიზი ყველა კომპონენტზე."
      if opt_detailed
      else "იყავი ლაკონური, მოკლე და კონკრეტული."
  )
  advice_instruction = (
      "აუცილებლად დაურთე პროფესიონალური ტრეიდერული რჩევა და სტრატეგიული რეკომენდაცია მომავლისთვის."
      if opt_advice
      else ""
  )

  system_prompt = f"""
    ინსტრუქცია AI-სთვის:
    გააანალიზე ეს გარიგება ({pair} - {side}).
    მკაცრი წესები:
    აკრძალულია ციტატების (Citations), წყაროების მითითების (Sources) და მისალმების გამოყენება.
    {lacony_instruction}
    {advice_instruction}
    ენა: პასუხი ყოველთვის დააბრუნე იმავე ენაზე, რა ენაზეც არის მოწოდებული სტუდენტის აღწერა.

    შენ ხარ პროფესიონალი ტრეიდერ-მენტორი. შენი ამოცანაა შეაფასო სტუდენტის გარიგება ობიექტური რეალობიდან გამომდინარე.
    
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
    [SCORES: 2,2,2,2,2]
    """

  try:
    # --- აქ მოხდება OpenAI / Claude API-ს რეალური გამოძახება ---
    # მაგალითი:
    # response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": system_prompt}])
    # analysis_text = response.choices[0].message.content

    # დინამიური საპილოტე პასუხი ტოგლების სტატუსის მიხედვით:
    detail_text = (
        " ვრცელი და ღრმა სტრატეგიული ანალიზით."
        if opt_detailed
        else " სტანდარტული ფორმატით."
    )
    advice_text = (
        "\n\n💡 **AI რჩევა**: ყურადღება მიაქციე მოცულობის დინამიკას გასვლის მომენტში,"
        " რომ თავიდან აირიდო ნაადრევი დახურვა."
        if opt_advice
        else ""
    )

    mock_analysis = (
        f"ანალიზი: გარიგება {pair} ({side}) წარმატებით იქნა გადამოწმებული.{detail_text}"
        " დონეები და ტრიგერები ობიექტურად ემთხვევა სკრინშოტს.\n\nსისტემური"
        " მატრიცა:\n📍 დონე: 2/2\n🧩 პატერნი: 2/2\n⚡ ტრიგერი: 2/2\n📊"
        " მოცულობა/ფონი: 2/2\n🛡️ მართვა: 2/2\n\n🏆 ობიექტური ქულა:"
        f" 10/10{advice_text}"
    )
    mock_scores = "SCORES:2,2,2,2,2"

    return mock_analysis, mock_scores

  except Exception as e:
    return f"AI შეცდომა: {str(e)}", ""
