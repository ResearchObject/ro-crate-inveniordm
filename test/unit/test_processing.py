import pytest

import rocrate_inveniordm.mapping.processing_functions as pf
from rocrate_inveniordm.mapping.mapping_utils import MappingException


def test_dateProcessing__date_only():
    out = pf.dateProcessing("5 June 2012")

    assert out == "2012-06-05"


def test_dateProcessing__timestamp():
    out = pf.dateProcessing("5 June 2012 09:30:44")

    assert out == "2012-06-05"


def test_dateProcessing__year_only():
    out = pf.dateProcessing("2012")

    assert out == "2012"


def test_dateProcessing__empty():
    out = pf.dateProcessing("")

    assert out is None


def test_dateProcessing__none():
    out = pf.dateProcessing(None)

    assert out is None


def test_spdx_id_from_uri__basic():
    out = pf.spdx_id_from_uri("https://spdx.org/licenses/CC-BY-NC-SA-4.0")

    assert out == "cc-by-nc-sa-4.0"


def test_spdx_id_from_uri__endswith_html():
    out = pf.spdx_id_from_uri("https://spdx.org/licenses/CC-BY-NC-SA-4.0.html")

    assert out == "cc-by-nc-sa-4.0"


def test_spdx_id_from_uri__fails():
    with pytest.raises(
        MappingException, match="SPDX identifier could not be extracted"
    ):
        pf.spdx_id_from_uri("https://spdx.org/licenses/")
