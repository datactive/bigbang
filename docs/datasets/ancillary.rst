.. _ancillary_datasets:

Ancillary Datasets
*********************

In addition to providing tools for gathering data from public sources, ``BigBang`` also includes some datasets that have been curated by contributors and researchers.

General
================

Email domain categories
-----------------------

BigBang comes with a partial list of email domains, categorized as:

- **Generic**. A domain associated with a generic email provider. E.g. ``gmail.com``
- **Personal**. A domain associated with a single individual. E.g ``csperkins.org``
- **Company**. A domain associated with a particular company. E.g. ``apple.com``
- **Academic**. A domain associated with a university or academic professional organization. E.g. ``mit.edu``
- **SDO**. A domain associated with a Standards Development Organization. E.g. ``ietf.org``

This data can be loaded as a Pandas DataFrame with indices as email domains and
categories in the ``category`` column with the following code:

::

  import bigbang.datasets.domains as domains
  domain_data = domains.load_data()

The sources of this data are a hand-curated list of domains provided by BigBang contributors
and a list of generic email domain providers provided by this `public gist <https://gist.github.com/ammarshah/f5c2624d767f91a7cbdc4e54db8dd0bf/>`_.


Organization Metadata
-----------------------

BigBang comes with a curated list of metadata about organizations. This data is provided as a DataFrame with the following columns:

- **name**. Organization name. E.g. ``gmail.com``
- **Category**. Kind of organization. E.g ``Infrastructure Company``
- **subsidiary**. This column describes when a company is the subsidiary of another company in the list. If the cell in this column is empty, this company can be understood as the parent company.. E.g. ``apple.com``
- **stakeholdergroup**. Stakeholdergroups are used as they have been defined in the WSIS process and the Tunis-agenda.
- **nationality**. The country name in which the stakeholder or subsidiary is registered.
- **email domain names**. Email domains associated with the organization. May include multiple, comma separated, domain names.
- **Membership Organization**. Membership of regional SDOs, derived from 3GPP data.

This data can be loaded as a Pandas DataFrame with indices as email domains and
categories in the ``category`` column with the following code:

::

  import bigbang.datasets.organizations as organizations
  organization_data = organizations.load_data()

The sources of this data are a hand-curated list of domains provided by BigBang contributors
and a list of generic email domain providers provided by this `public gist <https://gist.github.com/ammarshah/f5c2624d767f91a7cbdc4e54db8dd0bf/>`_.



IETF
================

Publication date of protocols.

3GPP
================

Release dates of standards.
