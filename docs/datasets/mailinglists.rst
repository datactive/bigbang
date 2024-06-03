Mailinglists
************

Below we describe, how the public mailing lists of each of the Internet standard developing organisations can be scraped from the web. Some mailng lists reach back to 1998 and are multiple GBs in size. Therefore, it can take a considerable amount of time to scrape an entire mailing list. This process can't be sped up, since one would commit a DDoS attack otherwise. So be prepared to leave your machine running over (multiple) night(s).


IETF
================

There are several ways to access the public mailing list data of the Internet Engineering Task Force (IETF).

The IETF documents many access methods `here <https://www.ietf.org/how/lists/>`_.
We discuss several oprtions.

Remotely sync
----------------

The most efficient and reliable way to export a full mailing list archive from the IETF is with the ``rsync`` tool.

For example:

``rsync -v -r rsync.ietf.org::mailman-archive/listname .``

BigBang can then be pointed to create directory and used for analytics.


Export from Web Interface
-----------------------

The IETF allow logged in users to export up to 5000 messages at a time from their
on-line `mail archive <https://mailarchive.ietf.org/arch/>`_.

These are downloaded as a compressed directory of ``.mbox`` files.

Put this directoy in you `archives/` directory to make it available for analysis.


Collect-mail from text archives
-------------------------------

The full email archives are also `available as text files <https://www.ietf.org/mail-archive/text/>`_` (``.mail``) 
available through the web.

BigBang comes with a script for collecting files like. For example, mail for a specific list can be collected using its archival URL.

For example, for the mailing list archive of the ``dnsop`` working group,
run the following command from the root directory of this repository:

``bigbang collect-mail --url https://www.ietf.org/mail-archive/text/dnsop/``

More information is available in the CLI help interface: ``bigbang collect-mail --help``


W3C
================
The World Wide Web Consortium (W3C) mailing archive is managed using the Hypermail 2.4.0 software and is hosted at:

``https://lists.w3.org/Archives/Public/``

There are two ways you can scrape the public mailing-list from that domain. First, one can write their own python script containing a variation of:

.. code-block:: python

    from bigbang.ingress import W3CMailList

    mlist = W3CMailList.from_url(
        name="public-testtwf",
        url="https://lists.w3.org/Archives/Public/public-testtwf/",
        select={"years": 2014, "fields": "header"},
    )
    mlist.to_mbox(path_to_file)

Or one can use the command line script and a file containg all mailing-list URLs one wants to scrape:

``bigbang collect-mail --file examples/url_collections/W3C.txt``

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

``bigbang collect-mail --file examples/url_collections/listserv.3GPP.txt``

IEEE
================
The Institute of Electrical and Electronics Engineers (IEEE) mailing archive is managed using the LISTSERV software and is hosted at:

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

``bigbang collect-mail --file examples/url_collections/listserv.IEEE.txt``


ICANN
================
The Internet Corporation for Assigned Names and Numbers (ICANN) mailing archive is managed using the Pipermail 0.09 format and is hosted at:

``https://mm.icann.org/pipermail/<name_of_mailing_list>``

where the part inside ``<name_of_mailing_list>`` needs to substituted by the name of the mailing list one wants to ingress.

Mailing lists in this format are scraped by reading their ``.txt`` or ``.txt.gz`` files of each month of a year. For a singled month, this can be done as follows

.. code-block:: python

    from bigbang.ingress import PipermailMailList

    mlist = PipermailMailList.from_period_urls(
        name="accred-model",
        url="https://mm.icann.org/pipermail/accred-model",
        period_urls=["https://mm.icann.org/pipermail/accred-model/2018-August.txt.gz"],
        fields="total",
    )

while an entire mailing list can be ingressed using

.. code-block:: python

    from bigbang.ingress import PipermailMailList

    mlist = PipermailMailList.from_url(
        name="accred-model",
        url="https://mm.icann.org/pipermail/accred-model",
        select={
            "years": 2018,
            "fields": "total",
        },
    )


Public Mailman 1 Web Archive
==============================

BigBang comes with a script for collecting files from public Mailman 1 web archives. An example of this is the
`scipy-dev <http://mail.python.org/pipermail/scipy-dev/>`_ mailing list page. To collect the archives of the scipy-dev mailing list, run the following command from the root directory of this repository:

``bigbang collect-mail --url http://mail.python.org/pipermail/scipy-dev/``

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

``bigbang collect-mail --file examples/urls.txt``

Once the data has been collected, BigBang has functions to support analysis.