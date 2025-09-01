from silhouette_core.quantize_models import quantize_embeddings


def test_quantize_embeddings(tmp_path):
    dist = tmp_path / "distillate.json"
    dist.write_text('{"embeddings": [[1, 2], [3, 4]]}')
    out = tmp_path / "embed.tflite"
    result = quantize_embeddings(dist, out)
    assert result.exists()
    assert result.read_text() == "[[1, 2], [3, 4]]"
