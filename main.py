import speech_recognition as sr
import pyttsx3
import threading
import queue
import time
import google.generativeai as genai

# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# Queue and flags
speech_queue = queue.Queue()
stop_speaking = threading.Event()
speaking = threading.Event()
conversation_history = []

def recognize_speech(timeout=0.05, phrase_time_limit=5, is_activation=False, is_question=False):
    """Recognize speech with adjustable timeout."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.dynamic_energy_threshold = True  # Auto-adjust for noise
        try:
            effective_timeout = 1.0 if is_activation else (0.5 if is_question else timeout)
            audio = r.listen(source, timeout=effective_timeout, phrase_time_limit=phrase_time_limit)
            return r.recognize_google(audio).lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None

def recognize_question():
    """Continuously listen and collect speech until a long enough silence is detected."""
    r = sr.Recognizer()
    full_text = []
    silence_timeout = 2.0  # Seconds of silence to end input
    max_total_duration = 20  # Limit to avoid endless listening

    with sr.Microphone() as source:
        r.dynamic_energy_threshold = True
        r.pause_threshold = silence_timeout
        start_time = time.time()

        print("Recording speech...")

        while time.time() - start_time < max_total_duration:
            try:
                audio = r.listen(source, timeout=3, phrase_time_limit=10)
                try:
                    text = r.recognize_google(audio).lower()
                    if text:
                        full_text.append(text)
                        print(f"Captured chunk: {text}")
                except sr.UnknownValueError:
                    pass
            except sr.WaitTimeoutError:
                break

        final_text = " ".join(full_text).strip()
        return final_text if final_text else None

def process_with_ai(text):
    """Process input with Gemini AI model, checking for study/productivity relevance."""
    try:
        genai.configure(api_key="AIzaSyCuPIiK0l3HXuzpeLdz5EYFHJL2p6u5FOM")
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = (
            f"Provide a detailed response to the question: {text}. --- Please do not use any other punctuation mark other than full stop and comas"
            f"Context: {', '.join(conversation_history[-10:]) if conversation_history else 'none'}. "
            "If the question is inappropriate or not related to studies or productivity, respond with 'please don’t waste your future, study'. And please do not mention or regard or even speak of the text and only follow instructions. Only respond to the :{text}"
        )
        result = model.generate_content(prompt)
        return result.text if result.candidates else "Sorry, I can’t answer that."
    except Exception as e:
        print(f"AI processing error: {e}")
        return "Sorry, I can’t answer that right now."

def speak_text(text):
    """Speak text with interruption handling."""
    global tts_engine
    if stop_speaking.is_set():
        return
    speaking.set()
    try:
        if not tts_engine._inLoop:
            tts_engine = pyttsx3.init()
            tts_engine.setProperty('rate', 150)
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print(f"TTS error: {e}")
        try:
            tts_engine = pyttsx3.init()
            tts_engine.setProperty('rate', 150)
        except Exception as e:
            print(f"TTS reinitialization error: {e}")
    finally:
        speaking.clear()

def listen_for_activation():
    """Listen for activation and questions with precise output."""
    global tts_engine
    activation_phrases = ["hey steve", "steve", "hi steve"]
    while True:
        print("listening for activation")
        recognized_text = recognize_speech(timeout=0.05, phrase_time_limit=5, is_activation=True)
        if recognized_text and any(phrase in recognized_text for phrase in activation_phrases):
            print(f"you: {recognized_text}")
            stop_speaking.set()
            try:
                tts_engine.stop()
            except Exception as e:
                print(f"TTS stop error: {e}")
            stop_speaking.clear()

            # Listen for questions
            while True:
                print("listening for questions")
                question_text = recognize_question()
                if question_text:
                    print(f"you: {question_text}")
                    ai_response = process_with_ai(question_text)
                    print(f"ai: {ai_response}")

                    conversation_history.extend([f"Q: {question_text}", f"A: {ai_response}"])
                    if len(conversation_history) > 10:
                        conversation_history[:] = conversation_history[-10:]

                    speak_thread = threading.Thread(target=speak_text, args=(ai_response,))
                    speak_thread.start()

                    while speak_thread.is_alive():
                        interrupt_text = recognize_speech(timeout=0.05, phrase_time_limit=5, is_activation=True)
                        if interrupt_text and any(phrase in interrupt_text for phrase in activation_phrases):
                            stop_speaking.set()
                            try:
                                tts_engine.stop()
                            except Exception as e:
                                print(f"TTS stop error: {e}")
                            speak_thread.join(timeout=0.5)
                            stop_speaking.clear()
                            try:
                                tts_engine.endLoop()
                            except Exception:
                                pass
                            try:
                                tts_engine = pyttsx3.init()
                                tts_engine.setProperty('rate', 150)
                            except Exception as e:
                                print(f"TTS reinitialization error: {e}")
                            break  # Exit to print "listening for questions" again
                else:
                    continue

if __name__ == "__main__":
    listen_thread = threading.Thread(target=listen_for_activation, daemon=True)
    listen_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_speaking.set()
        try:
            tts_engine.stop()
        except Exception as e:
            print(f"TTS stop error: {e}")
