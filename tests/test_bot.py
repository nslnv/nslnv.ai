import bot
from telegram.helpers import escape_markdown


def test_build_order_card_escape():
    order = {
        "topic": "*bold* _italic_",
        "deadline": "01.01.2030",
        "guidelines": "Use > quotes",
        "files": [],
        "uniqueness": "100%",
        "budget": "1000$",
    }
    text = bot.build_order_card(order, username="user")
    expected_topic = escape_markdown(order["topic"], version=2)
    assert expected_topic in text
