# Profiling


# Ressources / Links

For mp flamecharts:
- https://viztracer.readthedocs.io/en/stable/index.html
- https://github.com/gaogaotiantian/vizplugins
To then aggregate: (TODO: check if that's correct)
durations in nano seconds (ie divide by 1000 for ms)
```SELECT ts, SUM(dur), name FROM slice WHERE name LIKE '_log%'```


Cool tools, no native th/mp support unfrtunately
- https://www.roguelynn.com/words/asyncio-profiling/
- https://jiffyclub.github.io/snakeviz/