Open index.html directly for the offline demo.

To serve the demo and metadata API locally, open a terminal in this folder:
  python -m pip install -r requirements.txt
  python -m uvicorn server:app

Open http://127.0.0.1:8000 . Metadata is at /api/comparison.
The radar layers are aligned visual previews for the demo. The loss estimate is preliminary.
