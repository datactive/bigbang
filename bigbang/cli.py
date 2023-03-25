import click
from .ingress import mailman
from .analysis import repo_loader


@click.group()
def main():
    """BigBang CLI tools"""


# collect mail


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
    """Collects files from public mailman mailing list archives"""
    if url:
        mailman.collect_from_url(url, archive_dir=archives, notes=notes)
    elif file:
        mailman.collect_from_file(file, archive_dir=archives, notes=notes)
    else:
        print("Either --url or --file must be set")


# collect git


@main.command()
@click.option("--url", "url", required=True, help="URL of the git repo")
@click.option("--update", default=False, show_default=True, help="Update the git repo")
def collect_git_from_url(url, update):
    """Load git data from a repo URL"""
    repo_loader.get_repo(url, "remote", update)


@main.command()
@click.option(
    "--path", "path", required=True, help="Path of the file full of git repo URLs"
)
@click.option("--update", default=False, show_default=True, help="Update the git repo")
def collect_git_from_file_of_urls(path, update):
    """Load git data from repo URLs listed in a file"""
    with open(path, "r") as f:
        for line in f.readlines():
            url = line.strip()
            repo_loader.get_repo(url, "remote", update)


@main.command()
@click.option("--org-name", "org_name", required=True, help="GitHub organization name")
def collect_git_from_github_org(org_name):
    """Load git data from repos in a GitHub organization"""
    repo_loader.get_org_repos(org_name)
