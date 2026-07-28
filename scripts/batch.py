#!/usr/bin/env python3
"""
batch.py — manifest + parallel execution, shared by cut.py and treat.py.

WHY THIS EXISTS

Stage A is embarrassingly parallel and used to run strictly serially, one process per
fragment per operation. A 244-fragment piece is ~1,000 Python interpreter startups, and for
the 300-500 px images a deep archive pull actually yields, the STARTUP costs more than the
pixels. Two compounding wins, both here:

  * a manifest amortizes interpreter startup across every fragment in one process
  * --jobs N uses the other cores

DETERMINISM

Results cannot depend on scheduling order, because the seed is per-item rather than per-run:
every fragment's `--seed` is fixed by the manifest (or inherited from the top-level flags)
before any work starts, and each item builds its own `np.random.default_rng(seed)`. Nothing
is shared between items. `--jobs 1` and `--jobs 8` produce byte-identical output, and
`scripts/check_batch.sh` asserts exactly that.

MANIFEST FORMAT

One item per line, spelled like the command line it replaces — because that is how a build
script already thinks about these, and it keeps a manifest greppable and diffable:

    fragments/a.jpg  work/a.png
    fragments/b.jpg  work/b.png  --seed 12
    fragments/c.jpg  work/c.png  --seed 13 --sides bottom

Blank lines and `#` comments are skipped. Every line inherits the flags given on the
top-level invocation and may override any of them, so the common case stays short:

    cut.py --style torn --seed 7 --jobs 8 --manifest cuts.txt

A per-item `--seed` is what you want when fragments must differ (a tear recut per fragment);
inheriting one shared seed is what you want when they must match (the reconciling treatment).
Both spellings are one line apart, which is the point.
"""
import importlib, os, shlex, sys
from concurrent.futures import ProcessPoolExecutor

def add_args(ap):
    """Attach the batch flags to a tool's parser."""
    ap.add_argument("--manifest", help="file of items, one per line: IN OUT [per-item flags]. "
                                       "Amortizes interpreter startup across every fragment.")
    ap.add_argument("--jobs", type=int, default=1, metavar="N",
                    help="worker processes for --manifest (default 1; 0 = one per core). "
                         "Output is byte-identical at any --jobs: seeds are per-item.")
    ap.add_argument("--quiet", action="store_true", help="suppress the per-item line")
    return ap

def read_manifest(ap, base, path):
    """Parse each line against the same parser, inheriting the top-level namespace.

    Inheritance falls out of argparse: `parse_args(argv, namespace=ns)` only overwrites the
    attributes the line actually mentions. So a manifest line carries the differences and
    nothing else, and there is no second syntax to learn or to drift from the CLI."""
    import copy
    items = []
    with open(path) as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            ns = copy.deepcopy(base)
            ns.manifest = None                      # an item is never itself a batch
            ns.jobs = 1
            try:
                ap.parse_args(shlex.split(line), namespace=ns)
            except SystemExit:
                sys.exit(f"{path}:{n}: cannot parse manifest line: {line!r}")
            if not (ns.input and ns.output):
                sys.exit(f"{path}:{n}: manifest line needs IN and OUT: {line!r}")
            items.append(ns)
    return items

def _work(payload):
    """Run one item. Imports the tool by name so this survives the `spawn` start method
    macOS uses, where the child re-imports rather than forking the parent's memory."""
    module, ns = payload
    try:
        importlib.import_module(module).build(ns)
        return (ns.output, None)
    except SystemExit as e:                          # build() exits on bad args
        return (ns.output, f"{e}")
    except Exception as e:
        return (ns.output, f"{type(e).__name__}: {e}")

def run(ap, base, module):
    """Execute a manifest. Returns a process exit code."""
    items = read_manifest(ap, base, base.manifest)
    if not items:
        sys.exit(f"{base.manifest}: no items")
    for it in items:
        it.quiet = True                              # the batch reports, not each item
        d = os.path.dirname(it.output)
        if d:
            os.makedirs(d, exist_ok=True)

    jobs = base.jobs or (os.cpu_count() or 1)
    jobs = max(1, min(jobs, len(items)))
    payloads = [(module, it) for it in items]

    if jobs == 1:
        results = [_work(p) for p in payloads]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(_work, payloads))

    bad = [(o, e) for o, e in results if e]
    for o, e in bad:
        print(f"  FAILED {o}: {e}", file=sys.stderr)
    print(f"{module}: {len(results) - len(bad)}/{len(results)} items, {jobs} job(s)"
          + (f", {len(bad)} FAILED" if bad else ""))
    return 1 if bad else 0
