from pathlib import Path


def preprocess_image(source: Path, destination: Path) -> Path:
    """Perform local grayscale/threshold preprocessing for OCR."""
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("opencv-python is required for image preprocessing") from exc
    image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"無法讀取影像: {source}")
    image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), image)
    return destination

