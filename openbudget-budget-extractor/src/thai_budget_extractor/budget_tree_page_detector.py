import numpy as np
import numpy.typing as npt
import cv2

def get_white_column_ranges(image_array: npt.ArrayLike, margin_percent: int = 15):
    """
    Finds ranges of columns that are completely white (255) 
    within the content area (excluding margins).
    """
    img = np.array(image_array)
    width = img.shape[1]
    
    # Calculate margin in pixels
    margin = int(width * (margin_percent / 100))
    
    # Slice the image to ignore margins
    content_area = img[:, margin : width - margin]
    
    # Identify white columns in the sliced content area
    is_white_col = np.all(content_area == 255, axis=0)
    
    # Find transitions
    padded = np.concatenate(([False], is_white_col, [False]))
    diffs = np.diff(padded.astype(int))
    
    # Find start/end indices relative to the CONTENT_AREA
    starts_in_content = np.where(diffs == 1)[0]
    ends_in_content = np.where(diffs == -1)[0]
    
    # Offset the indices back to original image coordinates
    # We add the margin back to map the content-indices to full-image-indices
    starts = starts_in_content + margin
    ends = ends_in_content + margin
    
    return list(zip(starts, ends - 1))

def is_budget_tree_page(page: npt.ArrayLike) -> bool:
    white_spaces = get_white_column_ranges(page)
    return bool(white_spaces)
