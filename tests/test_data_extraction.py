from src.data_extraction import extract_emails, extract_title, transform_emails


def test_extract_title_from_html():
    html = "<html><head><title>My Example Page</title></head></html>"

    assert extract_title(html) == "My Example Page"


def test_extract_title_handles_whitespace_and_multiple_lines():
    html = """
    <html>
        <head>
            <title>
                My Example Page
            </title>
        </head>
    </html>
    """

    assert extract_title(html) == "My Example Page"


def test_extract_title_decodes_html_entities():
    assert extract_title("<title>Fish &amp; Chips</title>") == "Fish & Chips"


def test_extract_title_returns_none_when_missing():
    html = "<html><body><p>No title here</p></body></html>"

    assert extract_title(html) is None


def test_extract_emails_from_html():
    html = """
    <p>Contact alice@example.com for help.</p>
    <p>Or contact bob@example.org.</p>
    """

    assert extract_emails(html) == [
        "alice@example.com",
        "bob@example.org",
    ]


def test_extract_emails_returns_empty_list_when_none_found():
    html = "<p>No email address is available.</p>"

    assert extract_emails(html) == []


def test_transform_emails_normalizes_and_removes_duplicates():
    emails = [
        " ALICE@example.com ",
        "bob@example.org",
        "alice@EXAMPLE.com",
    ]

    assert transform_emails(emails) == [
        "alice@example.com",
        "bob@example.org",
    ]


def test_transform_emails_ignores_invalid_entries():
    emails = [
        "alice@example.com",
        "not-an-email",
        "",
        "bob@example.org",
    ]

    assert transform_emails(emails) == [
        "alice@example.com",
        "bob@example.org",
    ]


def test_transform_emails_handles_empty_input():
    assert transform_emails([]) == []
