import typer

app = typer.Typer(help="CRM Helper automation tool")


@app.command()
def run():
    """Run the CRM automation."""
    import asyncio

    from crm_helper.main import main

    asyncio.run(main())


@app.command()
def gui():
    """Open the configuration GUI."""
    from crm_helper.gui import App

    App().mainloop()


if __name__ == "__main__":
    app()
