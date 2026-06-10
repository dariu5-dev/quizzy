from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate limiter — keyed by the requester's IP address.
# Import this instance in each router; the app registers it in main.py.
limiter = Limiter(key_func=get_remote_address)
