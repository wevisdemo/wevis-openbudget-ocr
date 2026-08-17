import numpy as np
import numpy.typing as npt
import cv2

def save_image_with_bboxes(image_array, bboxes, output_path="output.jpg", color=(0, 0, 255), thickness=2):
    """
    Draws bounding boxes on an image.
    
    :param image_array: The original numpy array, either 2D (H, W) or 3D (H, W, C).
    :param bboxes: List of tuples/lists in the format (x_min, y_min, x_max, y_max).
    :param output_path: Where to save the resulting jpg.
    :param color: BGR color tuple (e.g., (0, 0, 255) is red).
    :param thickness: Thickness of the box lines.
    """
    # 1. Convert grayscale to BGR if it's 2D so we can draw colored boxes
    if len(image_array.shape) == 2:
        img_display = cv2.cvtColor(image_array.astype(np.uint8), cv2.COLOR_GRAY2BGR)
    else:
        img_display = image_array.copy()

    # 2. Iterate through bboxes and draw rectangles
    for bbox in bboxes:
        # Unpack the bounding box coordinates
        x_min, y_min, x_max, y_max = bbox
        
        # cv2.rectangle requires integer pixel coordinates
        start_point = (int(x_min), int(y_min))
        end_point = (int(x_max), int(y_max))
        
        # Draw the rectangle
        cv2.rectangle(img_display, start_point, end_point, color, thickness)
        
    # 3. Save the image
    cv2.imwrite(output_path, img_display)
    print(f"Saved image with {len(bboxes)} bounding boxes to {output_path}")