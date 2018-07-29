from signal import signal, SIGPIPE, SIG_DFL
import pstats
import sys

# Don't freak out when `head` stops reading data in `profile.sh`.
signal(SIGPIPE, SIG_DFL)

stats = pstats.Stats(sys.argv[-1])
stats.sort_stats("cumtime").print_stats()
