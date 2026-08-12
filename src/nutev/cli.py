from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from nutev.logs import setup_logger
from nutev.settings import NutevSettings


def main() -> None:
    p = argparse.ArgumentParser(
        prog="nutev",
        description="NutEV Evidence Engine — canonical command-line interface",
    )
    sub = p.add_subparsers(dest="command")

    gw = sub.add_parser("global-watch")
    gw.add_argument("--project-root", type=Path, required=True)
    gw.add_argument("--since-days", type=int, default=7)
    gw.add_argument("--mode", choices=["quick", "thesis", "exhaustive"], default="quick")
    gw.add_argument("--web-enabled", action="store_true")
    gw.add_argument("--official-crawl", action="store_true")
    gw.add_argument("--country-discovery", action="store_true")
    gw.add_argument("--llm-enabled", action="store_true")
    gw.add_argument("--resume", action="store_true")
    gw.add_argument("--notify-webhook", action="store_true")
    gw.add_argument("--webhook-url", type=str, default=None)
    gw.add_argument("--capture-enabled", action="store_true")
    gw.add_argument("--capture-limit", type=int, default=None)

    dash = sub.add_parser("dashboard")
    dash.add_argument("--project-root", type=Path, required=True)
    dash.add_argument("--port", type=int, default=8501)

    demo = sub.add_parser("demo-data")
    demo.add_argument("--project-root", type=Path, required=True)

    serve = sub.add_parser("serve")
    serve.add_argument("--project-root", type=Path, required=True)
    serve.add_argument("--host", type=str, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    platform_cmd = sub.add_parser("platform")
    platform_cmd.add_argument("--project-root", type=Path, required=True)
    platform_cmd.add_argument("--host", type=str, default="127.0.0.1")
    platform_cmd.add_argument("--port", type=int, default=8000)

    pilot = sub.add_parser("pilot-report")
    pilot.add_argument("--project-root", type=Path, required=True)

    prize = sub.add_parser("prize-metrics")
    prize.add_argument("--project-root", type=Path, required=True)

    verify = sub.add_parser("verify-sources")
    verify.add_argument("--project-root", type=Path, required=True)
    verify.add_argument("--timeout", type=float, default=20.0)
    verify.add_argument(
        "--no-countries",
        action="store_true",
        help="Check only the base manifest (skip per-country sources)",
    )

    guides = sub.add_parser(
        "guides",
        help="Fetch official guides, extract/OCR them, code A/B/C/D and extract key phrases",
    )
    guides.add_argument("--project-root", type=Path, required=True)
    guides.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N guides (default: all)",
    )
    guides.add_argument("--timeout", type=float, default=30.0)
    guides.add_argument(
        "--rate",
        type=float,
        default=0.5,
        help="Seconds between downloads per worker (politeness)",
    )
    guides.add_argument(
        "--offline",
        action="store_true",
        help="Skip downloads; only process guides already in 03C_official_docs",
    )
    guides.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel workers for fetch+OCR (default: 4)",
    )
    guides.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore the checkpoint and reprocess everything from scratch",
    )
    guides.add_argument(
        "--discover-fao",
        action="store_true",
        help=(
            "Crawl the FAO FBDG registry live for countries + guide files "
            "instead of relying only on the static manifest"
        ),
    )
    guides.add_argument(
        "--report",
        action="store_true",
        help=(
            "Also write the corpus report; needs pip install -e \".[report]\""
        ),
    )

    strategy = sub.add_parser(
        "strategy",
        help=(
            "Build transparent per-base search expressions from a question/PICOS "
            "spec (broad/balanced/specific)"
        ),
    )
    strategy.add_argument(
        "--spec",
        type=Path,
        required=True,
        help=(
            "JSON file: a PICOS dict (population/intervention/…) or "
            "{\"concepts\": [...]}"
        ),
    )
    strategy.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write the full provider×breadth grid as JSON",
    )

    play = sub.add_parser(
        "play",
        help=(
            "Run the gate-aware one-command PILOT pipeline: search, master corpus, "
            "lawful full-text recovery, download, text extraction and OCR"
        ),
    )
    play.add_argument("--project-root", type=Path, required=True)
    play.add_argument(
        "--version-id",
        type=str,
        default=None,
        help="Immutable strategy version ID (default: latest registered version)",
    )
    play.add_argument(
        "--breadth",
        choices=["broad", "balanced", "specific"],
        default="specific",
    )
    play.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Maximum records requested from each executable provider (1..10000)",
    )
    play.add_argument(
        "--providers",
        nargs="+",
        default=None,
        help="Optional subset: pubmed europepmc crossref openalex",
    )
    play.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore provider checkpoints for this PLAY invocation",
    )
    play.add_argument(
        "--metadata-only",
        action="store_true",
        help="Stop after search + corpus; do not resolve/download/extract full text",
    )

    args = p.parse_args()

    if not args.command:
        p.print_help()
        return

    if args.command == "global-watch":
        from nutev.global_watch.watch_pipeline import run_global_watch

        if not args.web_enabled:
            os.environ["NUTEV_DISABLE_NETWORK"] = "1"
        s = NutevSettings(
            project_root=args.project_root,
            web_enabled=args.web_enabled,
            mode=args.mode,
            since_days=args.since_days,
            llm_enabled=args.llm_enabled,
        )
        for directory in s.output_dirs.values():
            directory.mkdir(parents=True, exist_ok=True)
        logger = setup_logger(s.output_dirs["07_logs"])
        result = run_global_watch(
            s,
            logger,
            args.since_days,
            args.mode,
            args.resume,
            args.official_crawl,
            args.country_discovery,
            args.llm_enabled,
            capture_enabled=args.capture_enabled,
            capture_limit=args.capture_limit,
            notify_webhook=args.notify_webhook,
            webhook_url=args.webhook_url,
        )
        logger.info("Global watch: %s", result)
        return

    if args.command == "play":
        from nutev.pipelines.play_pipeline import run_play

        s = NutevSettings(project_root=args.project_root, web_enabled=True)
        for directory in s.output_dirs.values():
            directory.mkdir(parents=True, exist_ok=True)
        logger = setup_logger(s.output_dirs["07_logs"])
        summary = run_play(
            args.project_root,
            version_id=args.version_id,
            breadth=args.breadth,
            providers=args.providers,
            limit=args.limit,
            resume=not args.no_resume,
            metadata_only=args.metadata_only,
            logger=logger,
        )
        print("\nNutEV PLAY complete")
        print(f"play_id: {summary['play_id']}")
        print(f"status: {summary['status']['execution_status']}")
        print(
            "records: "
            f"{summary['search']['records_returned']} -> "
            f"{summary['corpus']['unique_records']} unique"
        )
        print(
            "full text: "
            f"{summary['fulltext']['downloaded']} downloaded | "
            f"{summary['extraction']['usable_text']} usable text | "
            f"{summary['extraction']['ocr_used']} OCR"
        )
        print(f"summary: {summary['artifacts']['summary_path']}")
        if summary["search"]["any_truncated"]:
            print("WARNING: at least one provider was truncated; this is not exhaustive.")
        print("Scientific state: PILOT only; PRISMA/formal execution remains blocked.")
        return

    if args.command == "dashboard":
        dashboard_path = Path(__file__).parent / "ui" / "dashboard.py"
        url = f"http://localhost:{args.port}"
        print(url)
        try:
            __import__("streamlit")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(dashboard_path),
                    "--server.port",
                    str(args.port),
                    "--",
                ],
                check=True,
                env={
                    **os.environ,
                    "NUTEV_DASHBOARD_PROJECT_ROOT": str(args.project_root),
                },
            )
        except ModuleNotFoundError:
            print('Streamlit não está instalado. Rode: pip install -e ".[dashboard]"')
        except Exception:
            print(url)
        return

    if args.command == "demo-data":
        from nutev.demo.demo_data import generate_demo_data

        generate_demo_data(args.project_root)
        print(f"Demo data generated at: {args.project_root}")
        return

    if args.command in {"serve", "platform"}:
        landing = f"http://{args.host}:{args.port}"
        if args.host == "0.0.0.0":
            print(
                "Atenção: você está expondo a API na rede. "
                "Use apenas em ambiente controlado."
            )
        print(f"Landing page: {landing}")
        print(f"API docs: {landing}/docs")
        print(f"Redoc: {landing}/redoc")
        try:
            __import__("fastapi")
            __import__("uvicorn")
            from nutev.api.server import create_app
            import uvicorn

            app = create_app(args.project_root)
            uvicorn.run(app, host=args.host, port=args.port)
        except ModuleNotFoundError:
            print('FastAPI/uvicorn não estão instalados. Rode: pip install -e ".[platform]"')
        return

    if args.command == "pilot-report":
        from nutev.export.pilot_report import generate_pilot_report

        path = generate_pilot_report(args.project_root)
        print(f"Pilot report generated: {path}")
        return

    if args.command == "prize-metrics":
        from nutev.export.prize_metrics import write_prize_metrics_summary

        path = write_prize_metrics_summary(args.project_root)
        print(f"Prize metrics generated: {path}")
        print(f"Prize metrics text: {path.with_suffix('.txt')}")
        return

    if args.command == "verify-sources":
        from nutev.search.verify_sources import (
            verify_official_sources,
            write_verification_report,
        )
        from nutev.settings import NutevSettings as _NS

        config_root = _NS(project_root=args.project_root).config_root
        rows = verify_official_sources(
            config_root,
            timeout=args.timeout,
            include_countries=not args.no_countries,
        )
        out = args.project_root / "07_logs" / "NUTEV_OFFICIAL_SOURCES_VERIFICATION.csv"
        write_verification_report(rows, out)
        total = len(rows)
        alive = sum(1 for row in rows if row.get("ok"))
        dead = [row for row in rows if not row.get("ok")]
        print(
            f"Verificadas {total} fontes oficiais: {alive} acessíveis, "
            f"{len(dead)} com problema."
        )
        for row in dead[:50]:
            print(
                f"  [{row.get('status_code')}] {row.get('reason')}  "
                f"{row.get('name')}  {row.get('url')}"
            )
        print(f"Relatório completo: {out}")
        return

    if args.command == "guides":
        from nutev.pipelines.guides_pipeline import run_guides

        s = NutevSettings(project_root=args.project_root)
        for directory in s.output_dirs.values():
            directory.mkdir(parents=True, exist_ok=True)
        logger = setup_logger(s.output_dirs["07_logs"])

        session = None
        if not args.offline and os.environ.get("NUTEV_DISABLE_NETWORK") != "1":
            import threading
            import time

            import requests
            from requests.adapters import HTTPAdapter

            session = requests.Session()
            session.headers["User-Agent"] = "NutEV Guides Fetcher/1.0"
            pool = max(args.workers * 2, 10)
            adapter = HTTPAdapter(pool_connections=pool, pool_maxsize=pool)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            original_get = session.get
            local = threading.local()

            def _throttled_get(*call_args, **call_kwargs):
                now = time.monotonic()
                last = getattr(local, "last", 0.0)
                wait = args.rate - (now - last)
                if wait > 0:
                    time.sleep(wait)
                local.last = time.monotonic()
                return original_get(*call_args, **call_kwargs)

            session.get = _throttled_get  # type: ignore[assignment]

        result = run_guides(
            s,
            logger,
            session=session,
            limit=args.limit,
            timeout=args.timeout,
            workers=args.workers,
            resume=not args.fresh,
            discover_fao=args.discover_fao,
            report=args.report,
        )
        logger.info("Guias: %s", result)
        print(
            f"Guias processados: {result['guides_processed']}/"
            f"{result['guides_in_manifest']} | "
            f"novos: {result['guides_new_this_run']} | "
            f"retomados: {result['guides_resumed_from_checkpoint']} | "
            f"com texto: {result['guides_with_fulltext']} | "
            f"OCR: {result['guides_ocr_used']} | "
            f"frases-chave: {result['key_phrases_total']}"
        )
        print(f"Checkpoint (salvar & continuar): {result['checkpoint']}")
        print(f"Tabela: {result['table_csv']}")
        print(f"Detalhe (frases-chave): {result['detail_json']}")
        return

    if args.command == "strategy":
        import json

        from nutev.search.strategy_builder import build_all, parse_concepts, parse_picos

        spec_data = json.loads(args.spec.read_text(encoding="utf-8"))
        spec = (
            parse_concepts(spec_data["concepts"])
            if isinstance(spec_data, dict) and "concepts" in spec_data
            else parse_picos(spec_data)
        )
        grid = build_all(spec)
        for provider, by_breadth in grid.items():
            print(f"\n=== {provider} ===")
            for breadth, expression in by_breadth.items():
                print(f"[{breadth}] {expression or '(vazio)'}")
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(grid, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\nGrade completa (provider × amplitude) salva em: {args.out}")
        return

    p.error(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
