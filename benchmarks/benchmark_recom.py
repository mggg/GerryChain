#!/usr/bin/env python3
"""Benchmark GerryChain ReCom throughput, optionally comparing versions.

Subcommands:

  run       Run the benchmark in the *current* environment and report ms/step.
            This is also the worker that `compare` invokes under the hood.

  compare   Run the benchmark against one or more targets, each in an isolated
            environment (via `uv`), and print a comparison table. Targets:

              local           this checkout's dev environment (working tree,
                              including uncommitted changes)
              pypi:<version>  a released version, e.g. pypi:0.3.2
              git:<ref>       any commit/branch/tag of this repo, e.g.
                              git:main, git:3f2e9e9, git:v0.3.1. Uses the
                              *committed* state of the ref - the working tree
                              is not consulted.

Each benchmark runs the chain once per seed: `--num-seeds` consecutive seeds
starting at `--seed`, times `--repeats`, with up to `--jobs` seeds running in
parallel (the chain itself is single-threaded, so parallel seeds on a
many-core machine contend only mildly). Results are aggregated as
min / median / max ms-per-step over all runs; `compare` computes the speedup
column from the medians.

Examples:

  # Quick timing of the working tree (5 seeds, 5 parallel jobs by default):
  uv run python benchmarks/benchmark_recom.py run --steps 250

  # Working tree vs. the commit you branched from vs. the last release:
  uv run python benchmarks/benchmark_recom.py compare local git:main pypi:0.3.2

  # Did my last commit help? (committed HEAD vs. its parent)
  uv run python benchmarks/benchmark_recom.py compare git:HEAD git:HEAD~1 --steps 500

  # Watch a single run with a progress bar:
  uv run python benchmarks/benchmark_recom.py run --num-seeds 1 --progress

  # Profile the working tree to find hotspots (forces sequential execution and
  # inflates timings; don't use the ms/step from a profiled run for comparisons):
  uv run python benchmarks/benchmark_recom.py run --num-seeds 1 --steps 250 --profile

The first target listed is the baseline for the speedup column. Isolated targets are resolved with
`uv run --no-project`, executed from a temp directory so the repo's `gerrychain/` package directory
cannot shadow the installed version. All targets must support the high-level API used here
(`Graph.from_json`, `Partition.from_random_assignment`, `recom`, `MarkovChain`, `updaters.Tally`),
which is stable from 0.3.x onward.

Note on RNG: by default a fresh base seed is drawn each invocation and printed; pass --seed to pin
it. Within a `compare`, every target gets the same seeds either way - though different gerrychain
versions consume the RNG streams differently, so they will not walk the same chains. This measures
throughput, not output equivalence. The script re-runs itself with PYTHONHASHSEED=0 so that a
pinned --seed is actually reproducible despite Python's hash-randomized set/dict ordering.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOP_DIR = SCRIPT_DIR.parent
RESULT_MARKER = "@@RESULT "
DEFAULT_JSON = SCRIPT_DIR / "graphs" / "hard_graph.json"
MAX_NUMPY_SEED = 2**32 - 1


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def numpy_seed(value: str) -> int:
    parsed = int(value)
    if not 0 <= parsed <= MAX_NUMPY_SEED:
        raise argparse.ArgumentTypeError(f"must be between 0 and {MAX_NUMPY_SEED}")
    return parsed


# --------------------------------------------------------------------------
# worker: run the benchmark in whatever environment we were launched into
# --------------------------------------------------------------------------

# (graph, args, progress) for _run_one_seed. Forked pool workers inherit it from the
# parent; spawned pool workers (Windows/macOS default) build it via _init_pool_worker.
_WORKER_STATE: tuple | None = None


def _init_pool_worker(args: argparse.Namespace) -> None:
    """Build _WORKER_STATE in a spawned pool worker, which inherits nothing from the
    parent and so must load the graph itself."""
    global _WORKER_STATE

    from gerrychain import Graph

    _WORKER_STATE = (Graph.from_json(args.json), args, False)


def _run_one_seed(seed: int) -> dict:
    """Run the chain for one seed. Must stay module-level so forked pool
    workers can call it; reads the graph from _WORKER_STATE."""
    import random
    from functools import partial

    import numpy as np

    from gerrychain import MarkovChain, Partition, accept, updaters
    from gerrychain.proposals import recom

    graph, args, progress = _WORKER_STATE

    profiler = None
    if args.profile:
        import cProfile

        profiler = cProfile.Profile()

    build_s: list[float] = []
    times_s: list[float] = []
    for _ in range(args.repeats):
        random.seed(seed)
        np.random.seed(seed)

        t0 = time.perf_counter()
        initial = Partition.from_random_assignment(
            graph,
            n_parts=args.parts,
            epsilon=args.epsilon,
            pop_col=args.pop_col,
            updaters={"population": updaters.Tally(args.pop_col, alias="population")},
        )
        build_s.append(time.perf_counter() - t0)

        ideal = sum(initial["population"].values()) / len(initial)
        proposal = partial(
            recom,
            pop_col=args.pop_col,
            pop_target=ideal,
            epsilon=args.epsilon,
            node_repeats=2,
        )
        chain = MarkovChain(
            proposal=proposal,
            constraints=[],
            accept=accept.always_accept,
            initial_state=initial,
            total_steps=args.steps,
        )
        steps_iter = chain.with_progress_bar() if progress else chain

        if profiler is not None:
            profiler.enable()
        t0 = time.perf_counter()
        for _ in steps_iter:
            pass
        elapsed = time.perf_counter() - t0
        if profiler is not None:
            profiler.disable()
        times_s.append(elapsed)

    result = {"seed": seed, "build_s": build_s, "times_s": times_s}
    if profiler is not None:
        out = Path(args.out)
        if args.num_seeds > 1:
            out = out.with_name(f"{out.stem}_seed{seed}{out.suffix}")
        profiler.dump_stats(str(out))
        result["profile_out"] = str(out)
    return result


def _print_seed_result(result: dict, steps: int) -> None:
    build = sum(result["build_s"]) / len(result["build_s"])
    per_repeat = ", ".join(f"{t / steps * 1000:.3f}" for t in result["times_s"])
    print(
        f"seed {result['seed']}: initial partition {build:.2f}s, ms/step per repeat: {per_repeat}",
        flush=True,
    )


def cmd_run(args: argparse.Namespace) -> None:
    # Defer imports because this environment is set by the orchestrator and may be different for
    # each worker process.
    import importlib.metadata
    import random
    import statistics

    import gerrychain
    from gerrychain import Graph

    global _WORKER_STATE

    try:
        version = importlib.metadata.version("gerrychain")
    except importlib.metadata.PackageNotFoundError:
        version = getattr(gerrychain, "__version__", "unknown")
    print(f"gerrychain {version} from {gerrychain.__file__}", flush=True)

    base_seed = args.seed
    if base_seed is None:
        base_seed = random.randrange(2**31)
        print(
            f"base seed drawn randomly: {base_seed} (pass --seed {base_seed} to reproduce)",
            flush=True,
        )
    if base_seed + args.num_seeds - 1 > MAX_NUMPY_SEED:
        raise SystemExit(
            f"--seed plus --num-seeds exceeds numpy's maximum seed value ({MAX_NUMPY_SEED})"
        )
    seeds = [base_seed + i for i in range(args.num_seeds)]
    jobs = max(1, min(args.jobs, len(seeds)))
    progress = args.progress
    if args.profile and jobs > 1:
        print("note: --profile forces sequential execution (--jobs 1)", flush=True)
        jobs = 1
    if progress and (jobs > 1 or len(seeds) > 1):
        print("note: --progress only applies to a single sequential seed; ignoring", flush=True)
        progress = False

    graph = Graph.from_json(args.json)
    print(
        f"graph={Path(args.json).name} nodes={len(graph.nodes)} "
        f"parts={args.parts} epsilon={args.epsilon} "
        f"steps={args.steps} pop_col={args.pop_col} "
        f"seeds={seeds[0]}..{seeds[-1]} repeats={args.repeats} jobs={jobs}",
        flush=True,
    )

    _WORKER_STATE = (graph, args, progress)
    seed_results: list[dict] = []
    if jobs == 1:
        for seed in seeds:
            result = _run_one_seed(seed)
            seed_results.append(result)
            _print_seed_result(result, args.steps)
    else:
        import multiprocessing

        start_methods = multiprocessing.get_all_start_methods()
        method = args.start_method
        if method == "auto":
            # prefer fork (children inherit the already-loaded graph); Windows has no
            # fork, so fall back to spawn with a per-worker graph load
            method = "fork" if "fork" in start_methods else "spawn"
        elif method not in start_methods:
            raise SystemExit(
                f"multiprocessing start method {method!r} is not available on this platform "
                f"(available: {', '.join(start_methods)})"
            )
        ctx = multiprocessing.get_context(method)
        if method == "fork":
            pool = ctx.Pool(processes=jobs)
        else:
            pool = ctx.Pool(processes=jobs, initializer=_init_pool_worker, initargs=(args,))
        with pool:
            for result in pool.imap_unordered(_run_one_seed, seeds):
                seed_results.append(result)
                _print_seed_result(result, args.steps)
        seed_results.sort(key=lambda r: r["seed"])

    if args.profile:
        import pstats

        for result in seed_results:
            print(f"\nprofile for seed {result['seed']} written to {result['profile_out']}")
            st = pstats.Stats(result["profile_out"])
            print("\n==== by cumulative time ====")
            st.sort_stats("cumulative").print_stats(30)
            print("\n==== by total (self) time ====")
            st.sort_stats("tottime").print_stats(30)

    all_ms = [t / args.steps * 1000 for r in seed_results for t in r["times_s"]]
    ms_stats = {
        "min": min(all_ms),
        "median": statistics.median(all_ms),
        "max": max(all_ms),
    }
    print(
        f"\nms/step over {len(all_ms)} run(s): min {ms_stats['min']:.3f}, "
        f"median {ms_stats['median']:.3f}, max {ms_stats['max']:.3f}",
        flush=True,
    )

    result = {
        "version": version,
        "module_file": gerrychain.__file__,
        "graph": str(Path(args.json).resolve()),
        "steps": args.steps,
        "seeds": seeds,
        "repeats": args.repeats,
        "jobs": jobs,
        "ms_per_step": ms_stats,
        "per_seed": seed_results,
        "profiled": bool(args.profile),
    }
    print(RESULT_MARKER + json.dumps(result), flush=True)


# --------------------------------------------------------------------------
# orchestrator: run the worker against several targets and compare
# --------------------------------------------------------------------------


def target_command(target: str, python_version: str) -> tuple[str, list[str]]:
    """Map a target spec to (display label, command prefix ending in a python)."""
    if target == "local":
        return "local (working tree)", [sys.executable]
    if target.startswith("pypi:"):
        version = target[len("pypi:") :]
        spec = f"gerrychain=={version}"
        label = f"pypi:{version}"
    elif target.startswith("git:"):
        ref = target[len("git:") :]
        sha = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=TOP_DIR,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        # as_uri() instead of an f-string so Windows paths (C:\...) form a valid file URL
        spec = f"gerrychain @ git+{TOP_DIR.as_uri()}@{sha}"
        label = f"git:{ref} ({sha[:9]})"
    else:
        raise SystemExit(
            f"unknown target {target!r}: expected 'local', 'pypi:<version>', or 'git:<ref>'"
        )
    prefix = [
        "uv",
        "run",
        "--no-project",
        "--python",
        python_version,
        "--with",
        spec,
        "python",
    ]
    return label, prefix


def cmd_compare(args: argparse.Namespace) -> None:
    import random

    base_seed = args.seed
    if base_seed is None:
        base_seed = random.randrange(2**31)
        print(
            f"base seed drawn randomly: {base_seed} - every target gets the same seeds "
            f"(pass --seed {base_seed} to reproduce)",
            flush=True,
        )

    script = str(Path(__file__).resolve())
    worker_args = [
        "run",
        "--json",
        str(Path(args.json).resolve()),
        "--parts",
        str(args.parts),
        "--epsilon",
        str(args.epsilon),
        "--steps",
        str(args.steps),
        "--seed",
        str(base_seed),
        "--num-seeds",
        str(args.num_seeds),
        "--jobs",
        str(args.jobs),
        "--repeats",
        str(args.repeats),
        "--pop-col",
        args.pop_col,
        "--start-method",
        args.start_method,
    ]

    results: list[tuple[str, dict | None]] = []
    # Run from a temp dir so the repo's gerrychain/ dir can't shadow installs.
    with tempfile.TemporaryDirectory() as tmpdir:
        for target in args.targets:
            label, prefix = target_command(target, args.python)
            print(f"\n=== {label} ===", flush=True)
            proc = subprocess.Popen(
                prefix + [script] + worker_args,
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            result = None
            assert proc.stdout is not None
            for line in proc.stdout:
                if line.startswith(RESULT_MARKER):
                    result = json.loads(line[len(RESULT_MARKER) :])
                else:
                    print("  " + line.rstrip(), flush=True)
            proc.wait()
            if proc.returncode != 0 or result is None:
                print(f"  FAILED (exit code {proc.returncode})", flush=True)
                results.append((label, None))
            else:
                results.append((label, result))

    baseline = next((r for _, r in results if r is not None), None)
    width = max((len(label) for label, _ in results), default=0)
    print(
        f"\n==== summary: graph={Path(args.json).name}, "
        f"{args.num_seeds} seed(s) x {args.repeats} repeat(s) from seed {base_seed}, "
        f"{args.steps} steps, parts={args.parts}, epsilon={args.epsilon}, "
        f"jobs={args.jobs} ===="
    )
    for label, result in results:
        if result is None:
            print(f"{label:<{width}}  FAILED")
            continue
        ms = result["ms_per_step"]
        if result is baseline:
            note = "(baseline)"
        else:
            note = f"({baseline['ms_per_step']['median'] / ms['median']:.2f}x baseline speed)"
        print(
            f"{label:<{width}}  median {ms['median']:9.3f} ms/step  "
            f"[min {ms['min']:9.3f}, max {ms['max']:9.3f}]  "
            f"gerrychain {result['version']:<10} {note}"
        )

    if any(result is None for _, result in results):
        sys.exit(1)


# --------------------------------------------------------------------------


def add_benchmark_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        default=str(DEFAULT_JSON),
        help=f"dual graph JSON to run on (default: {DEFAULT_JSON})",
    )
    parser.add_argument("--pop-col", default="TOTPOP", help="population column (default: TOTPOP)")
    parser.add_argument(
        "--parts", type=positive_int, default=6, help="number of districts (default: 6)"
    )
    parser.add_argument(
        "--epsilon", type=float, default=0.01, help="population deviation (default: 0.01)"
    )
    parser.add_argument(
        "--steps", type=positive_int, default=250, help="chain steps per run (default: 250)"
    )
    parser.add_argument(
        "--seed",
        type=numpy_seed,
        default=None,
        help="base random/numpy seed; consecutive seeds count up from it "
        "(default: drawn randomly and printed so the run can be reproduced)",
    )
    parser.add_argument(
        "--num-seeds",
        type=positive_int,
        default=5,
        help="number of consecutive seeds, starting at --seed (default: 5)",
    )
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=5,
        help="max seeds to run in parallel; each chain is single-threaded (default: 5)",
    )
    parser.add_argument(
        "--repeats",
        type=positive_int,
        default=1,
        help="timed repeats per seed (same trajectory re-run; default: 1)",
    )
    parser.add_argument(
        "--start-method",
        choices=["auto", "fork", "spawn"],
        default="auto",
        help="multiprocessing start method for parallel seeds (default: auto - "
        "fork where available, else spawn)",
    )


def main() -> None:
    # Hash randomization changes set/dict iteration order inside gerrychain, so a pinned --seed
    # only reproduces a run under a fixed hash seed. The interpreter's hash seed is locked at
    # startup, so re-run process once with PYTHONHASHSEED=0 and forward the exit code. (using
    # spawn-and-exit rather than os.execv b/c Windows fakes exec by spawning a new process)
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        sys.exit(subprocess.run([sys.executable] + sys.argv, env=env).returncode)

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="benchmark the current environment")
    add_benchmark_options(run_p)
    run_p.add_argument(
        "--progress",
        action="store_true",
        help="show a chain progress bar (single sequential seed only)",
    )
    run_p.add_argument(
        "--profile",
        action="store_true",
        help="also cProfile the chain (forces sequential execution; inflates timings)",
    )
    run_p.add_argument(
        "--out", default=str(SCRIPT_DIR / "recom_profile.prof"), help="profile output path"
    )
    run_p.set_defaults(func=cmd_run)

    cmp_p = sub.add_parser("compare", help="benchmark several targets and compare")
    cmp_p.add_argument(
        "targets",
        nargs="+",
        help="targets: 'local', 'pypi:<version>', 'git:<ref>' (first is the baseline)",
    )
    add_benchmark_options(cmp_p)
    cmp_p.add_argument(
        "--python", default="3.11", help="python version for isolated targets (default: 3.11)"
    )
    cmp_p.set_defaults(func=cmd_compare)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
