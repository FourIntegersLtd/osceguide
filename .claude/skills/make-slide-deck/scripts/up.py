"""up.py <name.jpg>... (from api/, via poetry) : resize and upload slide pictures to S3 under the pictures folder."""
import io, json, sys
from PIL import Image
from app.core.settings import get_settings
from app.features.media_production.s3 import s3_client
from app.features.media_production.slide_pictures import MAX_SIDE, PICTURE_FOLDER
from app.features.media_production.slide_scenes import ASSETS
s = get_settings(); c = s3_client(s)
for name in sys.argv[1:]:
    p = Image.open(ASSETS / "slides" / "images" / name).convert("RGB"); p.thumbnail((MAX_SIDE, MAX_SIDE))
    b = io.BytesIO(); p.save(b, "JPEG", quality=85); b.seek(0)
    c.upload_fileobj(b, s.aws_s3_bucket, f"{PICTURE_FOLDER}/{name}", ExtraArgs={"ContentType": "image/jpeg"}); print("up", name)
