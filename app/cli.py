import typer

from app.platform.actions import enqueue
from app.platform.context import PlatformContext
from app.platform.worker import serve

app = typer.Typer(no_args_is_help=True, help="One platform for platform crawls and web crawls.")


@app.command()
def crawl(url: str, keyword: str = "") -> None:
    """Enqueue one job. Known hosts become media jobs; everything else is web."""
    job = enqueue(PlatformContext.open(), url, keyword)
    typer.echo(f"queued {job.id} capability={job.capability} platform={job.platform or '-'}")


@app.command()
def worker(once: bool = False) -> None:
    """Run both capabilities from the same queue."""
    ctx = PlatformContext.open()
    serve(ctx, once=once)


@app.command("jobs")
def jobs(limit: int = 20) -> None:
    ctx = PlatformContext.open()
    for job in ctx.store.list_jobs(limit):
        typer.echo(f"{job.id} {job.status} {job.capability} {job.url} {job.error}")


@app.command("proxy-add")
def proxy_add(proxy_url: str) -> None:
    ctx = PlatformContext.open()
    ctx.proxies.add(proxy_url)
    typer.echo(f"proxy {proxy_url}")


@app.command()
def ui(host: str = "127.0.0.1", port: int = 8080, no_browser: bool = False) -> None:
    """Start the worker and open the browser console."""
    import threading
    import webbrowser

    import uvicorn

    from app.server import create_app

    ctx = PlatformContext.open()
    threading.Thread(target=serve, args=(ctx,), daemon=True).start()
    if not no_browser:
        open_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
        threading.Timer(0.8, lambda: webbrowser.open(f"http://{open_host}:{port}")).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
