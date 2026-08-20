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
# Suppress ccache warning from paddle
warnings.filterwarnings("ignore", message="No ccache found")

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

def filter_overlapping_bboxes(
    bboxes: List[Tuple[int, int, int, int]], 
    threshold: float = 0.4
) -> List[Tuple[int, int, int, int]]:
    
    # Calculate area and pair with the original box
    boxes_with_area = []
    for box in bboxes:
        x1, y1, x2, y2 = box
        area = max(0, x2 - x1) * max(0, y2 - y1)
        boxes_with_area.append((area, box))
    
    # Sort boxes by area descending so larger boxes are processed first
    boxes_with_area.sort(key=lambda x: x[0], reverse=True)
    
    keep = [True] * len(boxes_with_area)
    
    for i in range(len(boxes_with_area)):
        if not keep[i]:
            continue
        area_i, box_i = boxes_with_area[i]
        x1_i, y1_i, x2_i, y2_i = box_i
        
        for j in range(i + 1, len(boxes_with_area)):
            if not keep[j]:
                continue
            area_j, box_j = boxes_with_area[j]
            x1_j, y1_j, x2_j, y2_j = box_j
            
            # Intersection coordinates
            x1_inter = max(x1_i, x1_j)
            y1_inter = max(y1_i, y1_j)
            x2_inter = min(x2_i, x2_j)
            y2_inter = min(y2_i, y2_j)
            
            inter_w = max(0, x2_inter - x1_inter)
            inter_h = max(0, y2_inter - y1_inter)
            inter_area = inter_w * inter_h
            
            if inter_area == 0:
                continue
            
            # Overlap relative to the smaller box (box_j is always smaller or equal)
            overlap_ratio = inter_area / area_j if area_j > 0 else 0
            
            # Note: For standard Intersection over Union (IoU), use:
            # overlap_ratio = inter_area / (area_i + area_j - inter_area)
            
            if overlap_ratio > threshold:
                keep[j] = False
                
    return [boxes_with_area[i][1] for i in range(len(boxes_with_area)) if keep[i]]

def detect_text_lines(
    image: npt.NDArray, min_height=20, margin_x: int=7, margin_y: int=7
) -> List[Tuple[npt.NDArray, Tuple[int, int, int, int]]]:
    
    if len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1):
        process_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    else:
        process_image = image

    detector = OCRManager.get_paddle()
    results = detector.predict(process_image)
    
    text_lines = []
    
    if not results or results[0] is None:
        return text_lines
    
    boxes = results[0].get('dt_polys', [])
    img_h, img_w = image.shape[:2]
    bboxes = []
    for box in boxes:
        pts = np.array(box, dtype=np.int32)
        x_min, y_min = np.min(pts, axis=0)
        x_max, y_max = np.max(pts, axis=0)
        
        x_min = max(0, x_min - margin_x)
        y_min = max(0, y_min - margin_y)
        x_max = min(img_w, x_max + margin_x)
        y_max = min(img_h, y_max + margin_y)
        
        if (y_max - y_min) < min_height:
            continue
        
        bboxes.append((int(x_min), int(y_min), int(x_max), int(y_max)))
            
    bboxes = filter_overlapping_bboxes(bboxes) # filter overlapped bboxes
    for box in bboxes:
        x1, y1, x2, y2 = box
        text_lines.append((
            image[y1:y2, x1:x2], 
            (x1, y1, x2, y2)
        ))
    # Sort from top to bottom (y_min), then left to right (x_min)
    text_lines.sort(key=lambda item: (item[1][1], item[1][0]))
        
    return text_lines

def trim_line_whitespace(line_image: npt.NDArray, padding=10) -> npt.NDArray:
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
    text_lines = detect_text_lines(page_img)

    line_images = [
        l[0] for l in text_lines
    ]
    
    # Extract text for each line
    reader = OCRManager.get_easyocr()
    
    result_texts = []
    for line_img in line_images:
        img = trim_line_whitespace(line_img)
        text = reader.recognize(img, blocklist=OCR_BLOCK_LIST)[0][1]  # type: ignore
        result_texts.append(text)

    return "\n".join(result_texts)
