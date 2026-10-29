# Mouse audit: ieee_blog_bots

- Source shards: 1
- Rows: 50795
- Sessions: 156
- Subjects: 156
- Windows: 1113 (10 s, 5 s hop, at least 20 moves)

## Counts

| Dimension | Values |
|---|---|
| label | `{"0": 28339, "1": 22456}` |
| bot_type | `{"fallible": 10268, "human": 28339, "humanish": 3024, "mimic": 8986, "naive": 178}` |
| domain | `{"blog_platform": 50795}` |
| event | `{"click": 1438, "move": 42913, "scroll": 6444}` |
| coord_space | `{"pixels": 50795}` |
| touchscreen | `{"False": 50795}` |

## Numeric summaries

| Field | Summary |
|---|---|
| t_ms | `{"count": 50795, "max": 247686.0, "mean": 40531.75001476523, "min": 9.0, "p50": 26870.0, "p95": 82238.0}` |
| x | `{"count": 44351, "max": 1535.0, "mean": 666.8943654032604, "min": 0.0, "p50": 683.0, "p95": 1178.0}` |
| y | `{"count": 44351, "max": 766.0, "mean": 324.7295213185723, "min": 0.0, "p50": 302.0, "p95": 523.0}` |
| dt_ms | `{"count": 41000, "max": 97765.0, "mean": 113.58231707317073, "min": 10.0, "p50": 17.0, "p95": 100.0}` |
| events_per_second | `{"count": 156, "max": 42.74611398963731, "mean": 6.432735417741053, "min": 0.5372351351778406, "p50": 4.852398167301409, "p95": 16.385801362495517}` |

## Missing values

| Field | Count | Rate |
|---|---:|---:|
| screen_h | 50795 | 1.000000 |
| screen_w | 50795 | 1.000000 |
| x | 6444 | 0.126863 |
| y | 6444 | 0.126863 |
