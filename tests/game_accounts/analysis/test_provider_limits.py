"""Shared server-key outage and quota policy; synthetic upstream metadata only."""
from datetime import datetime, timedelta, timezone
import pytest
from app.game_accounts.provider_io import rate_limits

AT=datetime(2026,11,16,tzinfo=timezone.utc)

@pytest.mark.parametrize('reset',[None,'x','-1','0',str(int(AT.timestamp())-1),str(int(AT.timestamp())+301),'9'*30])
def test_unusable_reset_uses_bounded_fallback(reset):
    assert rate_limits.observation(429,{'X-RateLimit-Reset':reset},AT)==AT+timedelta(seconds=60)


def test_remaining_zero_keeps_current_success_but_stops_next_fetch():
    assert rate_limits.observation(200,{'X-RateLimit-Remaining':'0'},AT)==AT+timedelta(seconds=60)
    assert rate_limits.observation(200,{'X-RateLimit-Remaining':'1'},AT) is None
    assert rate_limits.observation(200,{'X-RateLimit-Remaining':'bad'},AT) is None


def test_reset_and_retry_after_take_later_deadline():
    headers={'X-RateLimit-Reset':str(int(AT.timestamp())+80),'Retry-After':'100'}
    assert rate_limits.observation(429,headers,AT)==AT+timedelta(seconds=100)


@pytest.mark.parametrize('status,seconds',[(401,60),(403,60),(415,60),(500,30),(502,30),(503,30),(504,30),(None,30)])
def test_project_outage_intervals_are_explicit_and_do_not_imply_maintenance(status,seconds):
    assert rate_limits.observation(status,{},AT)==AT+timedelta(seconds=seconds)


def test_retry_after_http_date_and_bad_values_are_bounded():
    from email.utils import format_datetime
    assert rate_limits.observation(503,{'Retry-After':format_datetime(AT+timedelta(seconds=90))},AT)==AT+timedelta(seconds=90)
    for value in ('bad','99999999','-1',format_datetime(AT+timedelta(seconds=301)),format_datetime(AT-timedelta(seconds=1))):
        assert rate_limits.observation(503,{'Retry-After':value},AT)==AT+timedelta(seconds=30)
