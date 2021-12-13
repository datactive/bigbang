Provided Datasets
====================

In addition to providing tools for gathering data from public sources,
BigBang also includes some datasets that have been curated by contributors and researchers.

The BigBang repository does not contain personally identifiable information of any kind.

The datasets included in BigBang pertain to organizational entities and provide metadata useful in
preprocessing and analysis of those entities.


Email domain categories
----------------------------

BigBang comes with a partial list of email domains, categorized as:

- **Generic**. A domain associated with a generic email provider. E.g. ``gmail.com``
- **Personal**. A domain associated with a single individual. E.g ``csperkins.org``
- **Company**. A domain associated with a particular company. E.g. ``apple.com``
- **Academic**. A domain associated with a university or academic professional organization. E.g. ``mit.edu``
- **SDO**. A domain associated with a Standards Development Organization. E.g. ``ietf.org``

This data can be loaded as a Pandas DataFrame with indices as email domains and 
categories in the ``category`` column with the following code:

::

  import bigbang.datasets.domains as domains``
  domain_data = domains.load_data()``

The sources of this data are a hand-curated list of domains provided by BigBang contributors
and a list of generic email domain providers provided by this `public gist <https://gist.github.com/ammarshah/f5c2624d767f91a7cbdc4e54db8dd0bf/>`_.