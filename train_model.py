from ultralytics import YOLO

def main():
    # Load the latest YOLOv11 nano model (fast and accurate)
    model = YOLO('yolo11n.pt') 

    print("Starting YOLOv11 training...")
    
    # Train the model
    results = model.train(
        data='data.yaml', 
        epochs=30,                   # Reduced to 30 since dataset is large (14k images)
        imgsz=640,                   # Dataset is already sized to 640, so this matches perfectly
        batch=16,                    
        name='cargosight_yolo11',        
        device='0',                  # Change to 'cpu' if you don't have an Nvidia GPU setup
        workers=0
    )

    print("Training complete! Your model is saved in runs/detect/cargosight_yolo11/weights/best.pt")

if __name__ == '__main__':
    main()