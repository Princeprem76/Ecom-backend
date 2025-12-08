# core/services/vertex_image_finder.py
import base64
from io import BytesIO
from typing import Optional

from PIL import Image
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict as schema_predict


class VertexImageProductFinder:
    """
    Predicts labels from an image using a Vertex AI Image Classification Endpoint.
    Converts any input image (e.g. WebP) to JPEG before sending.
    """

    def __init__(self, project: str, endpoint_id: str, location: str = "us-central1"):
        self.project = project
        self.endpoint_id = endpoint_id
        self.location = location
        self.api_endpoint = f"{location}-aiplatform.googleapis.com"

        self.client = aiplatform.gapic.PredictionServiceClient(
            client_options={"api_endpoint": self.api_endpoint}
        )
        self.endpoint_path = self.client.endpoint_path(
            project=self.project,
            location=self.location,
            endpoint=self.endpoint_id,
        )

    def _to_jpeg_bytes(self, image_bytes: bytes) -> Optional[bytes]:
        """
        Takes raw image bytes (any format Pillow understands, e.g. WebP)
        and returns JPEG bytes.
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # Ensure 3-channel RGB
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                elif img.mode == "L":
                    img = img.convert("RGB")

                buffer = BytesIO()
                # Quality 90 is a good balance, you can tweak
                img.save(buffer, format="JPEG", quality=90)
                return buffer.getvalue()
        except Exception:
            # if we can't decode, just return original for debugging
            return None

    def predict_product_name_from_file(self, image_file) -> Optional[str]:
        """
        image_file: Django UploadedFile
        Returns the best label name or None.
        """

        # Ensure pointer is at start
        if hasattr(image_file, "seek"):
            image_file.seek(0)

        raw_bytes = image_file.read()
        if not raw_bytes:
            return None

        # Convert to JPEG (handles WebP etc.)
        jpeg_bytes = self._to_jpeg_bytes(raw_bytes)
        if not jpeg_bytes:
            # fallback: try raw bytes (but this likely fails with the same error)
            jpeg_bytes = raw_bytes

        # Base64 encode for Vertex
        encoded_image = base64.b64encode(jpeg_bytes).decode("utf-8")

        instance = schema_predict.instance.ImageClassificationPredictionInstance(
            content=encoded_image
        ).to_value()

        instances = [instance]

        parameters = schema_predict.params.ImageClassificationPredictionParams(
            confidence_threshold=0.1,
            max_predictions=5,
        ).to_value()

        response = self.client.predict(
            endpoint=self.endpoint_path,
            instances=instances,
            parameters=parameters,
        )

        if not response.predictions:
            return None

        pred_dict = dict(response.predictions[0])
        display_names = pred_dict.get("displayNames") or []
        confidences = pred_dict.get("confidences") or []

        if not display_names:
            return None

        if confidences and len(confidences) == len(display_names):
            best_idx = max(range(len(confidences)), key=lambda i: confidences[i])
        else:
            best_idx = 0

        best_name = display_names[best_idx]
        return best_name.strip() if isinstance(best_name, str) else None
