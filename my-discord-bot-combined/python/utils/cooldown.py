import datetime

def check_cooldown(last_used, cooldown_seconds):
    if last_used is None:
        return True, None
    last_dt = datetime.datetime.fromisoformat(last_used)
    now = datetime.datetime.now()
    diff = (now - last_dt).total_seconds()
    if diff >= cooldown_seconds:
        return True, None
    return False, cooldown_seconds - diff
