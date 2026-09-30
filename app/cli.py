import typer

from app.platform.context import PlatformContext
from app.platform.models import Job, classify
from app.platform.worker import serve

app = typer.Typer(no_args_is_help=True, help="One platform for platform crawls and web crawls.")


@app.command()
def crawl(url: str, keyword: str = "") -> None:
    """Enqueue one job. Known hosts become media jobs; everything else is web."""
    ctx = PlatformContext.open()
    ctx.store.create_tables()
    capability, platform = classify(url)
    job = Job(url=url, keyword=keyword, capability=capability, platform=platform, cookie_key=platform)
    ctx.queue.push(job)
    ctx.store.save_job(job)
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
