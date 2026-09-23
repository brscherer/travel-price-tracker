from travel_tracker.promos.rss import parse_feed

_SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Sample Deal Blog</title>
    <item>
        <title>Passagem para Porto Alegre com desconto</title>
        <link>https://example.com/poa-deal</link>
        <guid>https://example.com/poa-deal</guid>
        <description>Aproveite passagens baratas saindo de Porto Alegre.</description>
        <pubDate>Mon, 01 Dec 2025 12:00:00 GMT</pubDate>
    </item>
    <item>
        <title>Bonus de milhas Livelo para Smiles</title>
        <link>https://example.com/bonus-deal</link>
        <guid>https://example.com/bonus-deal</guid>
        <description>Bonus de 100% na transferencia de pontos.</description>
        <pubDate>Tue, 02 Dec 2025 12:00:00 GMT</pubDate>
    </item>
</channel>
</rss>
"""


def test_parse_feed_extracts_items():
    items = parse_feed(_SAMPLE_FEED, "sample_blog")

    assert len(items) == 2
    assert items[0].source == "sample_blog"
    assert items[0].item_id == "https://example.com/poa-deal"
    assert items[0].title == "Passagem para Porto Alegre com desconto"
    assert items[0].link == "https://example.com/poa-deal"
    assert "Porto Alegre" in items[0].summary


def test_parse_feed_empty_body_returns_no_items():
    assert parse_feed(b"<rss><channel></channel></rss>", "sample_blog") == []
