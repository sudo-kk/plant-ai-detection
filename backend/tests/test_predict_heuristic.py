from fastapi.testclient import TestClient
from app import app
from PIL import Image
import io


def test_predict_with_png():
    client = TestClient(app)
    img = Image.new('RGB', (32, 32), color=(120, 180, 120))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    files = {'image': ('test.png', buf, 'image/png')}
    r = client.post('/predict', files=files)
    assert r.status_code == 200
    data = r.json()
    assert 'disease' in data
    assert 'confidence' in data
    assert 'inference_ms' in data
