import cv2
import dlib
import numpy as np
import csv
import time
from datetime import datetime

def shape_to_np(shape, dtype="int"):
    """Convert dlib shape object to numpy array"""
    coords = np.zeros((shape.num_parts, 2), dtype=dtype)
    for i in range(0, shape.num_parts):
        coords[i] = (shape.part(i).x, shape.part(i).y)
    return coords

def calculate_face_orientation(landmarks_np):
    """Calculate face orientation based on key facial landmarks
    
    Returns a value from -1 (far left) to 1 (far right)
    """
    # Get landmarks for face edges and nose
    # Left side of face: point 0
    # Right side of face: point 16
    # Nose tip: point 30
    
    if len(landmarks_np) < 31:  # Make sure we have enough landmarks
        return None
        
    left_face = landmarks_np[0]
    right_face = landmarks_np[16]
    nose_tip = landmarks_np[30]
    
    # Measure the distance from nose to each edge of the face
    distance_to_left = np.linalg.norm(nose_tip - left_face)
    distance_to_right = np.linalg.norm(nose_tip - right_face)
    
    # Calculate total face width
    face_width = np.linalg.norm(right_face - left_face)
    
    # If face width is too small, return None
    if face_width < 10:
        return None
    
    # Calculate relative position of nose between left and right edges
    # This will be around 0.5 when facing forward
    relative_pos = distance_to_left / (distance_to_left + distance_to_right)
    
    # Apply smoothing for values near 0.5 (facing forward) to reduce noise
    # and exaggerate values at extremes for better sensitivity
    if abs(relative_pos - 0.5) < 0.05:
        # Very close to center, keep it smooth around 0
        orientation = (relative_pos - 0.5) * 10
    else:
        # Apply non-linear scaling to emphasize movement
        orientation = np.sign(relative_pos - 0.5) * pow(abs(relative_pos - 0.5) * 2, 0.8)
    
    # Clamp to [-1, 1] range
    return max(-1.0, min(1.0, orientation))

def apply_moving_average(current_value, previous_values, window_size=5):
    """Apply moving average smoothing to reduce jitter"""
    # Add current value to the list
    previous_values.append(current_value)
    
    # Keep only the most recent values up to window_size
    if len(previous_values) > window_size:
        previous_values.pop(0)
    
    # Calculate the average
    return sum(previous_values) / len(previous_values)

def calibrate_face_orientation(cap, detector, predictor):
    """Calibrate the face orientation tracking"""
    print("Calibration: Look straight at the camera and press SPACE")
    
    center_orientations = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Draw instruction
        cv2.putText(frame, "Look straight at camera and press SPACE", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = detector(gray)
        
        if len(faces) > 0:
            # We'll only process the first face detected
            face = faces[0]
            
            # Get facial landmarks
            landmarks = predictor(gray, face)
            landmarks_np = shape_to_np(landmarks)
            
            # Calculate face orientation
            orientation = calculate_face_orientation(landmarks_np)
            
            if orientation is not None:
                # Draw current orientation value
                cv2.putText(frame, f"Current value: {orientation:.2f}", (20, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Draw facial landmarks to show tracking
                for (x, y) in landmarks_np[[0, 16, 30]]:  # Draw only key points
                    cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
                
                # Connect key points with lines
                cv2.line(frame, tuple(landmarks_np[0]), tuple(landmarks_np[30]), (0, 255, 255), 2)
                cv2.line(frame, tuple(landmarks_np[16]), tuple(landmarks_np[30]), (0, 255, 255), 2)
        
        cv2.imshow('Calibration', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 32:  # SPACE key
            # Take 10 readings of orientation to average
            center_readings = 0
            sum_orientation = 0
            
            # Clear the frame for new message
            ret, frame = cap.read()
            cv2.putText(frame, "Calibrating... Keep looking straight ahead", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow('Calibration', frame)
            
            while center_readings < 10:
                ret, frame = cap.read()
                if not ret:
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = detector(gray)
                
                if len(faces) > 0:
                    face = faces[0]
                    landmarks = predictor(gray, face)
                    landmarks_np = shape_to_np(landmarks)
                    orientation = calculate_face_orientation(landmarks_np)
                    
                    if orientation is not None:
                        sum_orientation += orientation
                        center_readings += 1
                
                # Show progress
                cv2.putText(frame, f"Taking readings: {center_readings}/10", (20, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow('Calibration', frame)
                cv2.waitKey(1)
                time.sleep(0.1)
            
            # Calculate center offset
            if center_readings > 0:
                center_offset = sum_orientation / center_readings
                print(f"Calibration complete! Center offset: {center_offset:.4f}")
                cv2.destroyWindow('Calibration')
                return center_offset
            else:
                print("Calibration failed, couldn't get enough readings.")
                continue
    
    cv2.destroyWindow('Calibration')
    return 0.0  # Default to no offset if calibration fails

def main():
    # Initialize dlib's face detector and facial landmark predictor
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    # Ensure the camera is opened properly
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    # Wait for camera to initialize
    time.sleep(1)
    
    # Prepare CSV file
    csv_filename = f"face_orientation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'orientation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    print("Press 'c' to start calibration")
    print("Press 'q' to quit")
    
    calibrated = False
    center_offset = 0.0  # Default to no offset
    
    last_orientation_value = None
    last_write_time = time.time()
    
    # For smoothing
    orientation_history = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = detector(gray)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            # Start calibration
            print("Starting calibration...")
            center_offset = calibrate_face_orientation(cap, detector, predictor)
            calibrated = True
            print("Calibration complete!")
            print("Recording to", csv_filename)
            continue
        elif key == ord('q'):
            break
        
        # If no calibration yet, show instructions
        if not calibrated:
            cv2.putText(frame, "Press 'c' to calibrate", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if len(faces) > 0:
            # We'll only process the first face detected
            face = faces[0]
            
            # Get facial landmarks
            landmarks = predictor(gray, face)
            landmarks_np = shape_to_np(landmarks)
            
            # Calculate face orientation
            raw_orientation = calculate_face_orientation(landmarks_np)
            
            if raw_orientation is not None:
                # Apply calibration offset
                calibrated_orientation = raw_orientation - center_offset
                
                # Apply smoothing with a moving average
                smoothed_orientation = apply_moving_average(calibrated_orientation, orientation_history)
                
                # Clamp to [-1, 1]
                final_orientation = max(-1.0, min(1.0, smoothed_orientation))
                
                # Write to CSV if there's a significant change or time elapsed
                current_time = time.time()
                if last_orientation_value is None or abs(final_orientation - last_orientation_value) > 0.03 or current_time - last_write_time >= 0.5:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    with open(csv_filename, 'a', newline='') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writerow({
                            'timestamp': timestamp,
                            'orientation': f"{final_orientation:.2f}"
                        })
                    last_orientation_value = final_orientation
                    last_write_time = current_time
                
                # Format orientation value for display
                orientation_str = f"{final_orientation:.2f}"
                
                # Calculate color based on orientation (red for right, blue for left)
                if final_orientation > 0:
                    # Right side - more red
                    color = (0, int(255 * (1 - final_orientation)), int(255 * final_orientation))
                else:
                    # Left side - more blue
                    color = (int(255 * abs(final_orientation)), int(255 * (1 - abs(final_orientation))), 0)
                
                # Display small label in corner
                cv2.putText(frame, f"Orientation: {orientation_str}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # Display large orientation value in center of screen
                frame_height, frame_width = frame.shape[:2]
                text_size = cv2.getTextSize(orientation_str, cv2.FONT_HERSHEY_DUPLEX, 2.0, 3)[0]
                text_x = (frame_width - text_size[0]) // 2
                text_y = frame_height - 50
                
                # Add background rectangle for better visibility
                cv2.rectangle(frame, 
                             (text_x - 10, text_y - text_size[1] - 10),
                             (text_x + text_size[0] + 10, text_y + 10),
                             (0, 0, 0), -1)
                
                # Draw the large text
                cv2.putText(frame, orientation_str, (text_x, text_y), 
                            cv2.FONT_HERSHEY_DUPLEX, 2.0, color, 3)
                
                # Draw a visualization bar
                bar_y = 60
                bar_height = 20
                bar_width = frame_width - 40
                
                # Draw background bar
                cv2.rectangle(frame, (20, bar_y), (20 + bar_width, bar_y + bar_height), (100, 100, 100), -1)
                
                # Calculate position
                pos_x = int(20 + (bar_width / 2) + (final_orientation * bar_width / 2))
                
                # Draw position indicator
                cv2.circle(frame, (pos_x, bar_y + bar_height // 2), 10, color, -1)
                
                # Add min and max labels
                cv2.putText(frame, "-1", (10, bar_y + bar_height + 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, "1", (20 + bar_width - 10, bar_y + bar_height + 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Draw facial landmarks for key points
                for (x, y) in landmarks_np[[0, 16, 30]]:  # Left face, right face, nose
                    cv2.circle(frame, (x, y), 4, color, -1)
                
                # Draw lines between key facial points
                cv2.line(frame, tuple(landmarks_np[0]), tuple(landmarks_np[30]), color, 2)
                cv2.line(frame, tuple(landmarks_np[16]), tuple(landmarks_np[30]), color, 2)
                
                # Draw face bounding box
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        # Display the resulting frame
        cv2.imshow('Face Orientation Tracker', frame)
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print(f"Face orientation data saved to {csv_filename}")

if __name__ == "__main__":
    main()