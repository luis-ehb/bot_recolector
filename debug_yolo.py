import cv2
from screencap import get_screenshot
from detector import load_model, detect

MODEL_PATH = "../models/best.pt"


def main():
    model = load_model(MODEL_PATH)
    img = get_screenshot()
    
    # detecta TODO (sin filtrar clases)
    detections = detect(model, img, conf=0.3, classes=None)  # baja la conf si quieres
    
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        label = det["label"]
        conf = det["conf"]
        # dibujar rectángulo
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"{label} {conf:.2f}", (x1, y1-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    
    # guardar imagen de debug
    cv2.imwrite("debug_detections.png", img)
    print(f"[INFO] Imagen de detecciones guardada como debug_detections.png")
    
if __name__ == "__main__":
    main()
