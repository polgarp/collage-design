# Trigger evals

`trigger-evals.json` tests the skill's **`description`** field — the line that decides whether
Claude reaches for this skill at all. 24 cases, 12 positive and 12 negative:

```json
{"query": "make a gig poster where a saint's engraving is torn open and a satellite
           photo bleeds through underneath", "should_trigger": true}

{"query": "build me a moodboard of interior design references — just arrange a grid
           of inspiration images", "should_trigger": false}
```

Half the positives deliberately avoid the word *collage*. The negatives are all near misses that
share its vocabulary but need a different tool — moodboard grid, background removal, panorama
stitch, generative art, logo — because over-firing costs 100k+ tokens on the wrong job.

## Running them

No bundled harness. For each `query`, start a session with the skill installed **alongside your
other skills** (triggering is competitive — `canvas-design` and image-editing skills contend
here), record whether it was invoked, and compare against `should_trigger`. Judge invocation
only, not output quality.

A false negative means adding vocabulary to the description. A false positive means sharpening
its "not for…" clause. If you fork and change the skill's *scope*, rewrite these cases first,
then the description, then check they agree.
