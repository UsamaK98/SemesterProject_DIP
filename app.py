from flask import Flask, render_template, Response
from flask import request, redirect, url_for, flash
import cv2
from gesture_detection import GestureController
from threading import Thread, Event
import mediapipe as mp


mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
gesture_detection_active = Event()
gesture_detection_active.clear()


app = Flask(__name__)

# capture_frames function:
# This function captures video frames using the GestureController object and calls the
# process_frame method to process each frame
def capture_frames(gc):
    global gesture_detection_active
    while True:
        ret, frame = gc.cap.read()
        if not ret:
            break

        frame = gc.process_frame(frame, gesture_detection_active)
        gc.frame = frame

# gen function:
# This function generates video frames in the form of byte strings that can be used for streaming
# purposes. It reads frames from the GestureController object, encodes them as JPEG images, and
# returns the byte strings.
def gen(gc):
    while True:
        ret, frame = gc.cap.read()  # getattr(gc, 'frame', None)
        frame = cv2.flip(frame, 1)
        
        # Draw hand landmarks on the frame
        if gc.hr_major or gc.hr_minor:
            if gc.hr_major:
                mp_drawing.draw_landmarks(frame, gc.hr_major, mp.solutions.hands.HAND_CONNECTIONS)
            if gc.hr_minor:
                mp_drawing.draw_landmarks(frame, gc.hr_minor, mp.solutions.hands.HAND_CONNECTIONS)

        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            print("Failed to encode the frame")

        frame_bytes = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Create the camera object
camera = cv2.VideoCapture(0)
gc = GestureController()
Thread(target=capture_frames, args=(gc,), daemon=True).start()  
@app.route('/video_feed')
def video_feed():
    return Response(gen(gc), mimetype='multipart/x-mixed-replace; boundary=frame')
   
@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')  # Create a settings.html file inside the templates folder

@app.route('/virtual_mouse_controller')
def virtual_mouse_controller():
    return render_template('virtual_mouse_controller.html')  # Create a virtual_mouse_controller.html file inside the templates folder

@app.route('/update_gesture_mappings', methods=['POST'])
def update_gesture_mappings():
    form_data = request.form
    print("Form data:", form_data)

    with open('mappings.txt', 'r') as f:
        lines = f.readlines()

    updated_lines = []
    used_gestures = set()
    for line in lines:
        if line.strip():
            gesture, action = line.strip().split(':')
            if action in form_data:
                updated_gesture = form_data[action]
                if updated_gesture in used_gestures:
                    return f"Error: Gesture '{updated_gesture}' is already mapped to another action. Please go back & select a different gesture.", 400
                used_gestures.add(updated_gesture)
                updated_lines.append(f"{updated_gesture}:{action}\n")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    with open('mappings.txt', 'w') as f:
        f.writelines(updated_lines)

    return redirect(url_for('settings'))



@app.route('/start_gesture_detection')
def start_gesture_detection():
    global gesture_detection_active
    gesture_detection_active.set()
    return '', 204

@app.route('/stop_gesture_detection')
def stop_gesture_detection():
    global gesture_detection_active
    gesture_detection_active.clear()
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
