"""Pure KST/cycle/availability rules shared by explicit and automatic scheduling."""
from datetime import datetime,time,timedelta,timezone
from app.raids.service import cycle,KST
from app.game_accounts.support import fail

TICK=timedelta(minutes=5)


def minute_aligned(stamp):
    return stamp.tzinfo is not None and stamp.utcoffset()==timedelta(0) and stamp.second==0 and stamp.microsecond==0


def aligned(stamp):
    return minute_aligned(stamp) and stamp.minute%5==0


def interval(start,end,cycle_key,*,floor=None,current=None,minute_precision=False):
    # Explicit beta departures opt in; default boundaries and all durations keep the five-minute policy.
    boundary=minute_aligned if minute_precision else aligned
    if (not boundary(start) or not boundary(end) or not timedelta(0)<end-start<=timedelta(days=1)
            or (end-start)%TICK!=timedelta(0)):fail('INVALID_REQUEST',400)
    bounds=cycle(start)
    if bounds.cycle_key!=cycle_key or end>bounds.ends_at:fail('CYCLE_CHANGED')
    maintenance_start=bounds.starts_at;maintenance_end=maintenance_start+timedelta(hours=4)
    if start<maintenance_end and end>maintenance_start:fail('MAINTENANCE_WINDOW')
    if floor is not None and start<floor:fail('SCHEDULE_BEFORE_FLOOR')
    if current is not None and start<current:fail('SCHEDULE_IN_PAST')


def local_start(cycle_key,weekday,clock):
    from datetime import date
    base=date.fromisoformat(cycle_key)
    day=base+timedelta(days=(weekday-3)%7)
    hour,minute=map(int,clock.split(':'))
    result=datetime.combine(day,time(hour,minute),KST).astimezone(timezone.utc)
    if cycle(result).cycle_key!=cycle_key:fail('CYCLE_CHANGED')
    return result


def ceil_tick(value):
    result=value.replace(second=0,microsecond=0)
    if result<value:result+=timedelta(minutes=1)
    return result+timedelta(minutes=(-result.minute)%5)


def covered(start,end,normalized):
    """Weekly Monday coordinates; end can cross Sunday and must be fully covered."""
    local=start.astimezone(KST)
    first=local.weekday()*1440+local.hour*60+local.minute
    minutes=int((end-start).total_seconds()/60)
    pieces=[(first,min(first+minutes,10080))]
    if first+minutes>10080:pieces.append((0,first+minutes-10080))
    return all(any(r['start_minute']<=a and r['end_minute']>=b for r in normalized) for a,b in pieces)


def quorum(count):
    if not 1<=count<=8:fail('PROPOSAL_TARGET_UNAVAILABLE')
    return 1 if count==1 else max(2,(count+1)//2)
