# python imports
import os
import json
import uuid
import traceback
from datetime import datetime

# other imports
import runpod
import torchaudio
from audiocraft.models import MAGNeT
from audiocraft.data.audio import audio_write

# installed imports
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import storage

load_dotenv()

# initialize firebase app
SERVICE_CERT = json.loads(os.getenv("SERVICE_CERT"))
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET")
cred_obj = firebase_admin.credentials.Certificate(SERVICE_CERT)
firebase_admin.initialize_app(cred_obj, {"storageBucket": STORAGE_BUCKET})


def generate_path(date=None):
    # Use the provided date or the current date if None
    if date is None:
        date = datetime.utcnow()
    # Format date components
    year = date.year
    month = date.month
    day = date.day
    # Format path
    path = os.path.join(f"{month:02d}-{year}", f"{day:02d}-{month:02d}")
    return path


def handler(job):
    try:
        request = job.get("input")
        model_name = f"facebook/{request.get('model', 'magnet-small-10secs')}"
        descriptions = str(request.get("prompt")).split(",")
        if not descriptions[0]:
            return {"error": "No description provided."}

        model = MAGNeT.get_pretrained(model_name)
        wav = model.generate(descriptions)

        results = {"audioURLs": []}

        for one_wav in wav:
            # Will save to filename.wav with loudness normalization at -14 db LUFS.
            filename = uuid.uuid4().hex
            filename = audio_write(
                filename,
                one_wav.cpu(),
                model.sample_rate,
                strategy="loudness",
                loudness_compressor=True,
            )

            # upload to firebase
            storage_client = storage.bucket()
            path = os.path.join("audiocraft", generate_path(), filename)
            blob = storage_client.blob(path)
            blob.upload_from_filename(filename)
            blob.make_public()
            url = blob.public_url
            os.remove(filename) if os.path.exists(filename) else None
            results["audioURLs"].append(url)

        results["success"] = True
        return results
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


runpod.serverless.start({"handler": handler})
