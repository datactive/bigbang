import click
from .ingress import mailman


@click.group()
def main():
    """BigBang CLI tools"""


@main.command()
@click.option("--url", "url", help="URL of mailman archive")
@click.option(
    "--file", "file", help="Path of a file with linebreak-seperated list of URLs"
)
@click.option(
    "--archives",
    "archives",
    default="./archives",
    show_default=True,
    help="Path to a specified directory for storing downloaded mail archives",
)
@click.option("--notes", "notes", help="Notes to record regarding provenance")
def collect_mail(url, file, archives, notes):
    """Collects files from public mailing list archives"""
    if url:
        mailman.collect_from_url(url, archive_dir=archives, notes=notes)
    elif file:
        mailman.collect_from_file(file, archive_dir=archives, notes=notes)
    else:
        print("Either --url or --file must be set")
