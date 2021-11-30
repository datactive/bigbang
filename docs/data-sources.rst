Data sources
**************

Mailman (IETF)
================

BigBang comes with a script for collecting files from public Mailman web
archives. An example of this is the
`scipy-dev <http://mail.python.org/pipermail/scipy-dev/>`_
mailing list page. To
collect the archives of the scipy-dev mailing list, run the following command
from the root directory of this repository:

``python3 bin/collect_mail.py -u http://mail.python.org/pipermail/scipy-dev/``

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

``python3 bin/collect_mail.py -f examples/urls.txt``

Once the data has been collected, BigBang has functions to support analysis.


W3C
======

Usage
-------

Ethical Considerations
------------------------



3GPP
=================
The 3GPP mailing archive is managed using the LISTSERV software and is hosted at:
https://list.etsi.org/scripts/wa.exe?HOME

In order to be able to view most header fields and text bodies (there might still
be some fields that are hidden) on needs to create an account here:
https://list.etsi.org/scripts/wa.exe?GETPW1=&X=&Y=

The entire archive reaches back to 1998 and is multiple GBs in size. Therefore,
it takes a considerable amount of time to scrape the entire archive and strain on
the server host if everyone of interest would scrape them individually. To 
resolve this issue we keep an up to date version of the archive.

We are currently working on a improved version of the 'Data Access Permit Application'.

Usage
-------

Ethical Considerations
------------------------



IETF DataTracker (RFC drafts, etc.)
========================================

BigBang can also be used to analyze data from IETF drafts.

It does this using the Glasgow IPL group's `ietfdata` `tool <https://github.com/glasgow-ipl/ietfdata>`_.

The script takes an argument, the working group acronym

``python3 bin/collect_draft_metadata.py -w httpbis``
