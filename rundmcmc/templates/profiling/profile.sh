#!/bin/bash

# Shoutout: https://stackoverflow.com/a/12187944/6670539
name=out
if [[ -e $name.pstats ]] ; then
    i=0
    while [[ -e $name-$i.pstats ]] ; do
        let i++
    done
    name=$name-$i
fi

# Set the hash seed for deterministic profiling.
PYTHONHASHSEED=0 python3 -m cProfile -o "$name.pstats" template_profile.py 10000
python3 summarize_stats.py "$name.pstats" | tee "$name.txt" | head -n 30

# gprof2dot is a dependency; should be installable through pip.
gprof2dot -f pstats "$name.pstats" | dot -Tpdf -o "$name.pdf"

# Replace "zathura" with your favorite PDF viewer, or remove the line
# completely if you want to open the files manually.
zathura "$name.pdf"
