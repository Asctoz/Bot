import speech_recognition as sr
import pyttsx3
import threading
import time
import google.generativeai as genai
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext

# === Global Configuration ===
activation_phrase = "hey steve"
MIC_INDEX = 0
assistant_active = True

# === Lock for TTS engine to avoid concurrent access ===
tts_lock = threading.Lock()

# Initialize TTS engine
def init_tts():
    try:
        engine = pyttsx3.init('sapi5')
        engine.setProperty('rate', 150)
        return engine
    except Exception as e:
        log_queue.put(('log', f"TTS initialization error: {e}"))
        return None

# Enhanced TTS with stop control
def say(text):
    if not tts_engine:
        return

    log_queue.put(('led', 'speak'))
    with tts_lock:
        if tts_engine.isBusy():
            tts_engine.stop()
        try:
            tts_engine.say(text)
            log_queue.put(('status', "Speaking response..."))
            tts_engine.runAndWait()
        except Exception as e:
            log_queue.put(('log', f"TTS error: {e}"))
    log_queue.put(('led', 'idle'))

# AI processing
def process_with_ai(question):
    log_queue.put(('led', 'process'))
    log_queue.put(('status', "Processing question with AI..."))

    prompt = (
        f"Provide a detailed response to the question '{question}' "
        f"Context: {', '.join(conversation_history[-10:]) or 'none'} "
        "Use only proper Punctuation in classical english and no special characters. Limit your answer to 100 words or less preferably but can exceed if necessary."
    )
    try:
        response = ai_model.generate_content(
            contents=prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=800
            )
        )
        ai_response = response.text.strip() or ""
        log_queue.put(('conversation', f"{question}||{ai_response}"))
        conversation_history.append(f"Q: {question}")
        conversation_history.append(f"A: {ai_response}")
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]
        return ai_response
    except Exception as e:
        log_queue.put(('log', f"AI error: {e}"))
        return ""

# Listen continuously for activation phrase
def listen_for_activation_forever():
    def listen_loop():
        log_queue.put(('status', "Waiting for activation phrase..."))
        log_queue.put(('led', 'listen'))

        with sr.Microphone(device_index=MIC_INDEX) as source:
            recognizer.adjust_for_ambient_noise(source)
            while assistant_active:
                try:
                    log_queue.put(('log', "Listening for activation phrase..."))
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio).lower()
                    log_queue.put(('log', f"Heard: {text}"))

                    if activation_phrase in text:
                        log_queue.put(('log', "Activation phrase detected!"))
                        with tts_lock:
                            if tts_engine.isBusy():
                                tts_engine.stop()
                        say("Yes")
                        threading.Thread(target=listen_for_question_and_respond, daemon=True).start()
                        break  # Exit loop after activation

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    log_queue.put(('log', f"Speech recognition error: {e}"))

    if assistant_active:
        threading.Thread(target=listen_loop, daemon=True).start()

# Listen for question and respond
def listen_for_question_and_respond():
    log_queue.put(('status', "Listening for question..."))
    log_queue.put(('led', 'listen'))

    with sr.Microphone(device_index=MIC_INDEX) as source:
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            question = recognizer.recognize_google(audio)
            log_queue.put(('log', f"Question detected: {question}"))

            ai_response = process_with_ai(question)
            log_queue.put(('status', "Speaking response..."))
            say(ai_response)

        except sr.WaitTimeoutError:
            log_queue.put(('log', "No question was asked after activation."))
        except sr.UnknownValueError:
            log_queue.put(('log', "Could not understand the question."))
        except sr.RequestError as e:
            log_queue.put(('log', f"Speech recognition error: {e}"))

    log_queue.put(('status', "Restarting activation listener..."))
    log_queue.put(('led', 'idle'))
    if assistant_active:
        listen_for_activation_forever()

# Detect microphone index
def init_mic():
    global MIC_INDEX
    log_queue.put(('log', "Detecting microphone..."))
    for idx, name in enumerate(sr.Microphone.list_microphone_names()):
        try:
            with sr.Microphone(device_index=idx) as src:
                MIC_INDEX = idx
                log_queue.put(('log', f"Using microphone: {name} (Index {idx})"))
                break
        except Exception:
            continue
    else:
        log_queue.put(('log', "No valid microphone found. Using default device."))

    if assistant_active:
        listen_for_activation_forever()

# === GUI Setup ===
def create_gui():
    global root, conversation_text, log_text, status_label, led_canvas, led, ai_model

    root = tk.Tk()
    root.title("Steve Assistant")
    root.geometry("900x700")
    root.minsize(700, 500)

    # === Tkinter Variables (NOW PLACED AFTER root=Tk()) ===
    global api_key_var, activation_var, rate_var
    api_key_var = tk.StringVar(value="AIzaSyAYHX8H-TTaSh9mk7kj67PpJUhlYyv-XjY")
    activation_var = tk.StringVar(value="hey steve")
    rate_var = tk.IntVar(value=150)

    # Initialize Google Gemini API
    genai.configure(api_key=api_key_var.get())
    ai_model = genai.GenerativeModel('gemini-2.0-flash')

    # Style configuration
    style = ttk.Style()
    style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
    style.configure("Status.TLabel", font=("Helvetica", 12))

    # Title Bar
    title_frame = ttk.Frame(root)
    title_frame.pack(pady=10)
    ttk.Label(title_frame, text="🎤 Steve Voice Assistant", style="Header.TLabel").pack()

    # Status Frame
    status_frame = ttk.Frame(root)
    status_frame.pack(pady=5)

    status_label = ttk.Label(status_frame, text="Status: Initializing...", style="Status.TLabel")
    status_label.pack(side=tk.LEFT, padx=10)

    led_canvas = tk.Canvas(status_frame, width=20, height=20)
    led = led_canvas.create_oval(5, 5, 15, 15, fill="gray")
    led_canvas.pack(side=tk.LEFT, padx=5)

    # Conversation History
    conv_frame = ttk.LabelFrame(root, text="Conversation History")
    conv_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    conversation_text = scrolledtext.ScrolledText(conv_frame, wrap=tk.WORD, width=80, height=15, state='disabled')
    conversation_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
    conversation_text.tag_configure('question', foreground='navy', spacing2=2)
    conversation_text.tag_configure('answer', foreground='darkgreen', spacing3=5)

    # Log Output
    log_frame = ttk.LabelFrame(root, text="System Log")
    log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=10, state='disabled')
    log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    # Control Panel
    control_frame = ttk.Frame(root)
    control_frame.pack(pady=10, fill=tk.X)

    def toggle_listening():
        global assistant_active
        assistant_active = not assistant_active
        if assistant_active:
            start_button.config(text="Pause Listening")
            log_queue.put(('status', "Assistant activated"))
            listen_for_activation_forever()
        else:
            start_button.config(text="Resume Listening")
            log_queue.put(('status', "Assistant paused"))

    start_button = ttk.Button(control_frame, text="Pause Listening", command=toggle_listening)
    start_button.pack(side=tk.LEFT, padx=5)

    def manual_activation():
        log_queue.put(('log', "Manual activation triggered"))
        threading.Thread(target=listen_for_question_and_respond, daemon=True).start()

    manual_button = ttk.Button(control_frame, text="Manual Activation", command=manual_activation)
    manual_button.pack(side=tk.LEFT, padx=5)

    def open_settings():
        settings_window = tk.Toplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("500x400")

        notebook = ttk.Notebook(settings_window)
        notebook.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        # API Settings Tab
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="API Settings")

        ttk.Label(api_frame, text="Google API Key:").pack(pady=5)
        api_entry = ttk.Entry(api_frame, width=50, textvariable=api_key_var)
        api_entry.pack(pady=5)

        # Assistant Settings Tab
        asst_frame = ttk.Frame(notebook)
        notebook.add(asst_frame, text="Assistant Settings")

        ttk.Label(asst_frame, text="Activation Phrase:").pack(pady=5)
        act_entry = ttk.Entry(asst_frame, textvariable=activation_var)
        act_entry.pack(pady=5)

        # Audio Settings Tab
        audio_frame = ttk.Frame(notebook)
        notebook.add(audio_frame, text="Audio Settings")

        ttk.Label(audio_frame, text="TTS Speech Rate:").pack(pady=5)
        rate_slider = ttk.Scale(audio_frame, from_=100, to=300, variable=rate_var, orient=tk.HORIZONTAL)
        rate_slider.pack(pady=5)

        def save_settings():
            global activation_phrase
            activation_phrase = activation_var.get().lower()

            if tts_engine:
                with tts_lock:
                    tts_engine.setProperty('rate', rate_var.get())

            settings_window.destroy()
            log_queue.put(('log', "Settings saved and applied."))

        ttk.Button(settings_window, text="Save Settings", command=save_settings).pack(pady=10)

    settings_button = ttk.Button(control_frame, text="Settings", command=open_settings)
    settings_button.pack(side=tk.LEFT, padx=5)

    exit_button = ttk.Button(control_frame, text="Exit", command=root.destroy)
    exit_button.pack(side=tk.RIGHT, padx=5)

    # Status Updates
    def update_gui():
        while True:
            try:
                msg_type, content = log_queue.get_nowait()
                if msg_type == 'log':
                    log_text.configure(state='normal')
                    log_text.insert(tk.END, f"[LOG] {content}\n")
                    log_text.configure(state='disabled')
                    log_text.see(tk.END)
                elif msg_type == 'conversation':
                    q, a = content.split('||')
                    conversation_text.configure(state='normal')
                    conversation_text.insert(tk.END, f"Q: {q}\n", 'question')
                    conversation_text.insert(tk.END, f"A: {a}\n\n", 'answer')
                    conversation_text.configure(state='disabled')
                    conversation_text.see(tk.END)
                elif msg_type == 'status':
                    status_label.config(text=f"Status: {content}")
                elif msg_type == 'led':
                    colors = {"idle": "gray", "listen": "green", "process": "gold", "speak": "red"}
                    led_canvas.itemconfig(led, fill=colors.get(content, "gray"))
            except queue.Empty:
                break
        root.after(100, update_gui)

    root.after(100, update_gui)
    log_queue.put(('status', "GUI initialized successfully"))

    # Start assistant threads
    threading.Thread(target=init_mic, daemon=True).start()
    root.mainloop()

# === Global Objects ===
tts_engine = init_tts()
recognizer = sr.Recognizer()
conversation_history = []
log_queue = queue.Queue()

# Main Execution
if __name__ == '__main__':
    create_gui()
