Mailinglists
************

Below we describe, how the public mailing lists of each of the Internet standard developing organisations can be scrabed from the web. Some mailng lists reach back to 1998 and is multiple GBs in size. Therefore, it can take a considerable amount of time to scrape an entire mailing list. This process can't be speed up, since one would commit a DDoS attack otherwise. So be prepared to leave your machine running over (multiple) night(s).

IETF
================

To scrabed public mailing lists of the Internet Engineering Task Force (IETF), there are two options outlined below.

Public Mailman Web Archive
--------------------------
BigBang comes with a script for collecting files from public Mailman web archives. An example of this is the
`scipy-dev <http://mail.python.org/pipermail/scipy-dev/>`_ mailing list page. To collect the archives of the scipy-dev mailing list, run the following command from the root directory of this repository:

``python3 bin/collect_mail.py -u http://mail.python.org/pipermail/scipy-dev/``

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

``python3 bin/collect_mail.py -f examples/urls.txt``

Once the data has been collected, BigBang has functions to support analysis.


Datatracker
-----------
BigBang can also be used to analyze data of IETF RFC drafts.

It does this using the Glasgow IPL group's ``ietfdata`` `tool <https://github.com/glasgow-ipl/ietfdata>`_.

The script takes an argument, the working group acronym

``python3 bin/collect_draft_metadata.py -w httpbis``


W3C
================
The World Wide Web Consortium (W3C) mailing archive is managed using the Hypermail software and is hosted at:

``https://lists.w3.org/Archives/Public/``

There are two ways you can scrape the public mailing-list from that domain. First, one can write their own python script containing a variation of:

.. code-block:: python

    from bigbang.ingress import ListservMailList

    mlist = W3CMailList.from_url(
        name="public-testtwf",
        url="https://lists.w3.org/Archives/Public/public-testtwf/",
        select={"years": 2014, "fields": "header"},
    )
    mlist.to_mbox(path_to_file)

Or one can use the command line script and a file containg all mailing-list URLs one wants to scrape:

``python bin/collect_mail.py -f examples/url_collections/W3C.txt``

3GPP
=================
The 3rd Generation Partnership Project (3GPP) mailing archive is managed using the LISTSERV software and is hosted at:

``https://list.etsi.org/scripts/wa.exe?HOME``

In order to successfully scrape all public mailing lists, one needs to create an account here:
https://list.etsi.org/scripts/wa.exe?GETPW1=&X=&Y=

There are two ways you can scrape the public mailing-list from that domain. First, one can write their own python script containing a variation of:

.. code-block:: python

    from bigbang.ingress import ListservMailList

    mlist = ListservMailList.from_url(
        name="3GPP_TSG_SA_WG2_EMEET",
        url="https://list.etsi.org/scripts/wa.exe?A0=3GPP_TSG_SA_WG2_EMEET",
        select={"fields": "header",},
        url_login="https://list.etsi.org/scripts/wa.exe?LOGON=INDEX",
        url_pref="https://list.etsi.org/scripts/wa.exe?PREF",
        login=auth_key,
    )
    mlist.to_mbox(path_to_file)

Or one can use the command line script and a file containg all mailing-list URLs one wants to scrape:

``python bin/collect_mail.py -f examples/url_collections/listserv.3GPP.txt``

IEEE
================
The Institute of Electrical and Electronics Engineers (W3C) mailing archive is managed using the LISTSERV software and is hosted at:

``https://listserv.ieee.org/cgi-bin/wa?INDEX``

There are two ways you can scrape the public mailing-list from that domain. First, one can write their own python script containing a variation of:

.. code-block:: python

    from bigbang.ingress import ListservMailList

    mlist = ListservMailList.from_url(
        name="IEEE-TEST",
        url="https://listserv.ieee.org/cgi-bin/wa?A0=IEEE-TEST",
        select={"fields": "header",},
        url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
        url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
        login=auth_key,
    )
    mlist.to_mbox(path_to_file)

Or one can use the command line script and a file containg all mailing-list URLs one wants to scrape:

``python bin/collect_mail.py -f examples/url_collections/listserv.IEEE.txt``
