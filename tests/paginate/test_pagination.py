import pytest

from zdesk import Zendesk

@pytest.fixture(scope="module", autouse=True)
def expected_ticket_count(zd: Zendesk):
    response = zd.tickets_count_list()
    count = response["count"]["value"]
    assert count >= 100, "Please create at least 100 tickets for this test to run"
    return count


def test_ticket_pagination(zd: Zendesk, expected_ticket_count: int):
    response = zd.tickets_list(per_page=100, get_all_pages=True)
    tickets = response["tickets"]
    assert len(tickets) == expected_ticket_count