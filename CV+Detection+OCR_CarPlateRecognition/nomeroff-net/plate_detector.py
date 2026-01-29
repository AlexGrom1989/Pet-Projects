import os
import cv2, numpy as np
from nomeroff_net import pipeline
from typing import Optional, Tuple
from datetime import datetime

class PlateDetector:
    def __init__(self):
        print("Загрузка детектора...")
        self.detector = pipeline("number_plate_detection_and_reading_runtime", image_loader="opencv")
        print("Детектор загружен")
    
    def detect(self, frame: np.ndarray) -> Optional[Tuple[str, float]]:
        try:
            results = self.detector([frame])
            if results and len(results) > 0:
                plates = results[-1][-1]
                if plates:
                    plate = str(plates[0]).upper()
                    plate = ''.join(c for c in plate if c.isalnum())
                    return (plate, 0.95) if len(plate) >= 6 else None
        except:
            pass
        return None
    
    @staticmethod
    def save(frame: np.ndarray, direction: str, plate: str) -> str:
        os.makedirs(f"photos/{direction}", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = f"photos/{direction}/{plate}_{timestamp}.jpg"
        cv2.imwrite(path, frame)
        return path
