from flask import Flask, render_template, Response
from flask import request, redirect, url_for
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


    """ def process_frame(self):  
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)
        gest_name = "default_value"
        
        with mp_hands.Hands(max_num_hands = 2,min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            
            ret, image = self.cap.read()

            if not ret:
                print("Ignoring empty camera frame.")
                

            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = hands.process(image)

            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.multi_hand_landmarks:
                GestureController.classify_hands(results)
                handmajor.update_hand_result(GestureController.hr_major)
                handminor.update_hand_result(GestureController.hr_minor)

                handmajor.set_finger_state()
                handminor.set_finger_state()
                gest_name = handminor.get_gesture()

                if gest_name == Gest.PINCH_MINOR:
                    Controller.handle_controls(gest_name, handminor.hand_result)
                else:
                    gest_name = handmajor.get_gesture()
                    Controller.handle_controls(gest_name, handmajor.hand_result)

                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            else:
                Controller.prev_hand = None       
        return gest_name, image


def gen(gc):
    cap = gc.cap
    try:
        while GestureController.cap.isOpened() and GestureController.gc_mode:
            gest_name, frame = gc.process_frame()
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                print("Failed to encode the frame")
                continue

            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
            cap.release() """

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

@app.route('/save_mappings', methods=['POST'])
def save_mappings():
    mappings = {}

    # Read mappings from the form
    for key, value in request.form.items():
        if key.startswith('gesture_'):
            gesture_id = key.split('_')[1]
            action_key = f'action_{gesture_id}'
            action = request.form.get(action_key)
            mappings[value] = action

    # Save mappings to the file
    with open('mappings.txt', 'w') as f:
        for gesture, action in mappings.items():
            f.write(f'{gesture}:{action}\n')

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



""" @app.route('/video_feed')
def video_feed():    
    gc = GestureController()
    while True:
    #return Response(gen(gc), mimetype='multipart/x-mixed-replace; boundary=frame')
        gest_name, frame = gc.process_frame()

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        key = cv2.waitKey(1)
        if key == 27:  # The Esc key
            break     
        
    return Response(frame, mimetype='multipart/x-mixed-replace; boundary=frame') """
        

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
