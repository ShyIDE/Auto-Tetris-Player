import time
import cv2
import numpy as np
import mss
import pyautogui
import threading
from pynput import keyboard

# **Game Capture Region**
game_region = {"top": 250, "left": 680, "width": 480, "height": 640}

# **Tetris Controls**
ROTATE_LEFT = 'z'
ROTATE_RIGHT = 'x'
MOVE_LEFT = 'left'
MOVE_RIGHT = 'right'
MOVE_DOWN = 'down'
HARD_DROP = 'space'
PAUSE_KEY = 'w'

# **Track AI State**
ai_running = True
game_active = False  

# **Pause AI When Pressing 'W'**
def toggle_ai():
    global ai_running
    ai_running = not ai_running
    state = "PAUSED 🛑" if not ai_running else "RUNNING ✅"
    print(f"🔄 AI is now: {state}", flush=True)

# **Keyboard Listener**
def listen_for_keys():
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()

def on_key_press(key):
    try:
        if key.char == PAUSE_KEY:
            toggle_ai()
    except AttributeError:
        pass  

# **Send Keystrokes**
def press_key(key):
    pyautogui.keyDown(key)
    time.sleep(0.05)
    pyautogui.keyUp(key)
    print(f"🔘 Pressed: {key}", flush=True)

# **Ensure Game Focus**
def focus_game():
    print("🎯 Clicking on game to ensure focus...", flush=True)
    pyautogui.click(game_region["left"] + 50, game_region["top"] + 50)
    time.sleep(0.2)

# **Capture Screen**
def capture_screen(region):
    with mss.mss() as sct:
        screenshot = sct.grab(region)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

# **Check if Tetris is Visible**
def is_game_visible():
    img = capture_screen(game_region)
    return img is not None and img.size > 0

# **Detect Board with Row Priority**
def detect_board(img):
    if img is None or img.size == 0:
        print("❌ Captured image is empty. Retrying...", flush=True)
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    try:
        board = cv2.resize(binary, (10, 20))
        board = (board > 128).astype(int)
    except cv2.error:
        print("⚠️ Resize failed! Retrying...", flush=True)
        return None  

    return board

def find_best_move(board):
    """
    Finds the best move by filling rows from left to right.
    Moves to the next row ONLY when the current row is completely full.
    """
    for row in range(19, -1, -1):  # Start from bottom row (19) and move up
        empty_cols = np.where(board[row, :] == 0)[0]  # Find empty columns in the current row
        
        # Check if the previous row still has empty spaces
        if row < 19 and np.any(board[row + 1, :] == 0):  
            print(f"⚠️ Previous Row {row+1} still has empty spaces! Staying in Row {row+1}", flush=True)
            continue  # Stay in the previous row to finish filling

        # Place in the first available empty column in the current row
        if len(empty_cols) > 0:
            target_col = empty_cols[0]  # Pick the first empty column from left to right
            print(f"🟢 Placing block in Row {row}, Column {target_col}", flush=True)
            return target_col  # Return the correct column for placement

    # If no valid move found, default to placing in the first available column in row 19
    print("⚠️ No valid move found, defaulting to the first available column at bottom", flush=True)
    first_empty_col = np.where(board[19, :] == 0)[0]
    return first_empty_col[0] if len(first_empty_col) > 0 else 5  # Default to first empty or center

# **Rotate Piece for Best Fit**
def rotate_piece():
    press_key(ROTATE_RIGHT)  
    time.sleep(0.1)

# **Move Piece Horizontally**
def move_piece(target_col, current_col):
    print(f"➡️ Moving piece from column {current_col} to {target_col}", flush=True)
    rotate_piece()  

    if target_col < current_col:
        for _ in range(current_col - target_col):
            press_key(MOVE_LEFT)
    elif target_col > current_col:
        for _ in range(target_col - current_col):
            press_key(MOVE_RIGHT)

    press_key(HARD_DROP)  

# **Show Capture Window with Grid**
def draw_detection_window():
    while True:
        img = capture_screen(game_region)
        if img is None or img.size == 0:
            print("❌ Tetris Not Found! Retrying...", flush=True)
            time.sleep(1)
            continue

        # **Draw Grid**
        for i in range(1, 10):  
            x = int(i * (game_region["width"] / 10))
            cv2.line(img, (x, 0), (x, game_region["height"]), (255, 255, 255), 1)
        for j in range(1, 20):  
            y = int(j * (game_region["height"] / 20))
            cv2.line(img, (0, y), (game_region["width"], y), (255, 255, 255), 1)

        cv2.putText(img, "✅ Tetris Frame", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Tetris Detection", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

# **Play Tetris Automatically**
def play_tetris():
    time.sleep(2)
    print("✅ Tetris AI Started!", flush=True)

    while True:
        if not ai_running:
            time.sleep(0.5)
            continue

        while not is_game_visible():
            print("🔄 Waiting for Tetris...", flush=True)
            time.sleep(2)

        focus_game()

        board_img = None
        while board_img is None:
            print("📷 Capturing board...", flush=True)
            board_img = capture_screen(game_region)
            if board_img is None or board_img.size == 0:
                print("⚠️ Empty board image! Retrying...", flush=True)
                time.sleep(1)
                continue

        board = None
        while board is None:
            print("🛠 Processing board state...", flush=True)
            board = detect_board(board_img)
            if board is None:
                print("⚠️ Invalid board detected! Retrying...", flush=True)
                time.sleep(1)
                continue

        target_col = find_best_move(board)
        current_col = 5  

        focus_game()
        move_piece(target_col, current_col)
        time.sleep(1)

# **Run Everything**
if __name__ == "__main__":
    ai_thread = threading.Thread(target=play_tetris, daemon=True)
    key_listener = threading.Thread(target=listen_for_keys, daemon=True)
    detection_thread = threading.Thread(target=draw_detection_window, daemon=True)

    ai_thread.start()
    key_listener.start()
    detection_thread.start()

    detection_thread.join()
