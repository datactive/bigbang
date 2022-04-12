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

Cropping
--------

If one is interested in specific subgroups contained in a mailinglist, then the
`ListservList` class instance can be cropped using the following functions:

.. code-block:: python

    mlist.crop_by_year(yrs=[2011, 2021])

    mlist.crop_by_address(header_field='from', per_address_field={'domain': [t-mobile.at, nokia.com]})

    mlist.crop_by_subject(match='OpenPGP')

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




Time-series
-----------
To find out during which period Emails were send to a mailinglist, one can call
``mlist.period_of_activity()``, which will help if one is interested in a
time-series analysis.
