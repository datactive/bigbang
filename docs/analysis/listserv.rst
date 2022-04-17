.. _analysis_3gpp:

3GPP
======

This page introduces a collection of simple functions with which a comprehensive
overview of 3GPP mailinglists, ingressed using `bigbang/ingress/listserv.py`, is
gained. Without extensive editing, these functions should also be applicable to
IETF, ICANN, W3C, and IEEE mailinglists, however it hasn't been tested yet.

To start, a ``ListservList`` class instance needs to be created using either
``.from_mbox()`` or ``.from_pandas_dataframe()``. Using the former as an example:

.. code-block:: python

    from bigbang.analysis.listserv import ListservList

    mlist_name = "3GPP_TSG_CT_WG1_122E_5G"
    mlist = ListservList.from_mbox(
        name=mlist_name,
        filepath=f"/path/to/{mlist_name}.mbox",
        include_body=True,
    )


The function argument ``include_body`` is by default ``True``, but if one has to work
with a large quantity of Emails, it might be necessary to set it to `False` to
avoid out-of-memory errors.

Cropping of mailinglist
-----------------------

If one is interested in specific subgroups contained in a mailinglist, then the
`ListservList` class instance can be cropped using the following functions:

.. code-block:: python

    # select Emails send in a specific year
    mlist.crop_by_year(yrs=[2011])

    # select Emails send within a period
    mlist.crop_by_year(yrs=[2011, 2021])

    # select Emails send or received from specified addresses
    mlist.crop_by_address(
        header_field='from',
        per_address_field={'domain': ['t-mobile.at', 'nokia.com']}
    )

    # select Emails containing string in subject
    mlist.crop_by_subject(match='OpenPGP')

In the second example, the function has an ``per_address_field`` argument. This
argument is a dictionary in which the top-level keys can be ``localpart``
and ``domain``, where the former is the part of an Email address that stands
in front of the @ and the latter after. Thus for `Heinrich.vonKleist@selbst.org`,
localpart is `Heinrich.vonKleist` and the domain is `selbst.org`.

Who is sending/receiving?
-------------------------
To get an insight in which actors are involved in a mailinglist, a ``ListservList``
class instance can be return the unique email domains and the unique email localparts
per domain for multiple header fields:

.. code-block:: python

    mlist.get_domains(header_fields=['from', 'reply-to'])

    mlist.get_localparts(header_fields=['from', 'reply-to'])

This will return a dictionary, in which each key (both 'from' and 'reply-to')
contains a list of all domains. If one wants see not just who contributes, but
also how much, change the default argument of ``return_msg_counts=False`` to ``True``:

.. code-block:: python

    mlist.get_domains(header_fields=['from', 'reply-to'], return_msg_counts=True)

Alternatively, one can also get the number of Emails send or received by a certain
address via,

.. code-block:: python

    mlist.get_messagescount(
        header_fields=['from', 'reply-to'],
        per_address_field={
            'domain': ['t-mobile.at', 'nokia.com'],
            'localpart': ['ian.hacking', 'victor.klemperer'],
        }
    )

.. _communication_network:

Communication Network
---------------------
For a more in-depth view into who is sending (receiving) to (from) whom in a
mailing list, one can use the ``return_msg_counts=False`` as follows:

.. code-block:: python

    mlist.create_sender_receiver_digraph()

This will create a new ``networkx.DiGraph()`` instance attribute for ``mlist``,
which can be used to perform a number of standard calculations using the
``networkx`` python package:

.. code-block:: python

    import networkx as nx

    nx.betweenness_centrality(mlist.dg, weight="weight")
    nx.closeness_centrality(mlist.dg)
    nx.degree_centrality(mlist.dg)

.. _time_series:

Time-series
-----------
To study, e.g., the continuity of an actors contribution to a mailinglist, many
function have an optional ``per_year`` boolean argument.

To simply find out during which period Emails were in a mailinglist, one can call
``mlist.period_of_activity()``.
