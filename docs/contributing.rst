Contributing
============

The BigBang community welcomes contributions.

Release Procedure
-----------------

When the community decides that it is time to cut a new release, the Core Developers select somebody to act as release manager.
That release manager then performs the following steps.

1. Determine the next release number via the standards of semantic versioning.
2. Solicit a worthy name for the release.
3. Address any remaining tickets in the GitHub milestone corresponding to the release, perhaps moving them to other milestones.
4. Consult the GitHub records of merged PRs and issues to write release notes documenting the changes made in this release.
5. If the dependencies in main are not already frozen, use ``pip freeze`` to create a new frozen dependency list. Consider testing the code against unfrozen dependencies first to update version numbers.
6. Use the `GitHub Releases interface <https://github.com/datactive/bigbang/releases>`_. to cut a new release from the main branch, with the selected name and number. This should create a new tag corresponding to the release commit.
7. Write a message to the BigBang development list announcing the new release, including the release notes.


README for BigBang Docs
-----------------------

To build the docs, go to the `docs/` directory and run

```
make html
```

The built docs will be deposited in `docs/_build`
