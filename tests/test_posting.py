from unittest.mock import Mock, patch

from silhouette_core.posting import post_transaction


def test_post_transaction_retries_success(tmp_path):
    responses = [Mock(status_code=429, text=""), Mock(status_code=201, text="ok")]

    def side_effect(*args, **kwargs):
        return responses.pop(0)

    with patch("silhouette_core.posting.requests.post", side_effect=side_effect) as mock_post:
        with patch("silhouette_core.posting.time.sleep"):
            posted, status, latency = post_transaction(
                {"id": "m1"}, "http://server", token=None, timeout=1, max_retries=1, deadletter_dir=str(tmp_path)
            )
    assert posted is True
    assert status == 201
    assert mock_post.call_count == 2


def test_post_transaction_failure_deadletter(tmp_path):
    resp = Mock(status_code=500, text="err")
    with patch("silhouette_core.posting.requests.post", return_value=resp), patch(
        "silhouette_core.posting.time.sleep"
    ):
        posted, status, latency = post_transaction(
            {"id": "m2"}, "http://server", token=None, timeout=1, max_retries=0, deadletter_dir=str(tmp_path)
        )
    assert posted is False
    assert status == 500
    assert (tmp_path / "m2_request.json").exists()
    assert (tmp_path / "m2_response.json").exists()
