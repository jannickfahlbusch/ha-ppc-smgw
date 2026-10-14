DEFAULT_MODEL = "LTE Smart Meter Gateway"
DEFAULT_NAME = "PPC SMGW"
DEFAULT_URL = "https://192.168.1.200/cgi-bin/hanservice.cgi"
MANUFACTURER = "Power Plus Communications AG"

# Upper bounds for reading multiple meters per poll. Every meter costs one
# extra request against the gateway, which locks down when polled too often,
# and the meter list comes from the gateway itself, so both are capped.
MAX_METERS_PER_POLL = 4
METER_READ_TIME_BUDGET = 60  # seconds for all meter reads of one poll
