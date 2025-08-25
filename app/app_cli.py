import typer
import asyncio
from app.rag import RAG

app = typer.Typer(help="CLI do Chatbot SIGNA")

@app.command()
def ask(q: str):
    """Faça uma pergunta ao Chatbot SIGNA."""
    rag = RAG()
    result = asyncio.run(rag.answer(q))
    typer.echo(result["answer"])
    if result["sources"]:
        typer.echo("\nFontes:")
        for s in result["sources"]:
            typer.echo(f"- {s}")

if __name__ == "__main__":
    app()
