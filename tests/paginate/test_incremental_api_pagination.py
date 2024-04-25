import datetime

from zdesk import Zendesk

days_ago = 60
start_time = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).timestamp()
incremental_api_page_size = 1000

def test_incremental_ticket_pagination(zd: Zendesk):
    response = zd.incremental_tickets_list(get_all_pages=True, cursor_pagination=False, start_time=start_time)
    time_pagination_tickets = response["tickets"]
    assert response["end_time"] > start_time
    assert response["end_of_stream"] is True
    assert len(time_pagination_tickets) > incremental_api_page_size

    response = zd.incremental_tickets_cursor_list(get_all_pages=True, cursor_pagination=False, start_time=start_time)
    cursor_pagination_tickets = response["tickets"]
    assert response["end_of_stream"] is True
    assert len(cursor_pagination_tickets) == len(time_pagination_tickets)
