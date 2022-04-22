# CONTENTS

1. General information
2. Definitions and explanation of Columns
3. Sources and methods

# 1. General Information
This table contains categorical information about stakeholders and subsidiaries that are active within the IETF and 3GPP.

In general, the 3GPP contains more fine-grained stakeholder compositions -- listing many more subsidiaries -- than the IETF. Therefore, if one is to use this data for the analysis of IETF mailing archives, we advise to merge all branches (subsidiaries, e.g., Ericsson España S.A.) into the highest node (stakeholder, e.g., Ericsson) of the tree. The highest node of the tree is identifiable through the subsidiary column, as the corresponding cell should be empty in that case.

# 2. Definitions and explanation of Columns
## Column A: name
The name of the company who has a member registered at a standard body organisation.
## Column B: Category
- Association
- Advertising Company
- Chipmaker
- Content Distribution Network
- Content Providers
- Consulting
- Cloud Provider
- Cybersecurity
- Financial Institution
- Hardware vendor
- Internet Registry
- Infrastructure Company
- Networking Equipment Vendor
- Network Service Provider
- Regional Standards Body
- Regulatory Body
- Research and Development Institution
- Software Provider
- Testing and Certification 
- Telecommunications Provider 
- Satellite Operator

As some stakeholders or subsidiaries are active in multiple market sectors, they have been associated with multiple categories, separating them with a comma.

As assigning such categories to stakeholders and subsidiaries is an inherently difficult endeavour we clearly state our objective here. The categories were assigned according to stakeholders and subsidiaries country registration and market sector activities as of November 2021. The correctness of those associations can’t be guaranteed to have been or will be the same in the past or future. 

[Something that we are thinking to follow up on in the future is to indicating whether the stakeholder or subsidiary has an ASN (Autonomous System Number; used for routing in the Internet), as it is not subject to debate and can be used to check for categories in other databases (eg, PeeringDB)]. A challenge with this is that corporations have different ASNs and there is change over time. 
## Column C: subsidiary
This column describes when a company is the subsidiary of another company in the list. If the cell in this column is empty, this company can be understood as the parent company. 
## Column D: stakeholdergroup
Stakeholdergroups are used as they have been defined in the WSIS process and the Tunis-agenda. 

- Academia
- Civil Society
- Private Sector (including industry consortia and associations; state-owned and government-funded businesses)
- Government
- Technical Community (IETF, ICANN, ETSI, 3GPP, oneM2M, etc)
- Intergovernmental organization 

## Column E: nationality
The country name in which the stakeholder or subsidiary is registered.

## Column F: email domain names
The Email domains associated with each stakeholder and subsidiary is derived from the Email addresses used by members that contribute to the public mailing archives of standard organisations IETF and 3GPP. The association has been made by hand to ensure that no, e.g., personal or free available domain names (such as @gmail.com) are used. Sometimes multiple email domain names match the same stakeholder, in which case both are listed separated by a comma.

## Column G: Membership Organization
Membership of regional SDOs, derived from 3GPP data.
- ARIB
- ATIS
- CCSA
- ETSI
- TSDSI
- TTA
- TTC

# 3. Sources and methods
The sources for relevant stakeholders and subsidiaries and their Email domain names are the mailing archives of the standard organisations and the membership data from the 3GPP. Their associated categories and nationalities are derived from Wikipedia data, the companies’ websites, as well as data from the standards organizations. 
