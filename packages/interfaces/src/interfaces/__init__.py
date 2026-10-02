def main() -> None:
    import uvicorn

    from interfaces.config import settings

    uvicorn.run("interfaces.server:app", host=settings.host, port=settings.port)
