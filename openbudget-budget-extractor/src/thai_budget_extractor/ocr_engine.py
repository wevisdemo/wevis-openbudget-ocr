from typing import Tuple, List
import os, shutil
import urllib.request
import tarfile
import cv2 as cv2
import numpy as np
import numpy.typing as npt
import easyocr
from paddleocr import TextDetection
from .constants import OCR_BLOCK_LIST

import warnings

# Suppress the specific pin_memory warning from PyTorch
warnings.filterwarnings("ignore", category=UserWarning, message=".*pin_memory.*")

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"


class OCRManager:
    _easyocr_instance = None
    _paddle_instance = None

    EASYOCR_DIR = "models/thai-vl"
    EASYOCR_URL = (
        "https://github.com/napatswift/naplog/releases/download/v0.0.1/thai-vl.tar.gz"
    )

    # 1. Renamed to match the internal PaddleX model name exactly
    PADDLE_DIR = "models/PP-OCRv6_medium_det_infer"
    PADDLE_URL = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv6_medium_det_infer.tar"

    @staticmethod
    def _download_and_extract(url: str, dest_dir: str, expected_file: str):
        if os.path.exists(expected_file):
            return

        os.makedirs(dest_dir, exist_ok=True)
        print(f"Downloading from {url}...")

        tar_path = os.path.join(dest_dir, "temp_model_archive")
        try:
            urllib.request.urlretrieve(url, tar_path)
            print("Extracting...")
            with tarfile.open(tar_path, "r:*") as tar_ref:
                tar_ref.extractall(path=dest_dir)

            # Remove the tar file first so it doesn't interfere with our check below
            os.remove(tar_path)

            # Smart flattening: If the archive unpacked into a single nested folder, bring contents up
            extracted_items = os.listdir(dest_dir)
            if len(extracted_items) == 1:
                single_item = os.path.join(dest_dir, extracted_items[0])
                if os.path.isdir(single_item):
                    for item in os.listdir(single_item):
                        shutil.move(os.path.join(single_item, item), dest_dir)
                    os.rmdir(single_item)

        except Exception as e:
            if os.path.exists(tar_path):
                os.remove(tar_path)
            raise RuntimeError(f"Failed to download or extract the model: {e}")

    @classmethod
    def get_easyocr(cls) -> easyocr.Reader:
        if cls._easyocr_instance is None:
            expected_file = os.path.join(cls.EASYOCR_DIR, "thai-vl.pth")
            cls._download_and_extract(cls.EASYOCR_URL, cls.EASYOCR_DIR, expected_file)

            cls._easyocr_instance = easyocr.Reader(
                ["th"],
                recog_network="thai-vl",
                user_network_directory=cls.EASYOCR_DIR,
                model_storage_directory=cls.EASYOCR_DIR,
                detector=False,
                gpu=True,
                verbose=False,
            )
        return cls._easyocr_instance

    @classmethod
    def get_paddle(cls):
        if cls._paddle_instance is None:
            expected_file = os.path.join(cls.PADDLE_DIR, "inference.pdiparams")
            cls._download_and_extract(cls.PADDLE_URL, cls.PADDLE_DIR, expected_file)
            cls._paddle_instance = TextDetection(model_dir=cls.PADDLE_DIR)
        return cls._paddle_instance


def detect_thai_text_lines(
    image: npt.NDArray, kernel_size=(10, 80), min_height=10, margin=5
) -> Tuple[List[npt.NDArray], List[List[int]]]:
    """
    Detects and extracts text lines from a document image, optimized for Thai text.

    Parameters:
    - image: np.array of the original image (BGR or Grayscale).
    - kernel_size: tuple (height, width) for the dilation kernel.
                   Height connects tone marks/vowels to base chars.
                   Width connects characters together into a solid line.
    - min_height: minimum pixel height of a line to be considered valid (filters noise).
    - margin: pixels to add to the top and bottom of the cropped line image.

    Returns:
    - line_images: list of np.array (cropped image of each line)
    - bounding_boxes: list of tuples (y_start, y_end) for each line
    """

    # 1. Convert to grayscale if it's a color image
    if len(image.shape) == 3:
        gray = cv2.cvtColor(
            image, cv2.COLOR_BGR2GRAY
        )  # pyright: ignore[reportAttributeAccessIssue]
    else:
        gray = image.copy()

    # 2. Binarize the image (Otsu's thresholding)
    # We invert it (THRESH_BINARY_INV) so text becomes WHITE (255) and background BLACK (0).
    # This is required because morphological dilation expands WHITE pixels.
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 3. Dilate the image to connect characters
    # Thai specific: We need a decent height in the kernel to pull tone marks down to the base.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size[1], kernel_size[0]))
    dilated = cv2.dilate(binary, kernel, iterations=1)

    # 4. Calculate Horizontal Projection Profile
    # Sum the pixel values along the horizontal axis (rows)
    # A sum of 0 means the row is completely black (whitespace in original document)
    horizontal_projection = np.sum(dilated, axis=1)

    # 5. Find the start and end of text lines based on the projection
    lines = []
    in_text = False
    start_y = 0

    # We define a small threshold in case of tiny noise specks (e.g., 255 * 5 pixels)
    noise_threshold = 255 * 5

    for y, row_sum in enumerate(horizontal_projection):
        if not in_text and row_sum > noise_threshold:
            # Transition from gap to text
            in_text = True
            start_y = y
        elif in_text and row_sum <= noise_threshold:
            # Transition from text to gap
            in_text = False
            end_y = y

            # Filter out noise (lines that are too thin)
            if (end_y - start_y) >= min_height:
                lines.append((start_y, end_y))

    # Handle edge case where image ends while still inside a text block
    if in_text:
        if (len(horizontal_projection) - start_y) >= min_height:
            lines.append((start_y, len(horizontal_projection)))

    # 6. Extract the line images from the ORIGINAL image
    line_images = []
    bounding_boxes = []
    img_height = image.shape[0]

    for start_y, end_y in lines:
        # Add margin, but ensure it doesn't go outside image boundaries
        y1 = max(0, start_y - margin)
        y2 = min(img_height, end_y + margin)

        # Crop from original image
        line_img = image[y1:y2, :]

        line_images.append(line_img)
        bounding_boxes.append((y1, y2))

    return line_images, bounding_boxes


def trim_line_whitespace(line_image: npt.NDArray, padding=10) -> npt.ArrayLike:
    if len(line_image.shape) == 3:
        gray = cv2.cvtColor(line_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = line_image.copy()

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    vertical_projection = np.sum(binary, axis=0)

    non_zero_cols = np.where(vertical_projection > 0)[0]

    if len(non_zero_cols) == 0:
        return line_image

    start_x = max(0, non_zero_cols[0] - padding)
    end_x = min(line_image.shape[1], non_zero_cols[-1] + padding + 1)

    return line_image[:, start_x:end_x]


def extract_texts(page_img: npt.NDArray):
    line_images, bboxes = detect_thai_text_lines(page_img)

    # Extract text for each line
    reader = OCRManager.get_easyocr()
    detector = OCRManager.get_paddle()
    
    result_texts = []
    for line_img in line_images:
        img = trim_line_whitespace(line_img)
        text = reader.recognize(img, blocklist=OCR_BLOCK_LIST)[0][1]  # type: ignore
        result_texts.append(text)

    return "\n".join(result_texts)
