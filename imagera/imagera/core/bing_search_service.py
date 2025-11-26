# core/services/vertex_product_search.py
from typing import Optional, Tuple

from google.cloud import aiplatform_v1 as aiplatform


class VertexProductRecognizer:
    """
    Calls a deployed Vertex AI Vision endpoint (image classification / product model)
    and returns ONE best product name (displayName).
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        endpoint_id: str,
    ):
        self.project_id = project_id
        self.location = location
        self.endpoint_id = endpoint_id

        api_endpoint = f"{location}-aiplatform.googleapis.com"
        self.client = aiplatform.PredictionServiceClient(
            client_options={"api_endpoint": api_endpoint}
        )
        self.endpoint_path = self.client.endpoint_path(
            project=project_id,
            location=location,
            endpoint=endpoint_id,
        )

    def extract_product_name(
        self,
        image_file=None,     
    ) -> Optional[str]:
        """
        Returns the top predicted displayName from the model,
        or None if nothing reasonable is found.

        Assumes your model is an image classification-type model
        that returns predictions with:
          - displayNames
          - confidences
        """
        if not image_file:
            raise ValueError("Provide image_file")

            # Read bytes from uploaded image
        content = image_file.read()
        instance = {"content": content, "mime_type": image_file.content_type or "image/jpeg"}


        instances = [instance]
        parameters = {}

        try:
            response = self.client.predict(
                endpoint=self.endpoint_path,
                instances=instances,
                parameters=parameters,
            )
        except Exception:
            return None

        # response.predictions is a list of per-instance predictions.
        # For AutoML / Vertex Vision classification you usually get:
        # predictions[0]["displayNames"], predictions[0]["confidences"]
        if not response.predictions:
            return None

        prediction = response.predictions[0]

        # predictions are protobuf Value objects; convert to dict
        # so we can index with normal keys
        if hasattr(prediction, "items"):
            pred_dict = dict(prediction.items())
        else:
            pred_dict = dict(prediction)

        display_names = pred_dict.get("displayNames") or pred_dict.get("display_names")
        confidences = pred_dict.get("confidences") or pred_dict.get("scores")

        if not display_names:
            return None

        # Pick the highest-confidence label
        if confidences and len(confidences) == len(display_names):
            best_idx = max(range(len(confidences)), key=lambda i: confidences[i])
        else:
            best_idx = 0

        best_name = display_names[best_idx]
        if isinstance(best_name, str) and best_name.strip():
            return best_name.strip()

        return None
