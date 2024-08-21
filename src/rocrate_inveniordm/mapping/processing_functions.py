import re

from rocrate_inveniordm.mapping.mapping_utils import SPDX_URI_PATTERN, MappingException


def dateProcessing(value):
    from dateutil.parser import parse

    if not value:
        return None

    if len(value) == 4:
        # only year
        return value

    fuzzy_date = parse(value, fuzzy=True)
    if not fuzzy_date:
        print("Warning: Date {date} could not be parsed.")
        return None
    return fuzzy_date.strftime("%Y-%m-%d")


def geonamesProcessing(value):
    # map the geonmames url to the geonames id
    # example: "http://sws.geonames.org/8152662/"
    if not value:
        return None
    if not value.startswith("http://sws.geonames.org/"):
        # not a geonnames url
        return None

    replaced_url = value.replace("http://sws.geonames.org/", "")
    replaced_url = replaced_url.replace("/", "")
    return replaced_url


def doi_processing(value):
    # check if value is doi format
    # example: "https://doi.org/10.4225/59/59672c09f4a4b"
    if not value:
        return None

    if not value.startswith("https://doi.org/"):
        return None

    replaced_url = value.replace("https://doi.org/", "")
    return replaced_url


def orcidProcessing(value):
    if not value:
        return None

    if not value.startswith("https://orcid.org/"):
        return None

    replaced_url = value.replace("https://orcid.org/", "")
    return replaced_url


def authorProcessing(value):
    if value == "Person":
        return "personal"
    elif value == "Organization":
        return "organizational"
    else:
        return None


def ISO8601Processing(value):
    return "ABC"


def embargoDateProcessing(value):
    """
    Parses the date and returns it in the format YYYY-MM-DD.
    """
    from dateutil.parser import parse

    if value is None:
        return None
    fuzzy_date = parse(value, fuzzy=True)
    if not fuzzy_date:
        print("Warning: Date {date} could not be parsed.")
        return None
    return fuzzy_date.strftime("%Y-%m-%d")


def convert_to_iso_639_3(value):
    """
    Converts the value to a valid ISO-639-3 language code
    """
    import iso639

    if value is None:
        return None
    try:
        language = iso639.Language.match(value)
        code = language.part3
    except iso639.language.LanguageNotFoundError:
        return None

    return code


def spdx_id_from_uri(value):
    match = re.match(SPDX_URI_PATTERN, value)
    if match:
        id = match.group("id")
        if id.endswith(".html") or id.endswith(".json"):
            id = id[:-5]
        id = id.lower()
        return id
    else:
        raise MappingException(
            f'The URI "{value}" was detected as an SPDX URI, '
            "but the SPDX identifier could not be extracted."
        )
