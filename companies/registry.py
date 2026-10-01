from companies.amazon import COMPANY as AMAZON
from companies.apple import COMPANY as APPLE
from companies.base import CompanyDefinition
from companies.databricks import COMPANY as DATABRICKS
from companies.snowflake import COMPANY as SNOWFLAKE
from companies.zscaler import COMPANY as ZSCALER
from companies.microsoft import COMPANY as MICROSOFT
from companies.amex import COMPANY as AMEX
from companies.capitalone import COMPANY as CAPITALONE
from companies.netflix import COMPANY as NETFLIX
from companies.stripe import COMPANY as STRIPE
from companies.reddit import COMPANY as REDDIT
from companies.redhat import COMPANY as REDHAT
from companies.yahoo import COMPANY as YAHOO
from companies.amd import COMPANY as AMD
from companies.disney import COMPANY as DISNEY
from companies.ford import COMPANY as FORD
from companies.intel import COMPANY as INTEL
from companies.paramount import COMPANY as PARAMOUNT
from companies.paypal import COMPANY as PAYPAL
from companies.cisco import COMPANY as CISCO
from companies.dell import COMPANY as DELL
from companies.doordash import COMPANY as DOORDASH
from companies.hp import COMPANY as HP
from companies.ibm import COMPANY as IBM
from companies.jpmc import COMPANY as JPMC
from companies.nvidia import COMPANY as NVIDIA
from companies.samsung import COMPANY as SAMSUNG
from companies.cvs import COMPANY as CVS
from companies.cvs_wd import COMPANY as CVS_WD
from companies.goldman_sachs import COMPANY as GOLDMAN_SACHS
from companies.google import COMPANY as GOOGLE
from companies.lyft import COMPANY as LYFT
from companies.meta import COMPANY as META
from companies.salesforce import COMPANY as SALESFORCE
from companies.uber import COMPANY as UBER

COMPANIES: dict[str, CompanyDefinition] = {
    AMAZON.slug: AMAZON,
    APPLE.slug: APPLE,
    CVS.slug: CVS,
    CVS_WD.slug: CVS_WD,
    GOLDMAN_SACHS.slug: GOLDMAN_SACHS,
    GOOGLE.slug: GOOGLE,
    LYFT.slug: LYFT,
    META.slug: META,
    SALESFORCE.slug: SALESFORCE,
    UBER.slug: UBER,
    CISCO.slug: CISCO,
    DELL.slug: DELL,
    DOORDASH.slug: DOORDASH,
    HP.slug: HP,
    IBM.slug: IBM,
    JPMC.slug: JPMC,
    NVIDIA.slug: NVIDIA,
    SAMSUNG.slug: SAMSUNG,
    AMD.slug: AMD,
    DISNEY.slug: DISNEY,
    FORD.slug: FORD,
    INTEL.slug: INTEL,
    PARAMOUNT.slug: PARAMOUNT,
    PAYPAL.slug: PAYPAL,
    REDDIT.slug: REDDIT,
    REDHAT.slug: REDHAT,
    YAHOO.slug: YAHOO,
    AMEX.slug: AMEX,
    CAPITALONE.slug: CAPITALONE,
    NETFLIX.slug: NETFLIX,
    MICROSOFT.slug: MICROSOFT,
    DATABRICKS.slug: DATABRICKS,
    SNOWFLAKE.slug: SNOWFLAKE,
    ZSCALER.slug: ZSCALER,
    STRIPE.slug: STRIPE,
}


def get_company(slug: str) -> CompanyDefinition:
    normalized_slug = slug.strip().lower()
    try:
        return COMPANIES[normalized_slug]
    except KeyError as exc:
        supported = ", ".join(sorted(COMPANIES))
        raise ValueError(f"Unsupported company '{slug}'. Supported companies: {supported}") from exc


def list_companies() -> list[str]:
    return sorted(COMPANIES)