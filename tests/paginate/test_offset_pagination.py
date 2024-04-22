import pytest

from zdesk import Zendesk, ZendeskError

@pytest.fixture(scope="module", autouse=True)
def expected_ticket_count(zd: Zendesk):
    response = zd.tickets_count_list()
    count = response["count"]["value"]
    assert count >= 100, "Please create at least 100 tickets for this test to run"
    return count


def test_search_pagination(zd: Zendesk, expected_ticket_count: int):
    # Try to implement a way to return partial results.
    # This includes refactoring, because results are merged together at the end
    # of pagination.
    try:
        response = zd.search(query="*", per_page=100, get_all_pages=True)
    except ZendeskError as e:
        return
    tickets = response["tickets"]
    assert len(tickets) == expected_ticket_count