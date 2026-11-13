import httpx
import pytest

from lrh.business import HostAuthError, HostHttpBusinessLookup, HostUnavailable


def lookup(handler):
    client = httpx.Client(base_url="http://host.test", transport=httpx.MockTransport(handler))
    return HostHttpBusinessLookup("http://host.test", client=client)


def test_forwards_bearer_and_maps_record():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.raw_path.decode()
        return httpx.Response(200, json={"kind": "order", "ref_id": "BM-1001", "title": "t", "body": "b"})

    record = lookup(handler).get("tok", "order", "BM-1001")
    assert (record.ref_id, seen["auth"], seen["path"]) == ("BM-1001", "Bearer tok", "/v1/orders/BM-1001")


def test_host_404_is_none_whether_denied_or_missing():
    assert lookup(lambda r: httpx.Response(404, json={"detail": "not_found"})).get("t", "order", "BM-1002") is None


def test_reference_is_url_encoded_not_interpolated():
    seen = {}

    def handler(request):
        seen["path"] = request.url.raw_path.decode()
        return httpx.Response(404)

    lookup(handler).get("t", "order", "BM-1/../../x?y=1")
    assert seen["path"] == "/v1/orders/BM-1%2F..%2F..%2Fx%3Fy%3D1"


def test_401_is_auth_error_and_5xx_or_timeout_is_unavailable():
    with pytest.raises(HostAuthError):
        lookup(lambda r: httpx.Response(401)).get("t", "order", "BM-1001")
    with pytest.raises(HostUnavailable):
        lookup(lambda r: httpx.Response(503)).get("t", "order", "BM-1001")

    def boom(request):
        raise httpx.ConnectTimeout("slow")

    with pytest.raises(HostUnavailable):
        lookup(boom).get("t", "order", "BM-1001")


def test_unknown_kind_rejected_before_any_request():
    with pytest.raises(ValueError):
        lookup(lambda r: pytest.fail("no request expected")).get("t", "customer", "c001")
